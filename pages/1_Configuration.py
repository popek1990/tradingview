"""Key Configuration — Minimalist Terminal Style."""

import streamlit as st
from auth import check_login
from config import Settings
from ui_utils import save_and_reload

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="🔑", layout="wide")

check_login()

# Settings loaded after login check
settings = Settings()

st.subheader("SECURITY CONFIGURATION")

with st.form("form_keys", border=True):
    st.markdown("#### ACCESS CONTROL")
    sec_key = st.text_input(
        "SEC_KEY (Auth key for Webhooks)",
        value=settings.sec_key,
        type="password",
        help="Min. 16 chars. Must match the key set in TradingView.",
    )
    dashboard_password = st.text_input(
        "DASHBOARD_PASSWORD (Panel Access)",
        value=settings.dashboard_password,
        type="password",
        help="Password for logging into this panel.",
    )

    st.markdown("---")
    st.markdown("#### GATEWAYS & TOKENS")
    tg_token = st.text_input(
        "TG_TOKEN (Telegram Bot Token)",
        value=settings.tg_token,
        type="password",
    )
    discord_webhook = st.text_input(
        "DISCORD_WEBHOOK (Webhook ID/Secret)",
        value=settings.discord_webhook,
        type="password",
    )
    slack_webhook = st.text_input(
        "SLACK_WEBHOOK (Webhook ID)",
        value=settings.slack_webhook,
        type="password",
    )

    submit = st.form_submit_button("SUBMIT CONFIGURATION", use_container_width=True)

if submit:
    if not dashboard_password.strip():
        st.error("DASHBOARD_PASSWORD cannot be empty!")
        st.stop()

    fields = {
        "SEC_KEY": sec_key,
        "TG_TOKEN": tg_token,
        "DISCORD_WEBHOOK": discord_webhook,
        "SLACK_WEBHOOK": slack_webhook,
        "DASHBOARD_PASSWORD": dashboard_password,
    }
    save_and_reload(fields)
