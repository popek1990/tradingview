# ----------------------------------------------- #
# Nazwa projektu         : TradingView-Webhook-Bot #
# Plik                   : main.py                 #
# ----------------------------------------------- #

import asyncio
import hmac
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from config import pobierz_ustawienia, przeladuj_ustawienia
from handler import wyslij_alert
from szablony import renderuj, wczytaj_szablony

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
SCIEZKA_LOGOW = "logs/webhook.log"
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATEFMT,
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            SCIEZKA_LOGOW, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger(__name__)

# Rate limiting
# slowapi/starlette probuje czytac .env domyslnie, co powoduje PermissionError w Dockerze.
# Ustawiamy config=None, aby temu zapobiec.
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"], config_filename=None)

# Konfiguracja pydantic-settings, aby NIE czytal .env automatycznie w slowapi/starlette
# (Robimy to recznie w config.py przez BaseSettings)
os.environ["Pydantic_Settings_Source_File"] = "none"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Walidacja krytycznych ustawien przy starcie serwera."""
    ust = pobierz_ustawienia()
    if not ust.sec_key:
        logger.critical("SEC_KEY nie jest ustawiony! Serwer odmawia startu.")
        raise SystemExit(1)
    logger.info("Serwer uruchomiony — SEC_KEY skonfigurowany")
    yield


app = FastAPI(title="TradingView Webhook Bot", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def obsluz_rate_limit(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"status": "zbyt_wiele_zapytan"})


# Model walidacji payloadu (key opcjonalny — moze byc w URL)
class AlertPayload(BaseModel):
    model_config = {"extra": "forbid"}  # Odrzucaj nieznane pola

    key: str | None = None
    msg: str | None = Field(default=None, max_length=4000)
    szablon: str | None = None
    telegram: str | None = None
    discord: str | None = None
    slack: str | None = None


@app.get("/health")
async def health():
    """Endpoint healthcheck — status serwera i wlaczonych kanalow."""
    ust = pobierz_ustawienia()
    return {
        "status": "ok",
        "kanaly": {
            "telegram": ust.wyslij_alerty_telegram,
            "discord": ust.wyslij_alerty_discord,
            "slack": ust.wyslij_alerty_slack,
        },
    }


async def _obsluz_webhook(request: Request, klucz_z_url: str | None) -> dict:
    """Wspolna logika obslugi webhooka — JSON, plain text, szablony."""
    content_type = request.headers.get("content-type", "")

    szablon: str | None = None
    dane_json: dict = {}
    extra: dict = {}

    if "application/json" in content_type:
        # JSON — stary format (z key) lub nowy (bez key, z szablonem)
        try:
            dane_json = await request.json()
            payload = AlertPayload(**dane_json)
        except Exception as e:
            logger.warning("Nieprawidlowy payload: %s", e)
            raise HTTPException(status_code=400, detail="Nieprawidlowy payload")

        klucz = klucz_z_url or payload.key
        msg = payload.msg
        szablon = payload.szablon
        extra = payload.model_dump(exclude_none=True, exclude={"key", "msg", "szablon"})
    else:
        # Plain text — cale body to wiadomosc
        try:
            body = await request.body()
            msg = body.decode("utf-8").strip()
        except Exception:
            raise HTTPException(status_code=400, detail="Nie mozna odczytac body")

        if not msg or len(msg) > 4000:
            raise HTTPException(
                status_code=400,
                detail="Wiadomosc pusta lub za dluga (max 4000 znakow)",
            )
        klucz = klucz_z_url

    # Walidacja klucza
    if not klucz:
        raise HTTPException(status_code=400, detail="Brak klucza (podaj w URL lub JSON)")

    ust = pobierz_ustawienia()

    if not hmac.compare_digest(klucz, ust.sec_key):
        ip = request.client.host if request.client else "nieznany"
        logger.warning("Alert odrzucony (nieprawidlowy klucz) z IP: %s", ip)
        raise HTTPException(status_code=403, detail="Nieprawidlowy klucz")

    # Obsluga szablonow
    if szablon:
        try:
            msg = renderuj(szablon, dane_json)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Walidacja — msg musi istniec (albo z body, albo z szablonu, albo z JSON)
    if not msg:
        raise HTTPException(status_code=400, detail="Brak wiadomosci (msg lub szablon)")

    logger.info("Alert odebrany — wysylanie do kanalow...")
    dane_alertu = {"msg": msg, **extra}
    wyniki = await asyncio.to_thread(wyslij_alert, dane_alertu)

    if wyniki and not any(wyniki.values()):
        logger.error("Wszystkie kanaly zawiodly: %s", wyniki)
        raise HTTPException(status_code=502, detail="Wszystkie kanaly zawiodly")

    return {"status": "ok", "kanaly": wyniki}


@app.post("/webhook")
@limiter.limit("30/minute")
async def webhook(request: Request):
    """Endpoint webhook — stary format z kluczem w JSON body."""
    return await _obsluz_webhook(request, klucz_z_url=None)


@app.post("/webhook/{klucz}")
@limiter.limit("30/minute")
async def webhook_z_kluczem(request: Request, klucz: str):
    """Endpoint webhook — klucz w URL, body jako JSON lub plain text."""
    return await _obsluz_webhook(request, klucz_z_url=klucz)


@app.post("/przeladuj-config")
@limiter.limit("5/minute")
async def przeladuj_config(request: Request):
    """Przeladowuje konfiguracje z .env (uzywane przez panel Streamlit)."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidlowy payload")

    ust = pobierz_ustawienia()

    klucz = data.get("key", "")
    if not klucz or not hmac.compare_digest(klucz, ust.sec_key):
        raise HTTPException(status_code=403, detail="Nieprawidlowy klucz")

    przeladuj_ustawienia()
    logger.info("Konfiguracja przeladowana na zadanie z panelu")
    return {"status": "ok"}
