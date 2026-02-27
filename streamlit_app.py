"""TradingView Webhook Bot — Panel zarzadzania."""

import os
import streamlit as st
import requests
from auth import sprawdz_logowanie
from config import Ustawienia

st.set_page_config(page_title="TradingView Bot", layout="wide")
sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")

st.title("TradingView Webhook Bot")
st.subheader("Panel zarzadzania")

ust = Ustawienia()

# --- Status kanalow i kluczy ---
kol1, kol2 = st.columns(2)

with kol1:
    st.markdown("### Status kanalow")
    kanaly = {
        "Telegram": ust.wyslij_alerty_telegram,
        "Discord": ust.wyslij_alerty_discord,
        "Slack": ust.wyslij_alerty_slack,
    }
    for nazwa, aktywny in kanaly.items():
        ikona = ":green_circle:" if aktywny else ":red_circle:"
        st.markdown(f"{ikona} **{nazwa}**")

with kol2:
    st.markdown("### Status kluczy")
    klucze = {
        "Klucz bezpieczenstwa (SEC_KEY)": bool(ust.sec_key),
        "Token Telegram": bool(ust.tg_token),
        "Webhook Discord": bool(ust.discord_webhook),
        "Webhook Slack": bool(ust.slack_webhook),
    }
    for nazwa, skonfigurowany in klucze.items():
        ikona = ":white_check_mark:" if skonfigurowany else ":warning:"
        st.markdown(f"{ikona} {nazwa}")

# --- Healthcheck serwera webhook ---
st.markdown("---")
st.markdown("### Serwer webhook")

try:
    resp = requests.get(f"{WEBHOOK_URL}/health", timeout=3)
    if resp.status_code == 200:
        st.success("Serwer webhook dziala poprawnie")
        dane = resp.json()
        st.json(dane)
    else:
        st.error(f"Serwer webhook zwrocil status {resp.status_code}")
except requests.ConnectionError:
    st.warning("Nie mozna polaczyc sie z serwerem webhook")
except Exception as e:
    st.warning(f"Blad polaczenia: {e}")
