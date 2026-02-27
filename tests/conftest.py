"""Wspoldzielone fixtures dla testow."""

import os
import pytest

# Ustawienia testowe — nadpisujemy zmienne srodowiskowe PRZED importem modulow
TEST_ENV = {
    "SEC_KEY": "test_secret_key_123",
    "DASHBOARD_HASLO": "test_haslo",
    "TG_TOKEN": "fake_tg_token",
    "KANAL": "-100123456",
    "WYSLIJ_ALERTY_TELEGRAM": "False",
    "WYSLIJ_ALERTY_DISCORD": "False",
    "WYSLIJ_ALERTY_SLACK": "False",
    "KANAL_2": "",
    "DISCORD_WEBHOOK": "",
    "SLACK_WEBHOOK": "",
}


@pytest.fixture(autouse=True)
def _wyczysc_singleton():
    """Resetuje singleton ustawien przed kazdym testem."""
    import config
    config._ustawienia = None
    yield
    config._ustawienia = None


@pytest.fixture(autouse=True)
def _env_testowy(monkeypatch, tmp_path):
    """Ustawia zmienne srodowiskowe testowe i tworzy tymczasowy .env."""
    for klucz, wartosc in TEST_ENV.items():
        monkeypatch.setenv(klucz, wartosc)

    # Tymczasowy .env (pydantic-settings czyta z env vars, nie z pliku w testach)
    env_plik = tmp_path / ".env"
    env_plik.write_text("")
    monkeypatch.chdir(tmp_path)

    # Katalog logs dla RotatingFileHandler
    (tmp_path / "logs").mkdir(exist_ok=True)
