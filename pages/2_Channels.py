"""Channels Configuration — Minimalist Terminal Style."""

import re

import streamlit as st
from auth import check_login
from config import Settings
from ui_utils import save_and_reload

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="viking_logo.jpg", layout="wide")

check_login()

# Settings loaded after login check
settings = Settings()

st.subheader("NOTIFICATION CHANNELS")

# --- How to get Telegram Chat ID ---
with st.expander("HOW TO GET TELEGRAM CHAT ID", expanded=False):
    st.markdown("**1.** Open Telegram and search for **@ShowJsonBot**")
    st.markdown("**2.** Add **@ShowJsonBot** to your group/channel")
    st.markdown("**3.** The bot will instantly reply with JSON — find `\"chat\"` → `\"id\"`:")
    st.code('{\n  "my_chat_member": {\n    "chat": {\n      "id": -5112822251,   ← THIS IS YOUR CHAT ID\n      "title": "your-group-name",\n      "type": "group"\n    }\n  }\n}', language="json")
    st.markdown("**4.** Copy the `id` value (e.g. `-5112822251`) and paste it below")

with st.form("form_channels", border=True):
    col_tg1, col_tg2 = st.columns(2)
    with col_tg1:
        st.markdown("#### TELEGRAM GROUP 1")
        tg_enabled = st.toggle("ENABLE", value=settings.send_alerts_telegram, key="tg1_toggle")
        channel = st.text_input("Chat ID", value=settings.channel, key="grp1_input",
                                help="Paste the chat ID from @ShowJsonBot")
    with col_tg2:
        st.markdown("#### TELEGRAM GROUP 2")
        tg_enabled_2 = st.toggle("ENABLE", value=settings.send_alerts_telegram_2, key="tg2_toggle")
        channel_2 = st.text_input("Chat ID", value=settings.channel_2, key="grp2_input",
                                  help="Paste the chat ID from @ShowJsonBot")

    st.markdown("---")
    # Toggle on/off only — secrets (webhook URL) editable only in Configuration
    col_dc, col_sl = st.columns(2)
    with col_dc:
        st.markdown("#### DISCORD")
        st.caption("⚠️ Experimental — not yet tested")
        dc_has_webhook = bool(settings.discord_webhook)
        dc_enabled = st.toggle("ENABLE", value=settings.send_alerts_discord and dc_has_webhook,
                               disabled=not dc_has_webhook, key="dc_toggle")
        if dc_has_webhook:
            st.caption("Webhook: configured (edit in Configuration)")
        else:
            st.warning("Webhook: NOT SET (configure in Configuration page)")
    with col_sl:
        st.markdown("#### SLACK")
        st.caption("⚠️ Experimental — not yet tested")
        sl_has_webhook = bool(settings.slack_webhook)
        sl_enabled = st.toggle("ENABLE", value=settings.send_alerts_slack and sl_has_webhook,
                               disabled=not sl_has_webhook, key="sl_toggle")
        if sl_has_webhook:
            st.caption("Webhook: configured (edit in Configuration)")
        else:
            st.warning("Webhook: NOT SET (configure in Configuration page)")

    submit = st.form_submit_button("PERSIST CHANNEL SETTINGS", use_container_width=True)

if submit:
    # Validate Telegram Chat IDs (must be numeric, negative for groups)
    for label, val in [("Channel 1", channel), ("Channel 2", channel_2)]:
        val = val.strip()
        if val and not re.match(r"^-?\d+$", val):
            st.error(f"{label}: Chat ID must be numeric (e.g. -5112822251)")
            st.stop()

    # Only toggles and TG channels — no webhook URL overwriting
    fields = {
        "SEND_ALERTS_TELEGRAM": str(tg_enabled),
        "SEND_ALERTS_TELEGRAM_2": str(tg_enabled_2),
        "CHANNEL": channel.strip(),
        "CHANNEL_2": channel_2.strip(),
        "SEND_ALERTS_DISCORD": str(dc_enabled),
        "SEND_ALERTS_SLACK": str(sl_enabled),
    }
    save_and_reload(fields)
