"""Regression tests for bugs.md B5, B7, B9, B10, B11, B13/B16 and B14."""

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestPanelClientIp:
    """B5: lockout must be per client, not global ("unknown" for everyone)."""

    def test_cloudflare_header_wins(self, monkeypatch):
        import auth
        fake = SimpleNamespace(context=SimpleNamespace(
            headers={"Cf-Connecting-Ip": "203.0.113.7"}, ip_address="172.21.0.1"))
        monkeypatch.setattr(auth, "st", fake)
        assert auth._get_client_ip() == "203.0.113.7"

    def test_peer_ip_without_cloudflare(self, monkeypatch):
        import auth
        fake = SimpleNamespace(context=SimpleNamespace(headers={}, ip_address="192.168.1.20"))
        monkeypatch.setattr(auth, "st", fake)
        assert auth._get_client_ip() == "192.168.1.20"

    def test_streamlit_still_provides_the_api(self):
        """The original bug was an API that silently disappeared."""
        import streamlit as st
        assert hasattr(st.context, "headers") and hasattr(st.context, "ip_address")


class TestReloadNotFromTunnel:
    """B7: tunnelled requests arrive from a private IP but carry CF-Connecting-IP."""

    @pytest.mark.asyncio
    async def test_reload_via_cloudflare_rejected(self, client):
        async with client as c:
            resp = await c.post("/reload-config", json={"key": "test_secret_key_123"},
                                headers={"CF-Connecting-IP": "203.0.113.7"})
        assert resp.status_code == 403


class TestStreamingBodyLimit:
    """B11: an oversized body without Content-Length is cut off, not buffered."""

    @pytest.mark.asyncio
    async def test_chunked_body_too_large(self, client):
        async def chunks():
            for _ in range(20):
                yield b"x" * 1000

        async with client as c:
            resp = await c.post("/webhook", content=chunks(),
                                headers={"content-type": "text/plain"})
        assert resp.status_code == 413

    @pytest.mark.asyncio
    async def test_small_chunked_body_still_readable(self, client, monkeypatch):
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")

        async def chunks():
            yield json.dumps({"key": "test_secret_key_123", "msg": "hi"}).encode()

        async with client as c:
            resp = await c.post("/webhook", content=chunks(),
                                headers={"content-type": "application/json"})
        assert resp.status_code == 200


class TestSecKeyMasking:
    """B14: records from child loggers must be masked too."""

    def test_child_logger_record_masked(self):
        from main import SecKeyFilter
        root_handlers = logging.getLogger().handlers
        assert any(isinstance(f, SecKeyFilter) for h in root_handlers for f in h.filters)
        record = logging.LogRecord("handler", logging.INFO, __file__, 1,
                                   '"%s %s"', ("POST", "/webhook/supersecretkey123"), None)
        for f in root_handlers[0].filters:
            f.filter(record)
        assert record.getMessage() == '"POST /webhook/***"'

    def test_format_placeholder_untouched(self):
        from main import SecKeyFilter
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "/webhook/%s", ("k",), None)
        SecKeyFilter().filter(record)
        record.getMessage()  # must not raise


class TestTelegramClient:
    """B13/B16: own Bot API client — retries on 429, never leaks the token."""

    def _resp(self, payload, status=200):
        r = MagicMock()
        r.status_code = status
        r.json.return_value = payload
        return r

    @patch("handler.time.sleep")
    @patch("handler.requests.post")
    def test_retries_after_429(self, post, sleep):
        from handler import Bot
        post.side_effect = [
            self._resp({"ok": False, "error_code": 429, "description": "Too Many Requests",
                        "parameters": {"retry_after": 3}}, 429),
            self._resp({"ok": True, "result": {"message_id": 1}}),
        ]
        Bot("123:ABC").sendMessage("-100", "hi")
        assert post.call_count == 2
        sleep.assert_called_once_with(3)

    @patch("handler.requests.post")
    def test_long_retry_after_not_waited(self, post):
        from handler import Bot, TelegramError
        post.return_value = self._resp({"ok": False, "description": "Too Many Requests",
                                        "parameters": {"retry_after": 60}}, 429)
        with pytest.raises(TelegramError):
            Bot("123:ABC").sendMessage("-100", "hi")
        assert post.call_count == 1

    @patch("handler.requests.post")
    def test_network_error_hides_token(self, post):
        import requests
        from handler import Bot, TelegramError
        post.side_effect = requests.ConnectionError("https://api.telegram.org/bot123:SECRET/sendMessage")
        with pytest.raises(TelegramError) as exc:
            Bot("123:SECRET").sendMessage("-100", "hi")
        assert "SECRET" not in str(exc.value)

    @patch("handler.requests.post")
    def test_markdown_error_falls_back_to_plain(self, post):
        from handler import Bot, _tg_send_message
        post.side_effect = [
            self._resp({"ok": False, "description": "Bad Request: can't parse entities"}, 400),
            self._resp({"ok": True, "result": {}}),
        ]
        _tg_send_message(Bot("1:A"), "-100", "*bad")
        assert "parse_mode" not in post.call_args_list[1].kwargs["json"]


class TestFormatPrice:
    """B10: minus kept, odd input returned unchanged, never raises."""

    @pytest.mark.parametrize("raw,expected", [
        ("-0.5", "-0.5"), ("-1234567.0", "-1 234 567"), ("inf", "inf"), ("nan", "nan"),
        ("1e-05", "1e-05"), ("abc", "abc"), (".5", "0.5"), ("100.10", "100.10"),
    ])
    def test_edge_cases(self, raw, expected):
        from aliases import format_price
        assert format_price(raw) == expected


class TestEnvWriter:
    """B9: panel writes .env values that python-dotenv reads back unchanged."""

    @pytest.mark.parametrize("value", ["p'a$s`w\\d", 'x"y', "a b#c", "$HOME", "plain"])
    def test_round_trip(self, tmp_path, value):
        from dotenv import dotenv_values
        from ui_utils import _set_env_key
        env = tmp_path / ".env"
        env.write_text("A=1\nDASHBOARD_PASSWORD=old\n")
        assert _set_env_key(str(env), "DASHBOARD_PASSWORD", value)
        assert dotenv_values(env) == {"A": "1", "DASHBOARD_PASSWORD": value}

    @pytest.mark.parametrize("value", ["${HOME}", "a\nb"])
    def test_rejects_unsafe_values(self, tmp_path, value):
        from ui_utils import _set_env_key
        env = tmp_path / ".env"
        env.write_text("DASHBOARD_PASSWORD=old\n")
        assert not _set_env_key(str(env), "DASHBOARD_PASSWORD", value)
        assert env.read_text() == "DASHBOARD_PASSWORD=old\n"
