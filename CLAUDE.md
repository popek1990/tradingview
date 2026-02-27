# CLAUDE.md

Ten plik zawiera wytyczne dla asystentów AI pracujących z tym repozytorium.

## Główne Zasady

1. **Język Polski**: Wszystkie odpowiedzi, wyjaśnienia, plany i wiadomości w commitach (commit messages) muszą być w języku **polskim**.
2. **Docker**: **NIE** wykonuj automatycznie komend `docker build`, `docker compose build` ani `docker compose up`. Aplikacja działa w Dockerze na innej maszynie i użytkownik sam zajmuje się przebudową i restartem kontenerów po wprowadzeniu zmian.

## Opis projektu

TradingView-Webhook-Bot — serwer webhook (FastAPI) odbierajacy alerty z TradingView i przekazujacy je do kanalow: Telegram, Discord, Slack. Posiada panel administracyjny Streamlit do zarzadzania konfiguracja przez przegladarke.

**Wymagania:** Python 3.12+

## Uruchamianie

```bash
# Docker (zalecane) — produkcja
docker compose build
docker compose up -d
# -> webhook: http://HOST:80/webhook (port 80 wymagany przez TradingView)
# -> panel:   http://localhost:8501 (tylko localhost)

# Lokalnie — webhook
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 80

# Lokalnie — panel Streamlit (osobny terminal)
streamlit run streamlit_app.py

# Testy (wymaga venv z zainstalowanymi requirements.txt)
pytest                       # wszystkie testy
pytest tests/test_handler.py # pojedynczy plik
pytest -k "test_telegram"   # testy po nazwie
```

### Wdrozenie na nowym serwerze

```bash
git clone https://github.com/popek1990/Tradingview.git
cd Tradingview
# Stworz .env z credentials (nie jest w repo)
cat > .env << 'EOF'
SEC_KEY=twoj_klucz
DASHBOARD_HASLO=twoje_haslo
TG_TOKEN=twoj_token_telegram
DISCORD_WEBHOOK=
SLACK_WEBHOOK=
EOF
docker compose build && docker compose up -d
```

## Repozytorium

- **GitHub:** https://github.com/popek1990/Tradingview (prywatne)
- **Branch:** main
- `.env` i `plan.md` sa w `.gitignore` — NIE trafiaja do repo

## Zaleznosci (requirements.txt)

| Pakiet | Wersja | Rola |
|---|---|---|
| `fastapi` | >=0.104.0 | Framework HTTP (webhook, health, reload) |
| `uvicorn[standard]` | >=0.24.0 | Serwer ASGI |
| `pydantic-settings` | >=2.1.0 | Klasa `Ustawienia(BaseSettings)` — config z .env |
| `python-dotenv` | >=1.0.0 | `set_key()` do zapisu .env z panelu Streamlit |
| `python-telegram-bot` | ==13.6 | Sync API Telegram (v13, NIE v20+) |
| `urllib3` | <2 | Wymagane przez python-telegram-bot 13.6 (v2 usunal potrzebne moduly) |
| `discord-webhook` | >=1.0.0 | Wysylanie embeddow na Discord |
| `requests` | >=2.28.0 | HTTP client (Slack webhook, healthcheck) |
| `slowapi` | >=0.1.9 | Rate limiting endpointow |
| `streamlit` | >=1.30.0 | Panel administracyjny |
| `pytest` | >=7.0.0 | Framework testowy |
| `pytest-asyncio` | >=0.21.0 | Testy async (FastAPI endpoints) |
| `httpx` | >=0.24.0 | AsyncClient do testow FastAPI |

## Struktura plikow

```
Tradingview/
  main.py                  # FastAPI — endpointy webhook, health, reload + logging do pliku
  handler.py               # Dispatcher alertow do kanalow (Telegram, Discord, Slack)
  config.py                # Pydantic BaseSettings — konfiguracja (jedno zrodlo prawdy)
  szablony.py              # CRUD i renderowanie szablonow wiadomosci
  szablony.json            # Plik szablonow (montowany jako Docker volume)
  auth.py                  # Autoryzacja haslem + timeout sesji + wylogowanie
  streamlit_app.py         # Dashboard Streamlit (strona glowna)
  pages/
    1_Konfiguracja.py      # Edycja kluczy/tokenow w .env
    2_Kanaly.py            # Toggle kanalow + ustawienia kanalu
    3_Test.py              # Reczne wysylanie alertow testowych
    4_Logi.py              # Podglad logow serwera webhook
    5_Szablony.py          # Zarzadzanie szablonami wiadomosci
  tests/
    __init__.py            # Marker pakietu testow
    conftest.py            # Fixtures testowe (env, singleton reset)
    test_config.py         # Testy konfiguracji i parsowania
    test_webhook.py        # Testy endpointow FastAPI
    test_handler.py        # Testy handlera z mockowanymi kanalami
  .env                     # Wrazliwe dane (tokeny, hasla) — w .gitignore, NIE w repo
  .gitignore               # Ignorowane pliki (venv, __pycache__, .env, plan.md, backups)
  .dockerignore            # Wykluczone z obrazu Docker (git, venv, backups, *.md)
  Dockerfile               # Obraz webhook (python:3.12-slim, port 1990)
  Dockerfile.streamlit     # Obraz panelu Streamlit (port 8501)
  docker-compose.yml       # Dwa serwisy: webhook + dashboard + volume logow + szablony
  pytest.ini               # Konfiguracja pytest (asyncio_mode=auto)
  requirements.txt         # Zaleznosci (produkcyjne + testowe)
  README.md                # README projektu (po polsku)
  CLAUDE.md                # Instrukcje dla Claude Code
  logs/                    # Logi serwera (tworzony automatycznie, wspoldzielony volume Docker)
```

