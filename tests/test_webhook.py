"""Tests for FastAPI endpoints (webhook, health, reload)."""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    """HTTP client for FastAPI tests."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def _test_templates(tmp_path, monkeypatch):
    """Creates a temporary templates file for tests."""
    import templates as mod
    file = tmp_path / "templates.json"
    data = {
        "target": {
            "content": "Alert: {ticker} on {exchange} price {close}",
            "variables": ["ticker", "exchange", "close"],
        }
    }
    file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(mod, "TEMPLATES_FILE_PATH", file)


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        async with client as c:
            resp = await c.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_no_channels(self, client):
        """/health does not expose channel details."""
        async with client as c:
            resp = await c.get("/health")
        data = resp.json()
        assert "channels" not in data


class TestWebhook:
    """Tests for old format — JSON with key in body."""

    @pytest.mark.asyncio
    async def test_valid_payload(self, client, monkeypatch):
        """Valid payload with correct key — 200 (warning when no channels)."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook", json={
                "key": "test_secret_key_123",
                "msg": "Test message",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "warning")

    @pytest.mark.asyncio
    async def test_bad_key(self, client):
        """Wrong key — 403."""
        async with client as c:
            resp = await c.post("/webhook", json={
                "key": "wrong_key_padding_16",
                "msg": "Test",
            })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_key(self, client):
        """No key field in JSON and no key in URL — 400."""
        async with client as c:
            resp = await c.post("/webhook", json={
                "msg": "Test",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_msg(self, client):
        """No msg field — 400."""
        async with client as c:
            resp = await c.post("/webhook", json={
                "key": "test_secret_key_123",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_message_too_long(self, client):
        """Message > 4000 chars — 400."""
        async with client as c:
            resp = await c.post("/webhook", json={
                "key": "test_secret_key_123",
                "msg": "x" * 4001,
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_payload(self, client):
        """Empty JSON — 400."""
        async with client as c:
            resp = await c.post("/webhook", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_non_json_no_key(self, client):
        """Plain text on /webhook (no key in URL) — 400."""
        async with client as c:
            resp = await c.post(
                "/webhook",
                content="not json",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400


class TestWebhookKeyInUrl:
    """Tests for new format — key in URL."""

    @pytest.mark.asyncio
    async def test_key_in_url_json(self, client, monkeypatch):
        """Key in URL + JSON body without key field — 200 (warning when no channels)."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "msg": "Test with key in URL",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "warning")

    @pytest.mark.asyncio
    async def test_key_in_url_plain_text(self, client, monkeypatch):
        """Key in URL + plain text body — 200 (warning when no channels)."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="Test plain text alert",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "warning")

    @pytest.mark.asyncio
    async def test_key_in_url_bad(self, client):
        """Bad key in URL — 403."""
        async with client as c:
            resp = await c.post("/webhook/wrong_key_pad_16", json={
                "msg": "Test",
            })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_plain_text_empty(self, client):
        """Empty plain text body — 400."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_plain_text_too_long(self, client):
        """Plain text > 4000 chars — 400."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="x" * 4001,
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_url_key_overrides_json(self, client, monkeypatch):
        """URL key takes priority over JSON body key."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "key": "wrong_key_in_json",
                "msg": "Test key priority",
            })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_key_too_long(self, client):
        """Key longer than 256 chars — 422 (FastAPI validation)."""
        async with client as c:
            resp = await c.post(f"/webhook/{'x' * 257}", json={
                "msg": "Test",
            })
        assert resp.status_code == 422


class TestWebhookTemplates:
    """Tests for template system."""

    @pytest.mark.asyncio
    async def test_template_valid(self, client, monkeypatch, _test_templates):
        """Template with valid variables — 200 (warning when no channels)."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "template": "target",
                "ticker": "SPX",
                "exchange": "TVC",
                "close": "6910",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "warning")

    @pytest.mark.asyncio
    async def test_template_nonexistent(self, client, _test_templates):
        """Nonexistent template — 400."""
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "template": "nonexistent",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_template_missing_variables(self, client, monkeypatch, _test_templates):
        """Template with missing variables — empty strings used."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "template": "target",
                "ticker": "SPX",
            })
        assert resp.status_code == 200


class TestWebhookAliases:
    """Tests for alias system (e.g., /spot BTCUSDT BINANCE 68000)."""

    @pytest.fixture(autouse=True)
    def _test_aliases(self, tmp_path, monkeypatch):
        """Creates a temporary aliases file for tests."""
        import aliases as mod
        file = tmp_path / "aliases.json"
        data = {
            "spot": {
                "variables": ["ticker", "exchange", "close"],
                "template": "Target #{ticker} on {exchange} price {close}",
            },
            "simple": {
                "variables": [],
                "template": "Fixed alert message",
            },
            "withinterval": {
                "variables": ["ticker", "interval"],
                "template": "Alert {ticker} on {interval}",
            },
        }
        file.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(mod, "ALIASES_FILE", file)

    @pytest.mark.asyncio
    async def test_alias_valid(self, client, monkeypatch):
        """Valid alias with correct args — 200 (warning when no channels)."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/spot BTCUSDT BINANCE 68000",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "warning")

    @pytest.mark.asyncio
    async def test_alias_no_variables(self, client, monkeypatch):
        """Alias with zero variables — 200."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/simple",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_alias_unknown(self, client):
        """Unknown alias — 400 with generic error (no internal details)."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/nonexistent",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid request"

    @pytest.mark.asyncio
    async def test_alias_wrong_arg_count(self, client):
        """Alias with wrong number of args — 400 with generic error."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/spot BTCUSDT",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid request"

    @pytest.mark.asyncio
    async def test_alias_interval_converted(self, client, monkeypatch):
        """Alias with interval variable — numeric minutes converted to human form."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/withinterval BTCUSD 60",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_alias_bad_key(self, client):
        """Alias with wrong key — 403 (key checked before alias)."""
        async with client as c:
            resp = await c.post(
                "/webhook/wrong_key_pad_16",
                content="/spot BTCUSDT BINANCE 68000",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 403


class TestHumanizeInterval:
    """Unit tests for humanize_interval()."""

    @pytest.mark.parametrize("raw,expected", [
        ("1", "1min"),
        ("5", "5min"),
        ("15", "15min"),
        ("30", "30min"),
        ("45", "45min"),
        ("60", "1h"),
        ("120", "2h"),
        ("240", "4h"),
        ("360", "6h"),
        ("720", "12h"),
        ("90", "1h30min"),
        ("1D", "1D"),
        ("1W", "1W"),
        ("1M", "1M"),
        ("3M", "3M"),
    ])
    def test_humanize_interval(self, raw, expected):
        from aliases import humanize_interval
        assert humanize_interval(raw) == expected


class TestReloadConfig:
    @pytest.mark.asyncio
    async def test_valid_reload(self, client):
        """Reload with correct key — 200."""
        async with client as c:
            resp = await c.post("/reload-config", json={
                "key": "test_secret_key_123",
            })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bad_key_reload(self, client):
        """Reload with wrong key — 403."""
        async with client as c:
            resp = await c.post("/reload-config", json={
                "key": "wrong_key_padding_16",
            })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_key_reload(self, client):
        """Reload with empty key — 403."""
        async with client as c:
            resp = await c.post("/reload-config", json={
                "key": "",
            })
        assert resp.status_code == 403


class TestBodySizeLimit:
    @pytest.mark.asyncio
    async def test_body_too_large(self, client):
        """Body > 10KB — 413."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="x" * 11_000,
                headers={"content-type": "text/plain", "content-length": "11000"},
            )
        assert resp.status_code == 413


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers(self, client):
        """Security headers are set."""
        async with client as c:
            resp = await c.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
