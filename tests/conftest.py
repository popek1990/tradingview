"""Shared test fixtures."""

import os
import pytest

# Test settings — override env vars BEFORE importing modules
TEST_ENV = {
    "SEC_KEY": "test_secret_key_123",
    "DASHBOARD_PASSWORD": "test_password",
    "TG_TOKEN": "fake_tg_token",
    "CHANNEL": "-100123456",
    "SEND_ALERTS_TELEGRAM": "False",
    "SEND_ALERTS_DISCORD": "False",
    "SEND_ALERTS_SLACK": "False",
    "CHANNEL_2": "",
    "DISCORD_WEBHOOK": "",
    "SLACK_WEBHOOK": "",
}


@pytest.fixture(autouse=True)
def _clear_singleton():
    """Resets settings singleton and handler caches before each test."""
    import config
    import handler
    config._settings = None
    # Reset Telegram bot cache
    handler._tg_bot_cache = None
    with handler._tg_names_lock:
        handler._tg_names_cache.clear()
    yield
    config._settings = None


@pytest.fixture(autouse=True)
def _test_env(monkeypatch, tmp_path):
    """Sets test env vars and creates temporary .env file."""
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)

    # Temporary .env (pydantic-settings reads from env vars, not file in tests)
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.chdir(tmp_path)

    # Logs directory for RotatingFileHandler
    (tmp_path / "logs").mkdir(exist_ok=True)