## Architektura i logika

Kod spolszczony — nazwy funkcji, zmiennych i komunikaty po polsku.

### Endpointy FastAPI (main.py)

| Endpoint | Metoda | Opis | Rate limit |
|---|---|---|---|
| `/webhook` | POST | Odbiera alerty TradingView (klucz w JSON body) | 30/min |
| `/webhook/{klucz}` | POST | Odbiera alerty — klucz w URL, body JSON lub plain text | 30/min |
| `/health` | GET | Healthcheck + status kanalow | brak |
| `/przeladuj-config` | POST | Reload configa z .env | 5/min |

Przy starcie serwera (`lifespan` context manager) walidacja krytycznych ustawien — jesli `SEC_KEY` jest pusty, serwer odmawia startu (`SystemExit(1)`).

Logi zapisywane do `logs/webhook.log` (RotatingFileHandler, max 5MB, 3 backupy) + stdout.

### Formaty webhooka (3 sposoby uzycia)

**1. Stary format — JSON z kluczem w body (wsteczna kompatybilnosc):**
```
POST /webhook
Body: {"key": "KLUCZ", "msg": "tresc alertu", "telegram?": "...", "discord?": "...", "slack?": "..."}
```

**2. Nowy format — klucz w URL + plain text (najprostszy):**
```
POST /webhook/KLUCZ
Content-Type: text/plain
Body: tresc alertu (z Markdown, newliny jako entery)
```

**3. Nowy format — klucz w URL + szablon:**
```
POST /webhook/KLUCZ
Body: {"szablon": "target", "ticker": "SPX", "exchange": "TVC", "close": "6910"}
```

### Przeplyw alertu

```
TradingView
  -> POST /webhook lub /webhook/{klucz}
  -> wykrycie Content-Type: application/json vs text/plain
  -> jesli JSON: walidacja Pydantic (AlertPayload)
  -> jesli plain text: cale body = wiadomosc (max 4000 zn.)
  -> klucz: z URL (priorytet) lub z JSON body
  -> porownanie klucza: hmac.compare_digest(klucz, sec_key)
  -> jesli szablon: renderuj(nazwa, zmienne) z szablony.json
  -> wyniki = await asyncio.to_thread(wyslij_alert, dane_alertu)
     -> kazdy wlaczony kanal (Telegram/Discord/Slack)
        -> data.get("kanal") or domyslna_wartosc_z_configu
        -> zwraca {kanal: True/False}
  -> HTTP 200 {"status": "ok", "kanaly": {kanal: sukces}}
  -> HTTP 502 jesli WSZYSTKIE kanaly zawiodly
  -> lub HTTP 400/403/429 przy bledach
```

### Szablony wiadomosci (szablony.py)

- `szablony.json` — plik JSON z definicjami szablonow (montowany jako Docker volume)
- `wczytaj_szablony()` / `zapisz_szablony()` — CRUD operacje (thread-safe z `threading.Lock()`)
- `renderuj(nazwa, zmienne)` — podstawia zmienne w szablonie (`str.format()`)
- Zarzadzanie z dashboardu Streamlit (`pages/5_Szablony.py`)

### Konfiguracja (config.py)

Klasa `Ustawienia(BaseSettings)` z pydantic-settings — **jedno zrodlo prawdy** dla calego projektu:
- Pydantic laduje zmienne z `.env` (przez `SettingsConfigDict(env_file=".env")`). W Docker plik `.env` jest montowany jako volume (docker-compose NIE uzywa dyrektywy `env_file:` — Pydantic sam go czyta).
- Niewrazliwe dane (flagi kanalow, ID kanalu) maja domyslne wartosci w klasie
- Singleton thread-safe: `pobierz_ustawienia()` — `threading.Lock()` z double-checked locking (uzywany przez serwer webhook)
- Swiezy odczyt: `Ustawienia()` — bezposrednia instancja (uzywany przez panel Streamlit, czyta aktualny .env)
- Reload: `przeladuj_ustawienia()` — tworzy nowa instancje z aktualnego `.env` (pod lockiem)

### Handler (handler.py)

