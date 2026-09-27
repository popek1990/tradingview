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


class TestReloadFromFile:
    """B1 regression: panel edits the .env FILE, reload must pick that up."""

    def test_reload_reads_changed_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SEC_KEY", raising=False)
        monkeypatch.delenv("SEND_ALERTS_TELEGRAM_2", raising=False)
        env = tmp_path / ".env"
        env.write_text('SEC_KEY="old_key_at_least_16"\nSEND_ALERTS_TELEGRAM_2=True\n')
        assert get_settings().sec_key == "old_key_at_least_16"

        env.write_text('SEC_KEY="new_key_at_least_16"\nSEND_ALERTS_TELEGRAM_2=False\n')
        s = reload_settings()
        assert s.sec_key == "new_key_at_least_16"
        assert s.send_alerts_telegram_2 is False

    def test_main_does_not_copy_env_file_into_environ(self):
        """A copy in os.environ would shadow later edits of the file."""
        import main
        assert not hasattr(main, "load_dotenv")

    def test_fingerprint_changes_with_settings(self, monkeypatch):
        from config import settings_fingerprint
        before = settings_fingerprint(Settings())
        monkeypatch.setenv("CHANNEL_2", "-100777")
        assert settings_fingerprint(Settings()) != before
