"""Testy modulu konfiguracji."""

import os
import pytest
from config import Ustawienia, pobierz_ustawienia, przeladuj_ustawienia


class TestUstawienia:
    def test_domyslne_wartosci(self, monkeypatch):
        """Domyslne wartosci sa poprawne."""
        # Usuwamy env vars zeby sprawdzic domyslne
        for key in list(os.environ):
            if key in ("WYSLIJ_ALERTY_TELEGRAM", "WYSLIJ_ALERTY_DISCORD", "DASHBOARD_HASLO"):
                monkeypatch.delenv(key)
        ust = Ustawienia()
        assert ust.wyslij_alerty_discord is False
        assert ust.dashboard_haslo == "admin"

    def test_laduje_z_env(self):
        """Wartosci z env vars sa ladowane."""
        ust = Ustawienia()
        assert ust.sec_key == "test_secret_key_123"
        assert ust.dashboard_haslo == "test_haslo"

    def test_bool_z_env(self, monkeypatch):
        """Boolean parsowany z roznych formatow."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        ust = Ustawienia()
        assert ust.wyslij_alerty_telegram is True

        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "false")
        ust2 = Ustawienia()
        assert ust2.wyslij_alerty_telegram is False


class TestSingleton:
    def test_pobierz_ustawienia_singleton(self):
        """Dwa wywolania zwracaja te sama instancje."""
        ust1 = pobierz_ustawienia()
        ust2 = pobierz_ustawienia()
        assert ust1 is ust2

    def test_przeladuj_ustawienia(self, monkeypatch):
        """Przeladowanie tworzy nowa instancje."""
        ust1 = pobierz_ustawienia()
        monkeypatch.setenv("SEC_KEY", "nowy_klucz")
        ust2 = przeladuj_ustawienia()
        assert ust1 is not ust2
        assert ust2.sec_key == "nowy_klucz"
