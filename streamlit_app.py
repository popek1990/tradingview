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
st.markdown("### Status systemu")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("SEC_KEY", "Skonfigurowany" if ust.sec_key else "Brak", delta="OK" if ust.sec_key else None, delta_color="normal")
with c2:
    st.metric("Telegram", "Włączony" if ust.wyslij_alerty_telegram else "Wyłączony", delta=ust.kanal if ust.wyslij_alerty_telegram else None)
with c3:
    st.metric("Discord", "Włączony" if ust.wyslij_alerty_discord else "Wyłączony")
with c4:
    st.metric("Slack", "Włączony" if ust.wyslij_alerty_slack else "Wyłączony")

st.caption("Panel zarzadzania v1.1 (Secured)")

st.markdown("---")

# --- Status kanalow i kluczy ---
kol1, kol2 = st.columns(2)

with kol1:
    st.markdown("### 📡 Status kanalow")
    kanaly = [
        ("📱 Telegram / Grupa 1", ust.wyslij_alerty_telegram),
        ("💬 Discord", ust.wyslij_alerty_discord),
        ("🔔 Slack", ust.wyslij_alerty_slack),
    ]
    if ust.kanal_2:
        kanaly.insert(1, ("📱 Telegram / Grupa 2", ust.wyslij_alerty_telegram_2))

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
