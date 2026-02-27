# ----------------------------------------------- #
# Nazwa projektu         : TradingView-Webhook-Bot #
# Plik                   : config.py               #
# ----------------------------------------------- #

import logging
import threading

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Ustawienia(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Klucz bezpieczenstwa — musi pasowac do "key" w alercie TradingView
    sec_key: str = ""

    # Haslo dostepu do panelu Streamlit
    dashboard_haslo: str = "admin"

    # Ustawienia Telegram
    wyslij_alerty_telegram: bool = True
    tg_token: str = ""
    kanal: str = "-1001929276330"

    # Ustawienia Discord
    wyslij_alerty_discord: bool = False
    discord_webhook: str = ""

    # Ustawienia Slack
    wyslij_alerty_slack: bool = False
    slack_webhook: str = ""


# Singleton z mozliwoscia przeladowania (thread-safe)
_lock = threading.Lock()
_ustawienia: Ustawienia | None = None


def pobierz_ustawienia() -> Ustawienia:
    """Zwraca aktualna instancje ustawien (tworzy przy pierwszym wywolaniu)."""
    global _ustawienia
    if _ustawienia is None:
        with _lock:
            if _ustawienia is None:
                _ustawienia = Ustawienia()
    return _ustawienia


def przeladuj_ustawienia() -> Ustawienia:
    """Przeladowuje ustawienia z .env (np. po zmianach w panelu Streamlit)."""
    global _ustawienia
    with _lock:
        _ustawienia = Ustawienia()
    logger.info("Konfiguracja przeladowana")
    return _ustawienia
