"""Channels Configuration — Minimalist Terminal Style."""

import streamlit as st
from telegram import Bot
from auth import check_login
from config import Settings
from ui_utils import save_and_reload

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="📡", layout="wide")

check_login()

# Settings loaded after login check
settings = Settings()

st.subheader("NOTIFICATION CHANNELS")

# --- Telegram Scanner ---
if "found_groups" not in st.session_state:
    st.session_state.found_groups = {}

with st.expander("TG NETWORK SCANNER", expanded=False):
    col_scan, col_info = st.columns([1, 2])
    with col_scan:
        if st.button("RUN SCAN", use_container_width=True):
            if not settings.tg_token: st.error("MISSING TG_TOKEN!")
            else:
                try:
                    bot = Bot(token=settings.tg_token)
                    bot_info = bot.get_me()
                    st.info(f"CONNECTED: @{bot_info.username}")
                    updates = bot.get_updates(timeout=10, allowed_updates=["message", "channel_post", "my_chat_member"])
                    groups = {}
                    for u in updates:
                        chat = u.message.chat if u.message else (u.channel_post.chat if u.channel_post else (u.my_chat_member.chat if u.my_chat_member else None))
                        if chat and chat.type in ["group", "supergroup", "channel"]:
                            groups[str(chat.id)] = chat.title or chat.username or str(chat.id)
                    if not groups: st.warning("NO NODES FOUND")
                    else:
                        st.session_state.found_groups.update(groups)
                        st.success(f"FOUND {len(groups)} NODES")
                except Exception as e: st.error(f"SCAN ERROR: {e}")
    with col_info:
        st.caption(f"Status: {len(st.session_state.found_groups)} nodes cached.")

# Helper for group selection
def render_group_selector(label, current_value, key_prefix):
    options = {"[ MANUAL ENTRY ]": None}
    selectbox_options = ["[ MANUAL ENTRY ]"]
    current_in_list = False
    for gid, gtitle in st.session_state.found_groups.items():
        label_opt = f"{gtitle} ({gid})"
        options[label_opt] = gid
        selectbox_options.append(label_opt)
        if str(gid) == str(current_value): current_in_list = True
    index = 0
    if current_in_list:
        for i, opt in enumerate(selectbox_options):
            if options[opt] == str(current_value):
                index = i; break
    selection = st.selectbox(f"{label} Target", options=selectbox_options, index=index, key=f"{key_prefix}_select")
    if selection == "[ MANUAL ENTRY ]":
        return st.text_input(f"ID: {label} (Manual)", value=current_value, key=f"{key_prefix}_input")
    else:
        val = options[selection]
        st.text_input(f"ID: {label} (Selected)", value=val, disabled=True, key=f"{key_prefix}_disabled")
        return val

with st.form("form_channels", border=True):
    col_tg1, col_tg2 = st.columns(2)
    with col_tg1:
        st.markdown("#### TELEGRAM GROUP 1")
        tg_enabled = st.toggle("ENABLE GROUP 1", value=settings.send_alerts_telegram)
        channel = render_group_selector("Group 1", settings.channel, "grp1")
    with col_tg2:
        st.markdown("#### TELEGRAM GROUP 2")
        tg_enabled_2 = st.toggle("ENABLE GROUP 2", value=settings.send_alerts_telegram_2)
        channel_2 = render_group_selector("Group 2", settings.channel_2, "grp2")

    st.markdown("---")
    # Toggle on/off only — secrets (webhook URL) editable only in Configuration
    col_dc, col_sl = st.columns(2)
    with col_dc:
        st.markdown("#### DISCORD")
        dc_enabled = st.toggle("ENABLE DISCORD", value=settings.send_alerts_discord)
        if settings.discord_webhook:
            st.caption("Webhook: configured (edit in Configuration)")
        else:
            st.warning("Webhook: NOT SET (configure in Configuration page)")
    with col_sl:
        st.markdown("#### SLACK")
        sl_enabled = st.toggle("ENABLE SLACK", value=settings.send_alerts_slack)
        if settings.slack_webhook:
            st.caption("Webhook: configured (edit in Configuration)")
        else:
            st.warning("Webhook: NOT SET (configure in Configuration page)")

    submit = st.form_submit_button("PERSIST CHANNEL SETTINGS", use_container_width=True)

if submit:
    # Only toggles and TG channels — no webhook URL overwriting
    fields = {
        "SEND_ALERTS_TELEGRAM": str(tg_enabled),
        "SEND_ALERTS_TELEGRAM_2": str(tg_enabled_2),
        "CHANNEL": channel,
        "CHANNEL_2": channel_2,
        "SEND_ALERTS_DISCORD": str(dc_enabled),
        "SEND_ALERTS_SLACK": str(sl_enabled),
    }
    save_and_reload(fields)
