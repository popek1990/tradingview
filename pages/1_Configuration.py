"""Key Configuration — Minimalist Terminal Style."""

import streamlit as st
from auth import check_login
from config import Settings
from ui_utils import save_and_reload

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="viking_logo.jpg", layout="wide")

check_login()

# Settings loaded after login check
settings = Settings()

st.subheader("SECURITY CONFIGURATION")

# Secrets are never sent back to the browser: fields start empty and an empty
# field keeps the current value.
def _state(value: str) -> str:
    return "currently: SET ••••" if value else "currently: NOT SET"


with st.form("form_keys", border=True):
    st.caption("Leave a field empty to keep its current value.")
    st.markdown("#### ACCESS CONTROL")
    sec_key = st.text_input(
        "SEC_KEY (Auth key for Webhooks)",
        type="password", placeholder=_state(settings.sec_key),
        help="Min. 16 chars. Must match the key set in TradingView. "
             "Generate with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"",
    )
    dashboard_password = st.text_input(
        "DASHBOARD_PASSWORD (Panel Access)",
        type="password", placeholder=_state(settings.dashboard_password),
        help="Password for logging into this panel (min. 8 chars).",
    )

    st.markdown("---")
    st.markdown("#### GATEWAYS & TOKENS")
    tg_token = st.text_input(
        "TG_TOKEN (Telegram Bot Token)",
        type="password", placeholder=_state(settings.tg_token),
    )
    discord_webhook = st.text_input(
        "DISCORD_WEBHOOK (Webhook ID/Secret)",
        type="password", placeholder=_state(settings.discord_webhook),
    )
    slack_webhook = st.text_input(
        "SLACK_WEBHOOK (Webhook ID)",
        type="password", placeholder=_state(settings.slack_webhook),
    )

    submit = st.form_submit_button("SUBMIT CONFIGURATION", use_container_width=True)

if submit:
    # Strip whitespace from all credentials to prevent silent auth failures
    entered = {
        "SEC_KEY": sec_key.strip(),
        "TG_TOKEN": tg_token.strip(),
        "DISCORD_WEBHOOK": discord_webhook.strip(),
        "SLACK_WEBHOOK": slack_webhook.strip(),
        "DASHBOARD_PASSWORD": dashboard_password.strip(),
    }
    fields = {k: v for k, v in entered.items() if v}

    if not fields:
        st.info("NOTHING CHANGED")
        st.stop()
    if "DASHBOARD_PASSWORD" in fields and len(fields["DASHBOARD_PASSWORD"]) < 8:
        st.error("DASHBOARD_PASSWORD must be at least 8 characters!")
        st.stop()
    if "SEC_KEY" in fields and len(fields["SEC_KEY"]) < 16:
        st.error("SEC_KEY must be at least 16 characters!")
        st.stop()

    save_and_reload(fields)
