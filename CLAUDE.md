# CLAUDE.md

This file contains guidelines for AI assistants working with this repository.

## Core Rules

1. **Language**: All responses, explanations, plans and commit messages must be in **English**.
2. **Docker**: Do **NOT** automatically run `docker build`, `docker compose build` or `docker compose up`. The app runs in Docker on another machine and the user handles rebuilds and restarts after changes.

## Project Description

TradingView-Webhook-Bot — webhook server (FastAPI) receiving alerts from TradingView and forwarding them to channels: Telegram, Discord, Slack. Has a Streamlit admin panel for configuration management via browser.

**Requirements:** Python 3.12+

## Running

```bash
# Docker (recommended) — production
docker compose up -d --build
# -> webhook: https://tv.popeklab.com/webhook (via Cloudflare Tunnel)
# -> panel:   https://panel.popeklab.com (via Cloudflare Tunnel)
# -> panel LAN: http://SERVER_IP:8501

Subdomain: tv.popeklab.com > Service: http://localhost:80
Subdomain: tvpanel.popeklab.com > Service: http://localhost:8501

# Cloudflare configuration
Main domain: popeklab.com
Page Shield: enabled
Bot Fight mode: disabled (blocks TradingView)
Leaked credentials mitigation: Activated
DDoS/SSL/TLS protection: enabled

# Locally — webhook
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 80

# Locally — Streamlit panel (separate terminal)
streamlit run Dashboard.py

# Tests (requires venv with installed requirements.txt)
pytest                       # all tests
pytest tests/test_handler.py # single file
pytest -k "test_telegram"   # tests by name
```

### Deployment on new server

```bash
git clone https://github.com/popek1990/Tradingview.git
cd Tradingview
# Create .env with credentials (not in repo)
cat > .env << 'EOF'
SEC_KEY=your_key
DASHBOARD_PASSWORD=your_password
TG_TOKEN=your_telegram_token
DISCORD_WEBHOOK=
SLACK_WEBHOOK=
EOF
docker compose up -d --build
```

## Repository

- **GitHub:** https://github.com/popek1990/Tradingview (private)
- **Branch:** main
- `.env` and `plan.md` are in `.gitignore` — NOT tracked in repo

## Dependencies (requirements.txt)

| Package | Version | Role |
|---|---|---|
| `fastapi` | >=0.104.0 | HTTP framework (webhook, health, reload) |
| `uvicorn[standard]` | >=0.24.0 | ASGI server |
| `pydantic-settings` | >=2.1.0 | `Settings(BaseSettings)` class — config from .env |
| `python-dotenv` | >=1.0.0 | `set_key()` for writing .env from Streamlit panel |
| `python-telegram-bot` | ==13.6 | Sync Telegram API (v13, NOT v20+) |
| `urllib3` | <2 | Required by python-telegram-bot 13.6 (v2 removed needed modules) |
| `discord-webhook` | >=1.0.0 | Sending embeds to Discord |
| `requests` | >=2.28.0 | HTTP client (Slack webhook, healthcheck) |
| `slowapi` | >=0.1.9 | Rate limiting for endpoints |
| `streamlit` | >=1.30.0 | Admin panel |
| `extra-streamlit-components` | >=0.1.71 | Cookie manager for auth sessions |
| `pytest` | >=7.0.0 | Test framework |
| `pytest-asyncio` | >=0.21.0 | Async tests (FastAPI endpoints) |
| `httpx` | >=0.24.0 | AsyncClient for FastAPI tests |

## File Structure

```
Tradingview/
  main.py                  # FastAPI — webhook, health, reload endpoints + file logging
  handler.py               # Alert dispatcher to channels (Telegram, Discord, Slack)
  config.py                # Pydantic BaseSettings — configuration (single source of truth)
  templates.py             # CRUD and rendering of message templates
  templates.json           # Templates file (mounted as Docker volume)
  auth.py                  # Password auth + cookie sessions + logout
  ui_utils.py              # Shared UI functions: header, status dots, CSS, layout
  Dashboard.py             # Streamlit dashboard (main page)
  viking_logo.jpg          # Logo displayed in panel header
  pages/
    1_Configuration.py     # Edit keys/tokens in .env
    2_Channels.py          # Channel toggles + channel settings
    3_Test.py              # Manual test alert sending
    4_Logs.py              # Webhook server log viewer
    5_Templates.py         # Message template management
  tests/
    __init__.py            # Test package marker
    conftest.py            # Test fixtures (env, singleton reset)
    test_config.py         # Configuration and parsing tests
    test_webhook.py        # FastAPI endpoint tests
    test_handler.py        # Handler tests with mocked channels
  .env                     # Sensitive data (tokens, passwords) — in .gitignore, NOT in repo
  .gitignore               # Ignored files (venv, __pycache__, .env, plan.md, backups)
  .dockerignore            # Excluded from Docker image (git, venv, backups, *.md)
  .streamlit/
    config.toml            # Streamlit config (theme, XSRF, CORS, headless)
  Dockerfile               # Webhook image (python:3.12-slim, port 1990)
  Dockerfile.streamlit     # Streamlit panel image (port 8501)
  docker-compose.yml       # Two services: webhook + dashboard + logs volume + templates
  pytest.ini               # Pytest config (asyncio_mode=auto)
  requirements.txt         # Dependencies (production + test)
  README.md                # Project README
  CLAUDE.md                # Instructions for Claude Code
  logs/                    # Server logs (auto-created, shared Docker volume)
```

