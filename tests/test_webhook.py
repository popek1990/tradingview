"""Testy endpointow FastAPI (webhook, health, reload)."""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def klient():
    """Klient HTTP do testow FastAPI."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def _szablony_testowe(tmp_path, monkeypatch):
    """Tworzy tymczasowy plik szablonow do testow."""
    import szablony as mod
    plik = tmp_path / "szablony.json"
    dane = {
        "target": {
            "tresc": "Alert: {ticker} na {exchange} cena {close}",
            "zmienne": ["ticker", "exchange", "close"],
        }
    }
    plik.write_text(json.dumps(dane), encoding="utf-8")
    monkeypatch.setattr(mod, "SCIEZKA_SZABLONOW", plik)


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_zwraca_ok(self, klient):
        async with klient as c:
            resp = await c.get("/health")
        assert resp.status_code == 200
        dane = resp.json()
        assert dane["status"] == "ok"
        assert "kanaly" in dane

    @pytest.mark.asyncio
    async def test_health_kanaly(self, klient):
        async with klient as c:
            resp = await c.get("/health")
        kanaly = resp.json()["kanaly"]
        assert "telegram" in kanaly
        assert "discord" in kanaly
        assert "slack" in kanaly


class TestWebhook:
    """Testy starego formatu — JSON z kluczem w body."""

    @pytest.mark.asyncio
    async def test_poprawny_payload(self, klient, monkeypatch):
        """Poprawny payload z dobrym kluczem — 200."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        async with klient as c:
            resp = await c.post("/webhook", json={
                "key": "test_secret_key_123",
                "msg": "Testowa wiadomosc",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_zly_klucz(self, klient):
        """Bledny klucz — 403."""
        async with klient as c:
            resp = await c.post("/webhook", json={
                "key": "zly_klucz",
                "msg": "Test",
            })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_brak_klucza(self, klient):
        """Brak pola key w JSON i brak klucza w URL — 400."""
        async with klient as c:
            resp = await c.post("/webhook", json={
                "msg": "Test",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_brak_msg(self, klient):
        """Brak pola msg — 400."""
        async with klient as c:
            resp = await c.post("/webhook", json={
                "key": "test_secret_key_123",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_za_dluga_wiadomosc(self, klient):
        """Wiadomosc > 4000 znakow — 400."""
        async with klient as c:
            resp = await c.post("/webhook", json={
                "key": "test_secret_key_123",
                "msg": "x" * 4001,
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_pusty_payload(self, klient):
        """Pusty JSON — 400."""
        async with klient as c:
            resp = await c.post("/webhook", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_nie_json_bez_klucza(self, klient):
        """Plain text na /webhook (bez klucza w URL) — 400."""
        async with klient as c:
            resp = await c.post(
                "/webhook",
                content="to nie json",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400


class TestWebhookKluczWUrl:
    """Testy nowego formatu — klucz w URL."""

    @pytest.mark.asyncio
    async def test_klucz_w_url_json(self, klient, monkeypatch):
        """Klucz w URL + JSON body bez pola key — 200."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        async with klient as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "msg": "Test z kluczem w URL",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_klucz_w_url_plain_text(self, klient, monkeypatch):
        """Klucz w URL + plain text body — 200."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        async with klient as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="Test plain text alert",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_klucz_w_url_zly(self, klient):
        """Zly klucz w URL — 403."""
        async with klient as c:
            resp = await c.post("/webhook/zly_klucz", json={
                "msg": "Test",
            })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_plain_text_pusty(self, klient):
        """Pusty plain text body — 400."""
        async with klient as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="",
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_plain_text_za_dlugi(self, klient):
        """Plain text > 4000 znakow — 400."""
        async with klient as c:
            resp = await c.post(
                "/webhook/test_secret_key_123",
                content="x" * 4001,
                headers={"content-type": "text/plain"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_klucz_url_nadpisuje_json(self, klient, monkeypatch):
        """Klucz w URL ma priorytet nad kluczem w JSON body."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        async with klient as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "key": "zly_klucz_w_json",
                "msg": "Test priorytetu klucza",
            })
        assert resp.status_code == 200


class TestWebhookSzablony:
    """Testy systemu szablonow."""

    @pytest.mark.asyncio
    async def test_szablon_poprawny(self, klient, monkeypatch, _szablony_testowe):
        """Szablon z poprawnymi zmiennymi — 200."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        async with klient as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "szablon": "target",
                "ticker": "SPX",
                "exchange": "TVC",
                "close": "6910",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_szablon_nieistniejacy(self, klient, _szablony_testowe):
        """Nieistniejacy szablon — 400."""
        async with klient as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "szablon": "nieistniejacy",
            })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_szablon_brakujace_zmienne(self, klient, monkeypatch, _szablony_testowe):
        """Szablon z brakujacymi zmiennymi — uzywane puste stringi."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        async with klient as c:
            resp = await c.post("/webhook/test_secret_key_123", json={
                "szablon": "target",
                "ticker": "SPX",
            })
        assert resp.status_code == 200


class TestPrzeladujConfig:
    @pytest.mark.asyncio
    async def test_poprawny_reload(self, klient):
        """Reload z poprawnym kluczem — 200."""
        async with klient as c:
            resp = await c.post("/przeladuj-config", json={
                "key": "test_secret_key_123",
            })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_zly_klucz_reload(self, klient):
        """Reload z blednym kluczem — 403."""
        async with klient as c:
            resp = await c.post("/przeladuj-config", json={
                "key": "zly_klucz",
            })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_pusty_klucz_reload(self, klient):
        """Reload z pustym kluczem — 403."""
        async with klient as c:
            resp = await c.post("/przeladuj-config", json={
                "key": "",
            })
        assert resp.status_code == 403
