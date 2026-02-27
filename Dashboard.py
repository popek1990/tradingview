"""TradingView Webhook Bot — Minimalist Dashboard."""

import os
import streamlit as st
from auth import sprawdz_logowanie
from config import Ustawienia

# Dashboard configuration
st.set_page_config(page_title="TV-BOT TERMINAL", page_icon="📟", layout="wide")
sprawdz_logowanie()

ust = Ustawienia()

# --- Section 1: CREDENTIALS MATRIX ---
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

st.markdown("---")
st.caption("Dashboard v2.0 | SYSTEM SECURED")