## Architecture and Logic

### FastAPI Endpoints (main.py)

| Endpoint | Method | Description | Rate limit |
|---|---|---|---|
| `/webhook` | POST | Receives TradingView alerts (key in JSON body) | 30/min |
| `/webhook/{key}` | POST | Receives alerts — key in URL, body as JSON or plain text | 30/min |
| `/health` | GET | Healthcheck (status only) | 60/min |
| `/reload-config` | POST | Reloads config from .env (internal Docker network only) | 5/min |

At server startup (`lifespan` context manager) critical settings are validated — if `SEC_KEY` is empty or shorter than 16 chars, server refuses to start (`SystemExit(1)`).

Logs written to `logs/webhook.log` (RotatingFileHandler, max 5MB, 3 backups) + stdout.

### Webhook Formats (3 usage modes)

**1. Old format — JSON with key in body (backwards compatible):**
```
POST /webhook
Body: {"key": "KEY", "msg": "alert content", "telegram?": "...", "discord?": "...", "slack?": "..."}
```

**2. New format — key in URL + plain text (simplest):**
```
POST /webhook/KEY
Content-Type: text/plain
Body: alert content (with Markdown, newlines as line breaks)
```

**3. New format — key in URL + template:**
```
POST /webhook/KEY
Body: {"template": "target", "ticker": "SPX", "exchange": "TVC", "close": "6910"}
```

### Alert Flow

```
TradingView
  -> POST /webhook or /webhook/{key}
  -> detect Content-Type: application/json vs text/plain
  -> if JSON: Pydantic validation (AlertPayload)
  -> if plain text: entire body = message (max 4000 chars)
  -> key: from URL (priority) or from JSON body
  -> key comparison: hmac.compare_digest(key, sec_key)
  -> if template: render(name, variables) from templates.json
  -> results = await asyncio.to_thread(send_alert, alert_data)
     -> each enabled channel (Telegram/Discord/Slack)
        -> data.get("channel") or default_from_config
        -> returns {channel: True/False}
  -> HTTP 200 {"status": "ok", "channels": {channel: success}}
  -> HTTP 502 if ALL channels failed
  -> or HTTP 400/403/429 on errors
```

### Message Templates (templates.py)

- `templates.json` — JSON file with template definitions (mounted as Docker volume)
- `load_templates()` / `save_templates()` — CRUD operations (thread-safe with `threading.Lock()`)
- `render(name, variables)` — substitutes variables in template (`str.replace()`)
- Managed from Streamlit dashboard (`pages/5_Templates.py`)

### Configuration (config.py)

`Settings(BaseSettings)` class from pydantic-settings — **single source of truth** for entire project:
- Pydantic loads variables from `.env` (via `SettingsConfigDict(env_file=".env")`). In Docker, `.env` is mounted as volume (docker-compose does NOT use `env_file:` directive — Pydantic reads it directly).
- Non-sensitive data (channel flags, channel ID) have default values in class
- Thread-safe singleton: `get_settings()` — `threading.Lock()` with double-checked locking (used by webhook server)
- Fresh read: `Settings()` — direct instance (used by Streamlit panel, reads current .env)
- Reload: `reload_settings()` — creates new instance from current `.env` (under lock)

### Handler (handler.py)

- `send_alert(data: dict) -> dict[str, bool]` — synchronous function, called in thread via `asyncio.to_thread()`. Returns send results for each channel.
- `NETWORK_TIMEOUT = 10` — timeout for all network operations (Telegram, Discord, Slack)
- Telegram bot cached: `_get_tg_bot(token)` — thread-safe with `threading.Lock()`, invalidated on token change
- Discord URL — handles full URLs and IDs only (auto-prefix). Embed: title (max 256 chars) + description (up to 4096 chars) for long messages.
- Slack — direct `requests.post()` with timeout. Response text verification (`"ok"` = success).
- Logging via `logging` (not print)

### Streamlit Panel

