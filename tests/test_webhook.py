"""Testy endpointow FastAPI (webhook, health, reload)."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def klient():
    """Klient HTTP do testow FastAPI."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


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
        """Brak pola key — 400."""
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
    async def test_nie_json(self, klient):
        """Nie-JSON body — 400."""
        async with klient as c:
            resp = await c.post("/webhook", content="to nie json", headers={"content-type": "text/plain"})
        assert resp.status_code == 400


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
