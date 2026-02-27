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
limiter = Limiter(key_func=get_remote_address)


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


# Model walidacji payloadu
class AlertPayload(BaseModel):
    key: str
    msg: str = Field(max_length=4000)
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


@app.post("/webhook")
@limiter.limit("30/minute")
async def webhook(request: Request):
    """Glowny endpoint — odbiera alerty z TradingView."""
    try:
        data = await request.json()
        payload = AlertPayload(**data)
    except Exception as e:
        logger.warning("Nieprawidlowy payload: %s", e)
        raise HTTPException(status_code=400, detail="Nieprawidlowy payload")

    ust = pobierz_ustawienia()

    if not hmac.compare_digest(payload.key, ust.sec_key):
        ip = request.client.host if request.client else "nieznany"
        logger.warning("Alert odrzucony (nieprawidlowy klucz) z IP: %s", ip)
        raise HTTPException(status_code=403, detail="Nieprawidlowy klucz")

    logger.info("Alert odebrany — wysylanie do kanalow...")
    wyniki = await asyncio.to_thread(wyslij_alert, payload.model_dump(exclude_none=True))

    if wyniki and not any(wyniki.values()):
        logger.error("Wszystkie kanaly zawiodly: %s", wyniki)
        raise HTTPException(status_code=502, detail="Wszystkie kanaly zawiodly")

    return {"status": "ok", "kanaly": wyniki}


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
