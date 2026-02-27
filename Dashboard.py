"""TradingView Webhook Bot — Minimalist Dashboard."""

import os
import streamlit as st
import requests
from auth import sprawdz_logowanie
from config import Ustawienia

# Dashboard configuration
st.set_page_config(page_title="TV-BOT TERMINAL", page_icon="📟", layout="wide")
sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
ust = Ustawienia()

# --- Section 1: SYSTEM OVERVIEW ---
st.subheader("📊 SYSTEM PERFORMANCE")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(label="AUTH KEY", 
              value="ACTIVE" if ust.sec_key else "MISSING", 
              delta="OK" if ust.sec_key else "ERROR",
              delta_color="normal")
with c2:
    status_tg = "ON" if ust.wyslij_alerty_telegram else "OFF"
    st.metric(label="TG G1", value=status_tg, delta=ust.kanal if ust.wyslij_alerty_telegram else None)
with c3:
    status_dc = "ON" if ust.wyslij_alerty_discord else "OFF"
    st.metric(label="DC GATE", value=status_dc)
with c4:
    status_sl = "ON" if ust.wyslij_alerty_slack else "OFF"
    st.metric(label="SL WEB", value=status_sl)

st.markdown("---")

# --- Section 2: CREDENTIALS MATRIX ---
st.markdown("### 🔑 CREDENTIALS VERIFICATION")
with st.container(border=True):
    col_l, col_r = st.columns(2)
    
    with col_l:
        klucze_l = [
            ("SEC_KEY (Auth Token)", bool(ust.sec_key)),
            ("TG_TOKEN (Bot API)", bool(ust.tg_token)),
            ("TG_CHID (Group 1)", bool(ust.kanal)),
        ]
        for nazwa, ok in klucze_l:
            status_icon = "✔" if ok else "✖"
            color = "#00FF41" if ok else "#F85149"
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{status_icon}</span> {nazwa}", unsafe_allow_html=True)

    with col_r:
        klucze_r = [
            ("DC_URL (Webhook Endpoint)", bool(ust.discord_webhook)),
            ("SL_URL (Webhook Endpoint)", bool(ust.slack_webhook)),
        ]
        if ust.kanal_2:
            klucze_r.insert(0, ("TG_CHID (Group 2)", True))
            
        for nazwa, ok in klucze_r:
            status_icon = "✔" if ok else "✖"
            color = "#00FF41" if ok else "#F85149"
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{status_icon}</span> {nazwa}", unsafe_allow_html=True)

# --- Section 3: SERVER TELEMETRY ---
st.markdown("---")
st.markdown("### 🖥️ WEBHOOK SERVER TELEMETRY")

try:
    resp = requests.get(f"{WEBHOOK_URL}/health", timeout=3)
    if resp.status_code == 200:
        dane = resp.json()
        st.success("WEBHOOK CORE: ONLINE")
        with st.expander("Show detailed telemetry"):
            st.json(dane)
    else:
        st.error(f"WEBHOOK CORE: ERROR (HTTP {resp.status_code})")
except Exception:
    st.warning("WEBHOOK CORE: UNREACHABLE / OFFLINE")
