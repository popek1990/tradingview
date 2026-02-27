"""TradingView Webhook Bot — Minimalist Dashboard."""

import os
import streamlit as st
import requests
from auth import sprawdz_logowanie
from config import Ustawienia

# Musi byc przed jakimkolwiek wywolaniem st. (oprocz auth jesli auth ma st.set_page_config)
# Ale sprawdz_logowanie wywoluje render_ui_header, wiec set_page_config musi byc tutaj.
st.set_page_config(page_title="TV-BOT TERMINAL", page_icon="📟", layout="wide")
sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
ust = Ustawienia()

# --- Sekcja 1: Głowne Metryki ---
st.subheader("📊 SYSTEM STATUS")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(label="SECURITY KEY", 
              value="ACTIVE" if ust.sec_key else "MISSING", 
              delta="OK" if ust.sec_key else "ERROR",
              delta_color="normal")
with c2:
    status_tg = "ON" if ust.wyslij_alerty_telegram else "OFF"
    st.metric(label="TELEGRAM NODE", value=status_tg, delta=ust.kanal if ust.wyslij_alerty_telegram else None)
with c3:
    status_dc = "ON" if ust.wyslij_alerty_discord else "OFF"
    st.metric(label="DISCORD NODE", value=status_dc)
with c4:
    status_sl = "ON" if ust.wyslij_alerty_slack else "OFF"
    st.metric(label="SLACK NODE", value=status_sl)

st.markdown("---")

# --- Sekcja 2: Szczegóły Konfiguracji ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📡 ACTIVE CHANNELS")
    
    with st.container(border=True):
        kanaly = [
            ("Telegram / Grupa 1", ust.wyslij_alerty_telegram),
            ("Discord Gateway", ust.wyslij_alerty_discord),
            ("Slack Webhook", ust.wyslij_alerty_slack),
        ]
        if ust.kanal_2:
            kanaly.insert(1, ("Telegram / Grupa 2", ust.wyslij_alerty_telegram_2))

        for nazwa, aktywny in kanaly:
            color = "#00FF41" if aktywny else "#F85149"
            status_text = "[ ACTIVE ]" if aktywny else "[ DISABLED ]"
            st.markdown(f"<code style='color: {color}; background: none;'>{status_text}</code> **{nazwa}**", unsafe_allow_html=True)

with col_right:
    st.markdown("### 🔑 CREDENTIALS")
    
    with st.container(border=True):
        klucze = [
            ("SEC_KEY (Auth)", bool(ust.sec_key)),
            ("TG_TOKEN (Bot)", bool(ust.tg_token)),
            ("TG_CHID (Primary)", bool(ust.kanal)),
        ]
        if ust.kanal_2:
            klucze.append(("TG_CHID (Secondary)", True))
        klucze.extend([
            ("DC_URL (Webhook)", bool(ust.discord_webhook)),
            ("SL_URL (Webhook)", bool(ust.slack_webhook)),
        ])

        for nazwa, ok in klucze:
            status_icon = "✔" if ok else "✖"
            color = "#00FF41" if ok else "#F85149"
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{status_icon}</span> {nazwa}", unsafe_allow_html=True)

# --- Sekcja 3: Healthcheck ---
st.markdown("---")
st.markdown("### 🖥️ WEBHOOK SERVER HEALTH")

try:
    resp = requests.get(f"{WEBHOOK_URL}/health", timeout=3)
    if resp.status_code == 200:
        dane = resp.json()
        st.success("WEBHOOK SERVER: ONLINE")
        with st.expander("Show raw telemetry data"):
            st.json(dane)
    else:
        st.error(f"WEBHOOK SERVER: ERROR (HTTP {resp.status_code})")
except Exception:
    st.warning("WEBHOOK SERVER: UNREACHABLE / OFFLINE")
