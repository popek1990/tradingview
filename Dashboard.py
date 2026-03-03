"""TradingView Webhook Bot — Minimalist Dashboard."""

import streamlit as st
from auth import check_login
from config import Settings

# Dashboard configuration
st.set_page_config(page_title="TradingView Alerts", page_icon="viking_logo.jpg", layout="wide")
check_login()

# Settings loaded after login check
settings = Settings()

# --- Section 1: CREDENTIALS MATRIX ---
st.markdown("### 🔑 CREDENTIALS VERIFICATION")
with st.container(border=True):
    col_l, col_r = st.columns(2)

    with col_l:
        keys_left = [
            ("SEC_KEY (Auth Token)", bool(settings.sec_key)),
            ("TG_TOKEN (Bot API)", bool(settings.tg_token)),
            ("TG_CHID (Group 1)", bool(settings.channel)),
        ]
        for label, ok in keys_left:
            status_icon = "✔" if ok else "✖"
            color = "#00FF41" if ok else "#F85149"
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{status_icon}</span> {label}", unsafe_allow_html=True)

    with col_r:
        keys_right = [
            ("DC_URL (Webhook Endpoint)", bool(settings.discord_webhook)),
            ("SL_URL (Webhook Endpoint)", bool(settings.slack_webhook)),
        ]
        if settings.channel_2:
            keys_right.insert(0, ("TG_CHID (Group 2)", True))

        for label, ok in keys_right:
            status_icon = "✔" if ok else "✖"
            color = "#00FF41" if ok else "#F85149"
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{status_icon}</span> {label}", unsafe_allow_html=True)

st.markdown("---")
st.caption("Dashboard v2.0 | SYSTEM SECURED")
