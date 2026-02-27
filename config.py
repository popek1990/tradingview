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

    # Haslo dostepu do panelu Streamlit (wymagane — brak domyslnego)
    dashboard_haslo: str = ""

    # Ustawienia Telegram
    wyslij_alerty_telegram: bool = True
    wyslij_alerty_telegram_2: bool = False
    tg_token: str = ""
    kanal: str = "-1001929276330"
    kanal_2: str = ""            # Druga grupa Telegram (opcjonalna)

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
                try:
                    _ustawienia = Ustawienia()
                except Exception as e:
                    logger.error(f"BLAD krytyczny: Nie udalo sie wczytac konfiguracji: {e}")
                    # Proba zaladowania bez pliku .env (tylko z os.environ)
                    _ustawienia = Ustawienia(_env_file=None)
    return _ustawienia


def przeladuj_ustawienia() -> Ustawienia:
    """Przeladowuje ustawienia z .env (np. po zmianach w panelu Streamlit)."""
    global _ustawienia
    with _lock:
        try:
            _ustawienia = Ustawienia()
            logger.info("Konfiguracja przeladowana z .env")
        except Exception as e:
            logger.warning(f"Problem przy przeladowaniu .env: {e}. Uzywam starych danych.")
    return _ustawienia