- `wyslij_alert(data: dict) -> dict[str, bool]` — synchroniczna funkcja, wywolywana w watku przez `asyncio.to_thread()`. Zwraca wyniki wysylki dla kazdego kanalu.
- `TIMEOUT_SIEC = 10` — timeout na wszystkie operacje sieciowe (Telegram, Discord, Slack)
- Bot Telegram cache'owany: `_pobierz_tg_bot(token)` — thread-safe z `threading.Lock()`, inwalidacja przy zmianie tokena
- Discord URL — obsluguje pelne URL i same ID (auto-prefix). Embed: title (max 256 zn.) + description (do 4096 zn.) dla dlugich wiadomosci.
- Slack — bezposredni `requests.post()` z timeout. Weryfikacja odpowiedzi tekstowej (`"ok"` = sukces).
- Logowanie przez `logging` (nie print)

### Panel Streamlit

- **Konfiguracja:** Wszystkie strony uzywaja `Ustawienia()` z config.py (nie `dotenv_values`). Jedno zrodlo prawdy dla domyslnych wartosci. Zapis do `.env` przez `set_key()` z python-dotenv.
- `auth.py` — `sprawdz_logowanie()` porownuje haslo z `DASHBOARD_HASLO` (`hmac.compare_digest`), ochrona bruteforce (max 5 prob, blokada 5 minut, reset po wygasnieciu), przycisk "Wyloguj" w sidebarze, auto-wylogowanie po 30 min nieaktywnosci.
- `streamlit_app.py` — Dashboard: statusy kanalow (wl/wyl), statusy kluczy (skonfigurowane/brak), healthcheck serwera
- `pages/1_Konfiguracja.py` — Edycja tokenow/kluczy, zapis do `.env` przez `set_key()` z weryfikacja sukcesu, auto-reload serwera
- `pages/2_Kanaly.py` — Toggle kanalow + ustawienia (kanal TG)
- `pages/3_Test.py` — Reczne wysylanie alertu testowego przez pelny pipeline `/webhook`
- `pages/4_Logi.py` — Podglad logow serwera: filtrowanie po poziomie (ERROR/WARNING/INFO), wyszukiwanie, konfigurowalny zakres
- `pages/5_Szablony.py` — Zarzadzanie szablonami wiadomosci: lista, dodawanie, edycja, usuwanie, podglad, generowanie JSON do TradingView
- Komunikacja ze serwerem: `WEBHOOK_URL` (env var, domyslnie `http://webhook:1990` w Dockerze, `http://localhost:80` lokalnie)

### Docker

- **Dockerfile** — `python:3.12-slim`, non-root user (`appuser`), katalog `logs` z uprawnieniami appuser, EXPOSE 1990, HEALTHCHECK na `/health`, graceful shutdown (`--timeout-graceful-shutdown 10`), `.env` NIE kopiowany (montowany jako volume)
- **Dockerfile.streamlit** — osobny obraz, non-root user (`appuser`), port 8501, HEALTHCHECK na `/_stcore/health`
- **docker-compose.yml** — serwis `webhook` (127.0.0.1:80->1990, 256M RAM, 0.5 CPU) + serwis `dashboard` (127.0.0.1:8501, 512M RAM, 0.5 CPU), wspoldzielony `.env`, `szablony.json` i `logi` (named volume) przez volume mount. Port 80 tylko localhost — ruch z internetu przez Cloudflare Tunnel. Limity zasobow przez `deploy.resources.limits`.

### Zmienne w .env

Wrazliwe: `SEC_KEY`, `DASHBOARD_HASLO`, `TG_TOKEN`, `DISCORD_WEBHOOK`, `SLACK_WEBHOOK`

Opcjonalne nadpisania: `WYSLIJ_ALERTY_TELEGRAM`, `WYSLIJ_ALERTY_TELEGRAM_2`, `WYSLIJ_ALERTY_DISCORD`, `WYSLIJ_ALERTY_SLACK`, `KANAL`

## Wazne uwagi

- **`.env` NIGDY nie trafia do repo ani do obrazu Docker** — jest w `.gitignore`. Nie commitowac, nie pushowac. Zawiera tokeny, hasla i klucze API. W Docker montowany jako volume.
- **Dashboard tylko localhost** — port Streamlit w docker-compose MUSI byc `127.0.0.1:8501:8501`. NIE otwierac na `0.0.0.0` — panel nie powinien byc publicznie dostepny z internetu.
- **Port 80** mapowany na `127.0.0.1:80` — dostep z internetu przez Cloudflare Tunnel (cloudflared na hoscie Proxmox). Nie otwierac na `0.0.0.0`.
- `python-telegram-bot==13.6` (sync API) — wywolywane przez `asyncio.to_thread()`. Wymaga `urllib3<2`. Upgrade do 20+ wymagalby przepisania na async.
- **Slack** — uzywamy `requests.post()` zamiast `slack-webhook` (brak timeout i bledna odpowiedz w slack-webhook).
- **Testy** — `pytest` z `httpx` AsyncClient i `pytest-asyncio` (38 testow, wszystkie PASSED). Konfiguracja w `pytest.ini` (asyncio_mode=auto). Fixtures w `conftest.py` resetuja singleton i ustawiaja testowe env vars.
- **`szablony.json` nie trafia do `.gitignore`** — jest w repo (pusty `{}` jako domyslny). W Docker montowany jako volume.
