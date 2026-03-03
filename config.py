# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : config.py               #
# ----------------------------------------------- #

import logging
import threading

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Security key — must match "key" in TradingView alert
    sec_key: str = ""

    # Dashboard access password (required — no default)
    dashboard_password: str = ""

    # Telegram settings
    send_alerts_telegram: bool = True
    send_alerts_telegram_2: bool = False
    tg_token: str = ""
    channel: str = ""
    channel_2: str = ""            # Second Telegram group (optional)

    # Discord settings
    send_alerts_discord: bool = False
    discord_webhook: str = ""

    # Slack settings
    send_alerts_slack: bool = False
    slack_webhook: str = ""


# Thread-safe singleton with reload capability
_lock = threading.Lock()
_settings: Settings | None = None


def get_settings() -> Settings:
    """Returns the current settings instance (creates on first call)."""
    global _settings
    if _settings is None:
        with _lock:
            if _settings is None:
                try:
                    _settings = Settings()
                except Exception as e:
                    logger.error("CRITICAL ERROR: Failed to load configuration: %s", e)
                    try:
                        _settings = Settings(_env_file=None)
                    except Exception as e2:
                        raise RuntimeError(f"Cannot load configuration: {e2}") from e
    return _settings


def reload_settings() -> Settings:
    """Reloads settings from .env (e.g. after changes in Streamlit panel)."""
    global _settings
    with _lock:
        try:
            _settings = Settings()
            logger.info("Configuration reloaded from .env")
        except Exception as e:
            logger.warning("Problem reloading .env: %s. Using old data.", e)
            if _settings is None:
                raise RuntimeError(f"Cannot load configuration: {e}") from e
    return _settings
