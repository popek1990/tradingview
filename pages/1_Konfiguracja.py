"""Konfiguracja Kluczy — Minimalist Terminal Style."""

import os
import streamlit as st
import requests
from dotenv import set_key
from auth import sprawdz_logowanie
from config import Ustawienia

# Must be first Streamlit command
st.set_page_config(page_title="TV-BOT | CONFIG", page_icon="🔑", layout="wide")

sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
SCIEZKA_ENV = ".env"
ust = Ustawienia()

st.subheader("🔑 SECURITY CONFIGURATION")

with st.form("form_keys", border=True):
    st.markdown("#### ACCESS CONTROL")
    sec_key = st.text_input(
        "SEC_KEY (Auth key for Webhooks)",
        value=ust.sec_key,
        type="password",
        help="Musi zgadzać się z kluczem wysyłanym przez TradingView."
    )
    dashboard_haslo = st.text_input(
        "DASHBOARD_HASLO (Panel Access)",
        value=ust.dashboard_haslo,
        type="password",
        help="Hasło do logowania do tego panelu."
    )

    st.markdown("---")
    st.markdown("#### GATEWAYS & TOKENS")
    tg_token = st.text_input(
        "TG_TOKEN (Telegram Bot Token)",
        value=ust.tg_token,
        type="password",
    )
    discord_webhook = st.text_input(
        "DISCORD_WEBHOOK (Webhook ID/Secret)",
        value=ust.discord_webhook,
        type="password",
    )
    slack_webhook = st.text_input(
        "SLACK_WEBHOOK (Webhook ID)",
        value=ust.slack_webhook,
        type="password",
    )

    zapisz = st.form_submit_button("SUBMIT CONFIGURATION", use_container_width=True)

if zapisz:
    if not dashboard_haslo.strip():
        st.error("DASHBOARD_HASLO cannot be empty!")
        st.stop()

    stary_sec_key = ust.sec_key
    pola = {
        "SEC_KEY": sec_key,
        "TG_TOKEN": tg_token,
        "DISCORD_WEBHOOK": discord_webhook,
        "SLACK_WEBHOOK": slack_webhook,
        "DASHBOARD_HASLO": dashboard_haslo,
    }

    bledy_zapisu = []
    for klucz, wartosc in pola.items():
        sukces, _, _ = set_key(SCIEZKA_ENV, klucz, wartosc)
        if not sukces:
            bledy_zapisu.append(klucz)

    if bledy_zapisu:
        st.error(f"FAILED TO WRITE: {', '.join(bledy_zapisu)}")
        st.stop()

    st.success("CONFIGURATION PERSISTED TO .ENV")
    st.toast("✅ Persisted!")

    try:
        resp = requests.post(
            f"{WEBHOOK_URL}/przeladuj-config",
            json={"key": stary_sec_key},
            timeout=5,
        )
        if resp.status_code == 200:
            st.success("WEBHOOK SERVER: CONFIG RELOADED")
        else:
            st.warning(f"WEBHOOK SERVER: RELOAD FAILED (HTTP {resp.status_code})")
    except Exception:
        st.info("WEBHOOK SERVER: UNREACHABLE (Manual restart required)")