- **Configuration:** All pages use `Settings()` from config.py (not `dotenv_values`). Single source of truth for default values. Writes to `.env` via `set_key()` from python-dotenv.
- `auth.py` — `check_login()` compares password with `DASHBOARD_PASSWORD` (`hmac.compare_digest`), brute-force protection (max 10 attempts, 15 min lockout), random server-side session token (`secrets.token_hex(32)`, valid 24h), session cookie (`extra-streamlit-components`).
- `ui_utils.py` — Shared UI functions: `render_ui_header()` (logo, status dots, logout), `check_system_status()` (healthcheck with 30s cache), `save_and_reload()` (.env write + server reload), `safe_html()` (XSS protection), constants `WEBHOOK_URL` and `ENV_FILE_PATH`, custom CSS (dark theme overrides).
- `Dashboard.py` — Dashboard: key statuses (configured/missing), credentials verification
- `pages/1_Configuration.py` — Edit tokens/keys, write to `.env` via `set_key()` with success verification, auto-reload server
- `pages/2_Channels.py` — Channel toggles + settings (TG channel)
- `pages/3_Test.py` — Manual test alert sending through full `/webhook` pipeline
- `pages/4_Logs.py` — Server log viewer: level filtering (ERROR/WARNING/INFO), search, configurable range
- `pages/5_Templates.py` — Message template management: list, add, edit, delete, preview, TradingView JSON generation
- Server communication: `WEBHOOK_URL` (env var, default `http://webhook:1990` in Docker, `http://localhost:80` locally)
- `.streamlit/config.toml` — Streamlit config: dark theme, headless mode, XSRF and CORS enabled

### Docker

- **Dockerfile** — `python:3.12-slim`, non-root user (`appuser`), EXPOSE 1990, HEALTHCHECK on `/health`, graceful shutdown (`--timeout-graceful-shutdown 10`), `.env` NOT copied (mounted as read-only volume).
- **Dockerfile.streamlit** — separate image, root user (needed for writing templates.json and .env from bind mount), port 8501, HEALTHCHECK on `/_stcore/health`
- **docker-compose.yml** — service `webhook` (127.0.0.1:80->1990, 256M RAM, 0.5 CPU, `.env` read-only) + service `dashboard` (0.0.0.0:8501, 512M RAM, 0.5 CPU), shared `.env`, `templates.json` and `logs` (named volume). Port 80 localhost only — internet traffic via Cloudflare Tunnel. Dashboard available on LAN and via Cloudflare Tunnel (`panel.popeklab.com`). Resource limits + `security_opt: no-new-privileges`.

### Environment Variables in .env

Sensitive: `SEC_KEY`, `DASHBOARD_PASSWORD`, `TG_TOKEN`, `DISCORD_WEBHOOK`, `SLACK_WEBHOOK`

Optional overrides: `SEND_ALERTS_TELEGRAM`, `SEND_ALERTS_TELEGRAM_2`, `SEND_ALERTS_DISCORD`, `SEND_ALERTS_SLACK`, `CHANNEL`

## Important Notes

- **`.env` NEVER goes into repo or Docker image** — it's in `.gitignore`. Do not commit or push. Contains tokens, passwords and API keys. Mounted as volume in Docker.
- **Dashboard** — port 8501 open on `0.0.0.0` (LAN access). Also available via Cloudflare Tunnel as `https://panel.popeklab.com`. Protected by password (`DASHBOARD_PASSWORD`) + brute-force protection + session expiry.
- **Port 80** mapped to `127.0.0.1:80` — internet access via Cloudflare Tunnel (`https://tv.popeklab.com`). Do not open on `0.0.0.0`.
- **Cloudflare Tunnel** — `cloudflared` on Proxmox host. Two public hostnames: `tv.popeklab.com` → `localhost:80` (webhook), `panel.popeklab.com` → `localhost:8501` (dashboard). Domain: `popeklab.com` (Cloudflare Registrar, WHOIS hidden). Zero open ports externally, server IP hidden.
- `python-telegram-bot==13.6` (sync API) — called via `asyncio.to_thread()`. Requires `urllib3<2`. Upgrade to 20+ would require rewriting to async.
- **Slack** — uses `requests.post()` instead of `slack-webhook` (no timeout and broken response in slack-webhook).
- **Tests** — `pytest` with `httpx` AsyncClient and `pytest-asyncio` (41 tests, all PASSED). Config in `pytest.ini` (asyncio_mode=auto). Fixtures in `conftest.py` reset singleton and set test env vars.
- **`templates.json` is NOT in `.gitignore`** — tracked in repo (empty `{}` as default). Mounted as volume in Docker.
- Do not push `CLAUDE.md`, `GEMINI.md`, `AUDIT_REPORT.md` or `.env` to GitHub! Make sure they are in `.gitignore`.
