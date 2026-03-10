# 🗣 TradingView Alerts to Telegram, Discord or Slack

<img width="1601" height="450" alt="image" src="https://github.com/user-attachments/assets/e146193b-584a-484a-a9b1-d9aa48b62a3d" />

A self-hosted webhook server that receives [TradingView](https://tradingview.com) alerts and forwards them to **Telegram**, **Discord**, and **Slack**. Comes with a password-protected admin dashboard for managing configuration through the browser.

Built with FastAPI + Streamlit, deployed via Docker Compose.

---

## Features

- **Multi-channel alerts** — Telegram (up to 2 groups), Discord, and Slack simultaneously
- **Alias system** — short commands like `/spot {{ticker}} {{exchange}} {{close}}` instead of complex JSON
- **Admin dashboard** — configure channels, manage aliases, send test alerts, view logs
- **Dynamic channel override** — redirect any alert to a different channel directly from the payload
- **Security** — HMAC key validation, rate limiting, SSRF protection, brute-force lockout

---

## Quick Start

```bash
git clone https://github.com/popek1990/Tradingview.git
cd Tradingview
cp .env.example .env
nano .env          # fill in your credentials (see comments inside)
./docker.sh        # or: docker compose up -d --build
```

After launch:
- **Webhook:** `http://localhost:80` (must be publicly accessible for TradingView)
- **Dashboard:** `http://localhost:8501` (password-protected)

> Your webhook must be reachable from the internet on port 80 or 443. Use [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), port forwarding, or a VPS.

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

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/webhook` | POST | Receive alerts (key in JSON body) |
| `/webhook/{key}` | POST | Receive alerts (key in URL) — **deprecated** |
| `/health` | GET | Health check |
| `/reload-config` | POST | Hot-reload settings from `.env` (internal network only) |

---

## Running Without Docker

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 80          # webhook server
streamlit run Dashboard.py                           # admin dashboard (separate terminal)
```

---

## Running Tests

```bash
pytest -v
```

---

## License

MIT
