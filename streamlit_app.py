"""TradingView Webhook Bot — Panel zarzadzania."""

import os
import streamlit as st
import requests
from auth import sprawdz_logowanie
from config import Ustawienia

st.set_page_config(page_title="TradingView Bot", page_icon="📈", layout="wide")
sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")

ust = Ustawienia()

# --- Naglowek ---
st.title("📈 TradingView Webhook Bot")

# Status bar pod tytulem
s_key = "🟢" if ust.sec_key else "🔴"
s_tg = "🟢" if ust.wyslij_alerty_telegram and ust.tg_token else "🔴"
s_tg2 = ""
if ust.kanal_2:
    s_tg2 = f' | <span title="Grupa 2: {ust.kanal_2}" style="cursor:help;">🟢 Telegram 2</span>'
s_dc = "🟢" if ust.wyslij_alerty_discord and ust.discord_webhook else "🔴"
s_sl = "🟢" if ust.wyslij_alerty_slack and ust.slack_webhook else "🔴"

st.markdown(f"""
<div style="font-size: 12px; opacity: 0.9; margin-top: -15px; margin-bottom: 10px;">
    <span title="Klucz bezpieczenstwa" style="cursor:help;">{s_key} SEC_KEY</span> |
    <span title="Kanal: {ust.kanal}" style="cursor:help;">{s_tg} Telegram</span>{s_tg2} |
    <span style="cursor:help;">{s_dc} Discord</span> |
    <span style="cursor:help;">{s_sl} Slack</span>
</div>
""", unsafe_allow_html=True)

st.caption("Panel zarzadzania v1.0")

st.markdown("---")

# --- Status kanalow i kluczy ---
kol1, kol2 = st.columns(2)

with kol1:
    st.markdown("### 📡 Status kanalow")
    kanaly = [
        ("📱 Telegram", ust.wyslij_alerty_telegram),
        ("💬 Discord", ust.wyslij_alerty_discord),
        ("🔔 Slack", ust.wyslij_alerty_slack),
    ]
    if ust.kanal_2:
        kanaly.insert(1, ("📱 Telegram 2", ust.wyslij_alerty_telegram))

    for nazwa, aktywny in kanaly:
        ikona = "🟢" if aktywny else "🔴"
        st.markdown(f"{ikona} **{nazwa}**")

with kol2:
    st.markdown("### 🔑 Status kluczy")
    klucze = [
        ("Klucz bezpieczenstwa (SEC_KEY)", bool(ust.sec_key)),
        ("Token Telegram", bool(ust.tg_token)),
        ("Kanal Telegram", bool(ust.kanal)),
    ]
    if ust.kanal_2:
        klucze.append(("Kanal Telegram 2", True))
    klucze.extend([
        ("Webhook Discord", bool(ust.discord_webhook)),
        ("Webhook Slack", bool(ust.slack_webhook)),
    ])

    for nazwa, skonfigurowany in klucze:
        ikona = "✅" if skonfigurowany else "⚠️"
        st.markdown(f"{ikona} {nazwa}")

# --- Healthcheck serwera webhook ---
st.markdown("---")
st.markdown("### 🖥️ Serwer webhook")

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
