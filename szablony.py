# ----------------------------------------------- #
# Nazwa projektu         : TradingView-Webhook-Bot #
# Plik                   : szablony.py             #
# ----------------------------------------------- #

"""CRUD i renderowanie szablonow wiadomosci."""

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

SCIEZKA_SZABLONOW = Path(__file__).parent / "szablony.json"
_lock = threading.Lock()


def wczytaj_szablony() -> dict:
    """Wczytuje szablony z pliku JSON. Zwraca pusty dict jesli plik nie istnieje."""
    try:
        with _lock:
            return json.loads(SCIEZKA_SZABLONOW.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def zapisz_szablony(szablony: dict) -> None:
    """Zapisuje szablony do pliku JSON."""
    with _lock:
        SCIEZKA_SZABLONOW.write_text(
            json.dumps(szablony, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    logger.info("Szablony zapisane (%d szablonow)", len(szablony))


def renderuj(nazwa: str, zmienne: dict) -> str:
    """Renderuje szablon o podanej nazwie z podanymi zmiennymi.

    Raises:
        KeyError: jesli szablon nie istnieje
        ValueError: jesli brakuje zmiennej w danych
    """
    szablony = wczytaj_szablony()
    if nazwa not in szablony:
        raise KeyError(f"Szablon '{nazwa}' nie istnieje")

    szablon = szablony[nazwa]
    tresc = szablon["tresc"]
    wymagane = szablon.get("zmienne", [])

    # Podstaw zmienne — bezpieczny str.replace() zamiast str.format()
    wynik = tresc
    for k in wymagane:
        wynik = wynik.replace(f"{{{k}}}", str(zmienne.get(k, "")))
    return wynik
