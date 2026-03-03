# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : main.py                 #
# ----------------------------------------------- #

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import logging.handlers
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Path, Request, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from aliases import parse_alias
from config import get_settings, reload_settings
from handler import send_alert
from templates import render

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_PATH = "logs/webhook.log"
os.makedirs("logs", mode=0o750, exist_ok=True)

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


class SecKeyFilter(logging.Filter):
    """Masks webhook keys in URL paths: /webhook/ANYTHING → /webhook/***."""

    import re as _re
    _PATTERN = _re.compile(r"/webhook/[^/\s?#]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._PATTERN.sub("/webhook/***", record.msg)
        if hasattr(record, "args") and record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    self._PATTERN.sub("/webhook/***", a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


# Apply SecKeyFilter to root logger so all access logs get masked
logging.getLogger().addFilter(SecKeyFilter())
# Also apply to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(SecKeyFilter())

# Rate limiting — use CF-Connecting-IP behind Cloudflare Tunnel
def get_client_ip(request: Request) -> str:
    """Gets real client IP. Trusts CF-Connecting-IP (Cloudflare) or falls back to TCP peer."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    return request.client.host if request.client else "unknown"

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

    if not settings.sec_key:
        logger.critical("SEC_KEY is empty. Please set SEC_KEY in .env.")
        raise SystemExit(1)
    if len(settings.sec_key) < 16:
        logger.critical("SEC_KEY too short (%d chars, min 16). Update in .env.", len(settings.sec_key))
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
_default_hosts = "localhost,127.0.0.1,webhook"
_allowed_hosts = os.getenv("ALLOWED_HOSTS", _default_hosts).split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[h.strip() for h in _allowed_hosts],
)


# Body size limit (max 10KB) — checks actual body, not just Content-Length header
MAX_BODY_SIZE = 10_000

@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    # Quick reject via Content-Length header (before reading body)
    content_length = request.headers.get("content-length")
    try:
        if content_length and int(content_length) > MAX_BODY_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    # Verify actual body size (handles chunked encoding and lying clients)
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})

    return await call_next(request)


# Request-ID middleware — adds unique ID to each request for log correlation
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


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

    # Read body once
    try:
        body = await request.body()
        raw = body.decode("utf-8").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Cannot read body")

    # TradingView sometimes sends JSON with Content-Type: text/plain.
    # Detect JSON by Content-Type or by body starting with "{".
    ct = content_type.split(";")[0].strip().lower()
    is_json = ct == "application/json" or raw.startswith("{")

    if is_json:
        # JSON — old format (with key) or new (without key, with template)
        try:
            json_data = json.loads(raw)
            payload = AlertPayload(**json_data)
        except Exception:
            logger.warning("Invalid JSON payload from IP: %s", get_client_ip(request))
            raise HTTPException(status_code=400, detail="Invalid payload")

        key = key_from_url or payload.key
        msg = payload.msg
        template_name = payload.template
        extra = payload.model_dump(exclude_none=True, exclude={"key", "msg", "template"})
    else:
        # Plain text — entire body is the message
        msg = raw

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

    if not hmac.compare_digest(
        hashlib.sha256(key.encode()).digest(),
        hashlib.sha256(settings.sec_key.encode()).digest(),
    ):
        logger.warning("Alert rejected (invalid key) from IP: %s", get_client_ip(request))
        raise HTTPException(status_code=403, detail="Invalid key")

    # Alias handling (e.g., "/spot BTCUSDT BINANCE 68000")
    if msg and msg.startswith("/"):
        try:
            alias_result = parse_alias(msg)
            if alias_result is not None:
                msg = alias_result
        except (KeyError, ValueError) as e:
            logger.warning("Alias error from %s: %s", get_client_ip(request), e)
            raise HTTPException(status_code=400, detail="Invalid request")

    # Template handling
    if template_name:
        try:
            msg = render(template_name, json_data)
        except (KeyError, ValueError) as e:
            logger.warning("Template error from %s: %s", get_client_ip(request), e)
            raise HTTPException(status_code=400, detail="Invalid request")

    # Validation — msg must exist (from body, template, or JSON)
    if not msg:
        raise HTTPException(status_code=400, detail="Missing message (msg or template)")

    logger.info("Alert received — sending to channels...")
    alert_data = {"msg": msg, **extra}
    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(send_alert, alert_data), timeout=30
        )
    except asyncio.TimeoutError:
        logger.error("Alert dispatch timed out (30s)")
        raise HTTPException(status_code=504, detail="Alert dispatch timed out")

    if not results:
        logger.warning("No channels enabled — alert not sent")
        return {"status": "warning", "detail": "No channels enabled", "channels": {}}

    if not any(results.values()):
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
    """Webhook endpoint — key in URL (deprecated), body as JSON or plain text."""
    logger.warning(
        "DEPRECATED: key in URL path from %s — use POST /webhook with key in JSON body",
        get_client_ip(request),
    )
    return await _handle_webhook(request, key_from_url=key)


@app.post("/reload-config")
@limiter.limit("5/minute")
async def reload_config(request: Request):
    """Reloads configuration from .env (used by Streamlit panel).

    Restricted to internal Docker network (172.x) and localhost.
    """
    # Use actual TCP source IP for access control (not spoofable headers)
    raw_ip = request.client.host if request.client else None
    if not raw_ip:
        raise HTTPException(status_code=403, detail="Access only from internal network")

    _PRIVATE_NETWORKS = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
    )
    try:
        addr = ipaddress.ip_address(raw_ip)
        is_internal = any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        is_internal = False

    if not is_internal:
        raise HTTPException(status_code=403, detail="Access only from internal network")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    settings = get_settings()

    key = data.get("key", "")
    if not key or not hmac.compare_digest(
        hashlib.sha256(key.encode()).digest(),
        hashlib.sha256(settings.sec_key.encode()).digest(),
    ):
        raise HTTPException(status_code=403, detail="Invalid key")

    reload_settings()
    logger.info("Configuration reloaded on request from panel")
    return {"status": "ok"}
