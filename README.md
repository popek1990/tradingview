# TradingView Webhook Bot

Serwer webhook odbierajacy alerty z [TradingView](https://tradingview.com) i przekazujacy je do kanalow: **Telegram**, **Discord**, **Slack**.

Posiada panel administracyjny (Streamlit) do zarzadzania konfiguracja przez przegladarke.

## Funkcje

- **Telegram** — wysylanie alertow przez bota (python-telegram-bot)
- **Discord** — wysylanie embeddow przez webhook
- **Slack** — wysylanie wiadomosci przez webhook
- **Panel administracyjny** — konfiguracja, toggle kanalow, testy, logi (Streamlit)
- **Dynamiczne kanaly** — mozliwosc przekierowania alertu do innego kanalu Telegram/Discord/Slack bezposrednio z alertu TradingView
- **Obsluga zmiennych TradingView** — `{{close}}`, `{{exchange}}`, `{{ticker}}` itp.
- **Autoryzacja** — klucz bezpieczenstwa w kazdym alercie, panel chroniony haslem
- **Rate limiting** — ochrona przed naduzyciem endpointow
- **Docker** — gotowe do wdrozenia na serwerze

## Wymagania

- Python 3.12+
- Docker i Docker Compose (zalecane)

## Szybki start

```bash
git clone https://github.com/popek1990/Tradingview.git
cd Tradingview

# Stworz plik .env z danymi dostepu
cat > .env << 'EOF'
SEC_KEY=twoj_klucz_bezpieczenstwa
DASHBOARD_HASLO=twoje_haslo_do_panelu
TG_TOKEN=token_bota_telegram
DISCORD_WEBHOOK=
SLACK_WEBHOOK=
EOF

docker compose build && docker compose up -d
```

Po uruchomieniu:
- **Webhook:** `http://<IP_SERWERA>:80/webhook` (port 80 wymagany przez TradingView)
- **Panel:** `http://localhost:8501` (tylko localhost)

## Przykladowy alert TradingView

W TradingView ustaw webhook URL na `http://<IP_SERWERA>/webhook` i wiadomosc:

```json
{
  "key": "twoj_klucz_bezpieczenstwa",
  "msg": "Sygnal *#{{ticker}}* po `{{close}}`",
  "telegram": "-100123456789",
  "discord": "https://discord.com/api/webhooks/...",
  "slack": "T00000000/B00000000/XXXXXXXXXXXXX"
}
```

- `key` — wymagany, musi zgadzac sie z `SEC_KEY` w `.env`
- `msg` — tresc alertu (Markdown obslugiwany)
- `telegram`, `discord`, `slack` — opcjonalne, nadpisuja domyslne kanaly z konfiguracji

## Endpointy

| Endpoint | Metoda | Opis |
|---|---|---|
| `/webhook` | POST | Odbiera alerty TradingView |
| `/health` | GET | Healthcheck + status kanalow |
| `/przeladuj-config` | POST | Przeladowanie konfiguracji z .env |

## Licencja

[MIT](LICENSE)
