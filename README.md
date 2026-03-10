# 🗣 TradingView Alerts to Telegram, Discord or Slack

<img width="1601" height="450" alt="image" src="https://github.com/user-attachments/assets/e146193b-584a-484a-a9b1-d9aa48b62a3d" />


A self-hosted webhook server that receives [TradingView](https://tradingview.com) alerts and forwards them to **Telegram**, **Discord**, and **Slack**. Comes with a password-protected admin dashboard for managing configuration through the browser.

Built with FastAPI + Streamlit, deployed via Docker Compose.

---

## Features

- **Multi-channel alerts** — forward TradingView signals to Telegram (up to 2 groups), Discord, and Slack simultaneously
- **Alias system** — define short commands like `/spot {{ticker}} {{exchange}} {{close}}` instead of pasting complex JSON in TradingView
- **Admin dashboard** — configure channels, manage aliases, send test alerts, view logs — all from the browser
- **Dynamic channel override** — redirect any alert to a different Telegram/Discord/Slack channel directly from the TradingView alert payload
- **TradingView variables** — supports `{{close}}`, `{{exchange}}`, `{{ticker}}`, `{{volume}}` and all other TradingView placeholders
- **Security** — HMAC key validation, rate limiting, body size limits, SSRF protection, brute-force lockout, security headers
- **Docker-ready** — two containers (webhook + dashboard), runs behind Cloudflare Tunnel or any reverse proxy

---

## Architecture

```
TradingView Alert
       │
       ▼
  POST /webhook ──► Key validation ──► Alias/Template expansion ──► Send to channels
       │                                                                │
       │                                                    ┌───────────┼───────────┐
       │                                                    ▼           ▼           ▼
       │                                                Telegram    Discord     Slack
       │
  Admin Dashboard (Streamlit :8501)
       │
       └──► Configure .env ──► POST /reload-config ──► Hot-reload settings
```

| File | Role |
|---|---|
| `main.py` | FastAPI app — webhook endpoints, rate limiting, middleware |
| `handler.py` | Dispatches alerts to Telegram/Discord/Slack |
| `config.py` | Settings management — thread-safe singleton with hot-reload |
| `aliases.py` | Alias system — `/shortcut {var1} {var2}` expansion |
| `auth.py` | Dashboard authentication — HMAC-signed session tokens |
| `Dashboard.py` | Streamlit entry point — credential status overview |
| `pages/` | Dashboard pages: Configuration, Channels, Aliases, Test, Logs |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/popek1990/Tradingview.git
cd Tradingview
```

### 2. Create the `.env` file

```bash
cp .env.example .env
nano .env
```

Fill in your credentials:

```env
# ── Security ──────────────────────────────────────────────────────
# SEC_KEY — must match the "key" field in your TradingView alert JSON.
# Use any combination of letters and numbers, at least 16 characters.
SEC_KEY=your_secret_key_here

# DASHBOARD_PASSWORD — password to log into the admin panel (min 8 chars).
# If your password contains special characters (& $ ! # etc.), wrap it in single quotes.
DASHBOARD_PASSWORD='your_password_here'

# ── Telegram ──────────────────────────────────────────────────────
# 1. Open Telegram → search for @BotFather → send /newbot → follow prompts
# 2. Copy the token (e.g. 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw)
# 3. Add the bot to your group and send any message there
# 4. The bot will auto-detect your groups in the Dashboard → Channels page
SEND_ALERTS_TELEGRAM=True
TG_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
CHANNEL=-1001234567890
SEND_ALERTS_TELEGRAM_2=False
CHANNEL_2=

# ── Discord (optional) ───────────────────────────────────────────
# 1. Open Discord → right-click your channel → Edit Channel
# 2. Go to Integrations → Webhooks → New Webhook
# 3. Name it (e.g. "TradingView Alerts") and click "Copy Webhook URL"
# URL format: https://discord.com/api/webhooks/{id}/{token}
SEND_ALERTS_DISCORD=False
DISCORD_WEBHOOK=https://discord.com/api/webhooks/1234567890/abcdefg

# ── Slack (optional) ─────────────────────────────────────────────
# 1. Go to https://api.slack.com/apps → Create New App → From scratch
# 2. Enable Incoming Webhooks → Add New Webhook to Workspace
# 3. Pick a channel and copy the Webhook URL
# URL format: https://hooks.slack.com/services/T.../B.../XXX
SEND_ALERTS_SLACK=False
SLACK_WEBHOOK=
```

> **Note:** Telegram tokens (`TG_TOKEN`) don't need quotes — they only contain safe characters (`0-9`, `A-Z`, `a-z`, `:`, `-`, `_`).

### 3. Build and run

```bash
chmod +x docker.sh
./docker.sh
```

This script pulls the latest code, rebuilds both containers, and starts them.

> Or manually: `docker compose up -d --build`

After launch:
- **Webhook:** `http://localhost:80` (needs to be publicly accessible for TradingView)
- **Dashboard:** `http://localhost:8501` (LAN accessible, password-protected)

---

## Getting Credentials

### Telegram Bot Token (`TG_TOKEN`)

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts (choose a name and username)
3. BotFather will reply with a token like: `110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`
4. Paste this token as `TG_TOKEN` in your `.env`
5. **Add the bot to your Telegram group** and send any message there
6. Go to the **Channels** page in the admin dashboard — the bot will auto-detect your groups

### Discord Webhook (`DISCORD_WEBHOOK`)

1. Open **Discord** and go to your server
2. Right-click the channel you want alerts in → **Edit Channel**
3. Go to **Integrations** → **Webhooks** → **New Webhook**
4. Name it (e.g. "TradingView Alerts"), pick the channel
5. Click **Copy Webhook URL** and paste it as `DISCORD_WEBHOOK` in your `.env`

### Slack Webhook (`SLACK_WEBHOOK`)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Go to **Incoming Webhooks** → toggle **On**
3. Click **Add New Webhook to Workspace** → pick a channel → **Allow**
4. Copy the Webhook URL and paste it as `SLACK_WEBHOOK` in your `.env`

---

## Exposing the Webhook to the Internet

TradingView sends alerts from its cloud servers, so your webhook **must be reachable from the internet** on port **80** (HTTP) or **443** (HTTPS). TradingView does not support custom ports.

### Option A: Cloudflare Tunnel (recommended)

Free, secure, no need to open ports on your router.

```bash
cloudflared tunnel login
cloudflared tunnel create tradingview
cloudflared tunnel route dns tradingview webhook.yourdomain.com
cloudflared tunnel run --url http://localhost:80 tradingview
```

Then in TradingView, set webhook URL to: `https://webhook.yourdomain.com/webhook`

### Option B: Port forwarding

1. Forward **external port 80 → your server's local IP, port 80 (TCP)** on your router
2. Find your public IP: `curl ifconfig.me`
3. In TradingView, set webhook URL to: `http://<YOUR_PUBLIC_IP>/webhook`

> If your ISP assigns a dynamic IP, use a free DDNS service like [DuckDNS](https://www.duckdns.org).

### Option C: VPS

Rent a VPS ([Hetzner](https://www.hetzner.com/cloud), [DigitalOcean](https://www.digitalocean.com), [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)), install Docker, clone this repo, and run `docker compose up -d`.

---

## Setting Up TradingView Alerts

### Step 1: Create your key

Choose your own secret key — any combination of letters and numbers, **at least 16 characters** long. For example: `Abc123Xyz456Qwer` (do **not** use this example — create your own!).

This key must be entered in **two places**:
1. **On the server** — paste it into `SEC_KEY` in your `.env` file, or enter it in the Dashboard under **Configuration → Auth key for Webhooks**
2. **In TradingView** — include it as the `"key"` field in every alert message (see Step 2)

Both values must be **exactly the same**. If they don't match, the webhook will reject the alert.

### Step 2: Create an alert in TradingView

1. Open a chart on [TradingView](https://www.tradingview.com) and click **Alert** (clock icon or `Alt+A`)
2. Set your trigger conditions (price crossing a level, indicator signal, etc.)
3. Check **Webhook URL** and enter your server address:
   ```
   https://yourdomain.com/webhook
   ```
4. In the **Message** field, paste a JSON payload like this:

```json
{
  "key": "Abc123Xyz456Qwer",
  "msg": "/spot {{ticker}} {{exchange}} {{close}}"
}
```

> Replace `Abc123Xyz456Qwer` with **your own key** (the same one you set as `SEC_KEY`).

5. Click **Create**

When the alert triggers, TradingView will replace `{{ticker}}`, `{{exchange}}`, `{{close}}` with real values (e.g. `BTCUSDT`, `BINANCE`, `68000`) and send the JSON to your webhook.

### Message examples

#### Plain text message

```json
{
  "key": "Abc123Xyz456Qwer",
  "msg": "Signal #{{ticker}} at price {{close}}"
}
```

#### Using an alias

Aliases let you use short commands instead of writing long messages. Define them in the Dashboard under **Aliases**, then reference them in TradingView:

```json
{
  "key": "Abc123Xyz456Qwer",
  "msg": "/spot {{ticker}} {{exchange}} {{close}}"
}
```

TradingView sends something like `/spot BTCUSDT BINANCE 68000` — the webhook expands it using the alias template you defined.

![Alias in TradingView Message field](alias_example.png)
![Alias output in Telegram](alias_output_example.png)

#### Channel override

You can redirect any alert to a different Telegram group, Discord, or Slack channel by adding optional fields:

```json
{
  "key": "Abc123Xyz456Qwer",
  "msg": "VIP alert: {{ticker}} at {{close}}",
  "telegram": "-10018645640",
  "discord": "https://discord.com/api/webhooks/...",
  "slack": "T00000000/B00000000/XXXXXXXXXXXXX"
}
```

### Available TradingView variables

You can use any [TradingView placeholder](https://www.tradingview.com/support/solutions/43000531021/) in the `"msg"` field. The most common ones:

| Variable | Description | Example value |
|---|---|---|
| `{{ticker}}` | Symbol name | `BTCUSDT` |
| `{{exchange}}` | Exchange name | `BINANCE` |
| `{{close}}` | Current price | `68000` |
| `{{open}}` | Open price | `67500` |
| `{{high}}` | High price | `68500` |
| `{{low}}` | Low price | `67000` |
| `{{volume}}` | Volume | `1234.56` |
| `{{interval}}` | Timeframe (readable) | `1h` |
| `{{time}}` | Alert trigger time | `2024-01-15T12:30:00Z` |

### Legacy method: Key in URL (deprecated)

> **Deprecated:** This method exposes the key in the URL path, which may appear in access logs. Use the JSON method above instead.

Set webhook URL to `https://yourdomain.com/webhook/Abc123Xyz456Qwer` and the message to plain text:

```
/spot {{ticker}} {{exchange}} {{close}}
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/webhook` | POST | Receive alerts (key in JSON body) — **recommended** |
| `/webhook/{key}` | POST | Receive alerts (key in URL) — **deprecated** |
| `/health` | GET | Health check |
| `/reload-config` | POST | Hot-reload settings from `.env` (internal network only) |

---

## Docker Setup

The project runs two containers:

| Container | Port | Purpose |
|---|---|---|
| `webhook` | `127.0.0.1:80 → 1990` | FastAPI webhook server |
| `dashboard` | `0.0.0.0:8501 → 8501` | Streamlit admin panel |

Both containers:
- Run as non-root user (`appuser`)
- Have `no-new-privileges` security option
- Share `.env`, `aliases.json`, and a `logs` volume

### Volumes (bind mounts)

| File | Purpose |
|---|---|
| `.env` | Configuration (read-only for webhook, read-write for dashboard) |
| `aliases.json` | Alias definitions |
| `templates.json` | Message templates |
| `logs/` | Shared log directory (named volume) |

---

## Running Without Docker

```bash
pip install -r requirements.txt

# Terminal 1: Webhook server
uvicorn main:app --host 0.0.0.0 --port 80

# Terminal 2: Admin dashboard
streamlit run Dashboard.py
```

---

## Running Tests

```bash
pytest              # all tests
pytest -v           # verbose
pytest -k "test_telegram"  # by name
```

---

## Security

- **Key validation** — constant-time comparison using `hmac.compare_digest` on SHA-256 hashes
- **Rate limiting** — 30 requests/minute per IP via slowapi (uses `CF-Connecting-IP` behind Cloudflare)
- **Body size limit** — 10KB max (checks both `Content-Length` header and actual body)
- **SSRF protection** — Discord/Slack webhook URLs validated for scheme, hostname, and path prefix
- **Security headers** — HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Brute-force protection** — per-IP lockout on dashboard login
- **Internal endpoints** — `/reload-config` restricted to RFC 1918 private networks
- **Non-root containers** — webhook runs as `appuser` with `no-new-privileges`
- **Docs disabled** — `/docs` and `/redoc` are disabled in production

---

## Tech Stack

- **Python 3.12+**
- **FastAPI** + **Uvicorn** — async webhook server
- **Streamlit** — admin dashboard
- **python-telegram-bot 13.6** — Telegram integration (sync API, called via `asyncio.to_thread`)
- **discord-webhook** — Discord integration
- **pydantic-settings** — configuration management
- **slowapi** — rate limiting
- **Docker Compose** — containerized deployment

---

## License

MIT
