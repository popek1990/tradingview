"""Security-focused tests — extends test_webhook.py with dedicated security coverage."""

import hmac
import hashlib
import secrets
import time
import json

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    """HTTP client for FastAPI tests."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestSecurityHeaders:
    """Full security header coverage (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)."""

    @pytest.mark.asyncio
    async def test_all_security_headers(self, client):
        async with client as c:
            resp = await c.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "max-age=" in resp.headers.get("Strict-Transport-Security", "")
        assert resp.headers.get("Content-Security-Policy") == "default-src 'none'"

    @pytest.mark.asyncio
    async def test_security_headers_on_error(self, client):
        """Security headers are also present on error responses."""
        async with client as c:
            resp = await c.post("/webhook", json={"msg": "no key"})
        assert resp.status_code == 400
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"


class TestDocsDisabled:
    """OpenAPI docs endpoints must be disabled in production."""

    @pytest.mark.asyncio
    async def test_docs_returns_404(self, client):
        async with client as c:
            resp = await c.get("/docs")
        assert resp.status_code in (404, 405)

    @pytest.mark.asyncio
    async def test_redoc_returns_404(self, client):
        async with client as c:
            resp = await c.get("/redoc")
        assert resp.status_code in (404, 405)

    @pytest.mark.asyncio
    async def test_openapi_json_returns_404(self, client):
        async with client as c:
            resp = await c.get("/openapi.json")
        assert resp.status_code in (404, 405)


class TestSSRFValidation:
    """Tests for _validate_webhook_url() — SSRF protection on Discord/Slack URLs."""

    def test_valid_discord_url(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://discord.com/api/webhooks/123/abc",
            "discord.com", "/api/webhooks/",
        ) is True

    def test_valid_slack_url(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://hooks.slack.com/services/T/B/X",
            "hooks.slack.com", "/services/",
        ) is True

    def test_rejects_http(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "http://discord.com/api/webhooks/123/abc",
            "discord.com", "/api/webhooks/",
        ) is False

    def test_rejects_wrong_host(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://evil.com/api/webhooks/123/abc",
            "discord.com", "/api/webhooks/",
        ) is False

    def test_rejects_query_string(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://discord.com/api/webhooks/123/abc?redirect=evil.com",
            "discord.com", "/api/webhooks/",
        ) is False

    def test_rejects_fragment(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://discord.com/api/webhooks/123/abc#frag",
            "discord.com", "/api/webhooks/",
        ) is False

    def test_rejects_path_traversal(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://discord.com/api/webhooks/../../etc/passwd",
            "discord.com", "/api/webhooks/",
        ) is False

    def test_rejects_wrong_prefix(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url(
            "https://discord.com/other/path/123",
            "discord.com", "/api/webhooks/",
        ) is False

    def test_rejects_empty_url(self):
        from handler import _validate_webhook_url
        assert _validate_webhook_url("", "discord.com", "/api/webhooks/") is False


class TestTokenValidation:
    """Tests for auth token creation and validation."""

    def test_valid_token(self):
        from auth import _create_token, _validate_token
        secret = "test_secret_password"
        token = _create_token(secret)
        assert _validate_token(token, secret) is True

    def test_invalid_signature(self):
        from auth import _create_token, _validate_token
        token = _create_token("correct_secret")
        assert _validate_token(token, "wrong_secret") is False

    def test_expired_token(self):
        from auth import _validate_token, SESSION_TTL
        # Create token with timestamp far in the past (new 3-part format)
        ts = str(int(time.time()) - SESSION_TTL - 100)
        nonce = secrets.token_hex(16)
        payload = f"{ts}.{nonce}"
        sig = hmac.new("secret".encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = f"{ts}.{nonce}.{sig}"
        assert _validate_token(token, "secret") is False

    def test_malformed_token_no_dot(self):
        from auth import _validate_token
        assert _validate_token("nodottoken", "secret") is False

    def test_malformed_token_too_many_parts(self):
        from auth import _validate_token
        assert _validate_token("a.b.c.d", "secret") is False

    def test_malformed_token_two_parts(self):
        from auth import _validate_token
        assert _validate_token("a.b", "secret") is False

    def test_malformed_token_empty(self):
        from auth import _validate_token
        assert _validate_token("", "secret") is False

    def test_blacklisted_token(self):
        from auth import _create_token, _validate_token, _get_invalidated_tokens
        secret = "test_secret_password"
        token = _create_token(secret)
        assert _validate_token(token, secret) is True
        # Blacklist the token
        _get_invalidated_tokens()[token] = time.time() + 3600
        assert _validate_token(token, secret) is False

    def test_token_uniqueness(self):
        """Two tokens created with the same secret must differ (nonce)."""
        from auth import _create_token
        secret = "test_secret_password"
        t1 = _create_token(secret)
        t2 = _create_token(secret)
        assert t1 != t2

    def test_token_has_three_parts(self):
        """Token format must be timestamp.nonce.signature."""
        from auth import _create_token
        token = _create_token("secret")
        parts = token.split(".")
        assert len(parts) == 3
        # First part is numeric timestamp
        assert parts[0].isdigit()
        # Second part is hex nonce (32 hex chars = 16 bytes)
        assert len(parts[1]) == 32
        assert all(c in "0123456789abcdef" for c in parts[1])


class TestInvalidatedTokensPath:
    """P5: invalidated_tokens.json must be in logs/ (Docker named volume)."""

    def test_invalidated_tokens_in_logs_dir(self):
        from auth import INVALIDATED_TOKENS_FILE
        assert INVALIDATED_TOKENS_FILE.parent.name == "logs"


class TestEmptySECKEYValidation:
    """Regression test for #3 — dashboard must reject empty SEC_KEY."""

    @pytest.mark.asyncio
    async def test_webhook_rejects_empty_key(self, client):
        """Webhook rejects request with empty key."""
        async with client as c:
            resp = await c.post("/webhook", json={"key": "", "msg": "test"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_rejects_missing_key(self, client):
        """Webhook rejects request with no key field."""
        async with client as c:
            resp = await c.post("/webhook", json={"msg": "test"})
        assert resp.status_code == 400


class TestGenericErrorMessages:
    """Verify alias/template errors return generic messages (no internal details)."""

    @pytest.fixture(autouse=True)
    def _test_aliases(self, tmp_path, monkeypatch):
        import aliases as mod
        file = tmp_path / "aliases.json"
        data = {
            "spot": {
                "variables": ["ticker", "exchange", "close"],
                "template": "Target #{ticker} on {exchange} price {close}",
            },
        }
        file.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(mod, "ALIASES_FILE", file)

    @pytest.mark.asyncio
    async def test_alias_error_generic_message(self, client):
        """Unknown alias returns generic 'Invalid request', not internal details."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/nonexistent",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid request"
        assert "Unknown alias" not in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_alias_wrong_args_generic_message(self, client):
        """Wrong arg count returns generic 'Invalid request'."""
        async with client as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="/spot BTCUSDT",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid request"


class TestDeprecationWarning:
    """Verify /webhook/{key} endpoint logs deprecation warning + sunset headers."""

    @pytest.mark.asyncio
    async def test_key_in_url_still_works(self, client, monkeypatch):
        """Deprecated endpoint still functions (backwards compatible)."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "msg": "Test deprecated endpoint",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "warning")

    @pytest.mark.asyncio
    async def test_sunset_headers_present(self, client, monkeypatch):
        """P6: /webhook/{key} must include Deprecation and Sunset headers."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        async with client as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "msg": "Test sunset headers",
            })
        assert resp.headers.get("Deprecation") == "true"
        assert resp.headers.get("Sunset") == "2026-06-01"


class TestHmacKeyIndependence:
    """P4: HMAC signing key must be independent of the dashboard password."""

    def test_get_hmac_key_returns_stable_key(self, tmp_path, monkeypatch):
        """_get_hmac_key() generates and persists a key."""
        import auth
        key_file = tmp_path / ".hmac_key"
        monkeypatch.setattr(auth, "_HMAC_KEY_FILE", key_file)
        key1 = auth._get_hmac_key()
        key2 = auth._get_hmac_key()
        assert key1 == key2
        assert len(key1) == 64  # 32 bytes = 64 hex chars

    def test_hmac_key_independent_of_password(self, tmp_path, monkeypatch):
        """Token signed with HMAC key validates regardless of password change."""
        import auth
        key_file = tmp_path / ".hmac_key"
        monkeypatch.setattr(auth, "_HMAC_KEY_FILE", key_file)
        hmac_key = auth._get_hmac_key()
        token = auth._create_token(hmac_key)
        # Token validates with HMAC key, not with any password
        assert auth._validate_token(token, hmac_key) is True
        assert auth._validate_token(token, "some_password") is False
