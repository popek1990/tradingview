# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : main.py                 #
# ----------------------------------------------- #

import asyncio
import hmac
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Path, Request, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from config import get_settings, reload_settings
from handler import send_alert
from templates import render

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_PATH = "logs/webhook.log"
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATEFMT,
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_FILE_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger(__name__)

# Rate limiting — use CF-Connecting-IP behind Cloudflare Tunnel
def get_client_ip(request: Request) -> str:
    """Gets real client IP (CF-Connecting-IP > X-Forwarded-For > client.host)."""
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )

# slowapi/starlette tries to read .env by default, causing PermissionError in Docker.
# Set a non-existent file to prevent the library from opening it.
limiter = Limiter(key_func=get_client_ip, default_limits=["30/minute"], config_filename=".env.no_load")

# Prevent pydantic-settings from auto-reading .env in slowapi/starlette
os.environ["Pydantic_Settings_Source_File"] = "none"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validates critical settings at server startup."""
    settings = get_settings()
    
    env_path = ".env"
    if os.path.exists(env_path) and not os.access(env_path, os.R_OK):
        logger.critical("Permission denied to read .env! Please run 'chmod 664 .env' on the host machine.")
        raise SystemExit(1)

    if not settings.sec_key or len(settings.sec_key) < 16:
        logger.warning("SEC_KEY is missing or too short (min. 16 chars). Attempting to auto-generate...")
        try:
            import secrets
            from dotenv import set_key
            
            new_key = secrets.token_hex(32)
            # Create .env if it doesn't exist
            if not os.path.exists(env_path):
                open(env_path, 'a').close()
                os.chmod(env_path, 0o664)
                
            set_key(env_path, "SEC_KEY", new_key)
            settings.sec_key = new_key
            logger.info("Successfully auto-generated a new secure SEC_KEY and saved it to .env.")
        except Exception as e:
            logger.critical(f"Failed to auto-generate SEC_KEY: {e}. Please set SEC_KEY in .env manually or fix permissions (chmod 664 .env).")
            raise SystemExit(1)
            
    logger.info("Server started — SEC_KEY configured")
    yield


# Disabled /docs /redoc /openapi in production
app = FastAPI(
    title="TradingView Webhook Bot",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter

# Trusted Host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["tv.popeklab.com", "localhost", "127.0.0.1", "webhook", "test", "testserver"],
)


# Body size limit (max 10KB)
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10_000:
        return JSONResponse(status_code=413, content={"detail": "Payload too large"})
    return await call_next(request)


# Security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"status": "too_many_requests"})


# Payload validation model (key optional — can be in URL)
class AlertPayload(BaseModel):
    model_config = {"extra": "ignore"}  # Ignore unknown fields (safer in production)

    key: str | None = None
    msg: str | None = Field(default=None, max_length=4000)
    template: str | None = None
    telegram: str | None = None
    discord: str | None = None
    slack: str | None = None


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """Healthcheck endpoint — returns status only (no channel details)."""
    return {"status": "ok"}


async def _handle_webhook(request: Request, key_from_url: str | None) -> dict:
    """Shared webhook handling logic — JSON, plain text, templates."""
    content_type = request.headers.get("content-type", "")

    template_name: str | None = None
    json_data: dict = {}
    extra: dict = {}

    if "application/json" in content_type:
        # JSON — old format (with key) or new (without key, with template)
        try:
            json_data = await request.json()
            payload = AlertPayload(**json_data)
        except Exception:
            ip = request.client.host if request.client else "unknown"
            logger.warning("Invalid JSON payload from IP: %s", ip)
            raise HTTPException(status_code=400, detail="Invalid payload")

        key = key_from_url or payload.key
        msg = payload.msg
        template_name = payload.template
        extra = payload.model_dump(exclude_none=True, exclude={"key", "msg", "template"})
    else:
        # Plain text — entire body is the message
        try:
            body = await request.body()
            msg = body.decode("utf-8").strip()
        except Exception:
            raise HTTPException(status_code=400, detail="Cannot read body")

        if not msg or len(msg) > 4000:
            raise HTTPException(
                status_code=400,
                detail="Message empty or too long (max 4000 chars)",
            )
        key = key_from_url

    # Key validation
    if not key:
        raise HTTPException(status_code=400, detail="Missing key (provide in URL or JSON)")

    settings = get_settings()

    if not hmac.compare_digest(key, settings.sec_key):
        ip = request.client.host if request.client else "unknown"
        logger.warning("Alert rejected (invalid key) from IP: %s", ip)
        raise HTTPException(status_code=403, detail="Invalid key")

    # Template handling
    if template_name:
        try:
            msg = render(template_name, json_data)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Validation — msg must exist (from body, template, or JSON)
    if not msg:
        raise HTTPException(status_code=400, detail="Missing message (msg or template)")

    logger.info("Alert received — sending to channels...")
    alert_data = {"msg": msg, **extra}
    results = await asyncio.to_thread(send_alert, alert_data)

    if results and not any(results.values()):
        logger.error("All channels failed: %s", results)
        raise HTTPException(status_code=502, detail="All channels failed")

    return {"status": "ok", "channels": results}


@app.post("/webhook")
@limiter.limit("30/minute")
async def webhook(request: Request):
    """Webhook endpoint — old format with key in JSON body."""
    return await _handle_webhook(request, key_from_url=None)


@app.post("/webhook/{key}")
@limiter.limit("30/minute")
async def webhook_with_key(request: Request, key: str = Path(..., max_length=256)):
    """Webhook endpoint — key in URL, body as JSON or plain text."""
    return await _handle_webhook(request, key_from_url=key)


@app.post("/reload-config")
@limiter.limit("5/minute")
async def reload_config(request: Request):
    """Reloads configuration from .env (used by Streamlit panel).

    Restricted to internal Docker network (172.x) and localhost.
    """
    ip = get_client_ip(request)
    if not (ip.startswith("172.") or ip.startswith("127.") or ip == "localhost"):
        raise HTTPException(status_code=403, detail="Access only from internal network")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    settings = get_settings()

    key = data.get("key", "")
    if not key or not hmac.compare_digest(key, settings.sec_key):
        raise HTTPException(status_code=403, detail="Invalid key")

    reload_settings()
    logger.info("Configuration reloaded on request from panel")
    return {"status": "ok"}
