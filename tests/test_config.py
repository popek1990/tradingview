"""Tests for configuration module."""

import os
import pytest
from config import Settings, get_settings, reload_settings


class TestSettings:
    def test_default_values(self, monkeypatch):
        """Default values are correct."""
        for key in list(os.environ):
            if key in ("SEND_ALERTS_TELEGRAM", "SEND_ALERTS_DISCORD", "DASHBOARD_PASSWORD"):
                monkeypatch.delenv(key)
        settings = Settings()
        assert settings.send_alerts_discord is False
        assert settings.dashboard_password == ""

    def test_loads_from_env(self):
        """Values from env vars are loaded."""
        settings = Settings()
        assert settings.sec_key == "test_secret_key_123"
        assert settings.dashboard_password == "test_password"

    def test_bool_from_env(self, monkeypatch):
        """Boolean parsed from various formats."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        settings = Settings()
        assert settings.send_alerts_telegram is True

        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "false")
        settings2 = Settings()
        assert settings2.send_alerts_telegram is False


class TestSingleton:
    def test_get_settings_singleton(self):
        """Two calls return the same instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reload_settings(self, monkeypatch):
        """Reload creates a new instance."""
        s1 = get_settings()
        monkeypatch.setenv("SEC_KEY", "new_key_at_least_16")
        s2 = reload_settings()
        assert s1 is not s2
        assert s2.sec_key == "new_key_at_least_16"
