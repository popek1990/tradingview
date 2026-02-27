"""Channels Configuration — Minimalist Terminal Style."""

import os
import streamlit as st
import requests
from dotenv import set_key
from telegram import Bot
from auth import sprawdz_logowanie
from config import Ustawienia

sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
SCIEZKA_ENV = ".env"
ust = Ustawienia()

st.subheader("📡 NOTIFICATION CHANNELS")

# --- Telegram Scanner ---
if "znalezione_grupy" not in st.session_state:
    st.session_state.znalezione_grupy = {}

with st.expander("🔄 TG NETWORK SCANNER", expanded=False):
    col_scan, col_info = st.columns([1, 2])
    with col_scan:
        if st.button("RUN SCAN", use_container_width=True):
            if not ust.tg_token: st.error("MISSING TG_TOKEN!")
            else:
                try:
                    bot = Bot(token=ust.tg_token)
                    bot_info = bot.get_me()
                    st.info(f"CONNECTED: @{bot_info.username}")
                    updates = bot.get_updates(timeout=10, allowed_updates=["message", "channel_post", "my_chat_member"])
                    grupy = {}
                    for u in updates:
                        chat = u.message.chat if u.message else (u.channel_post.chat if u.channel_post else (u.my_chat_member.chat if u.my_chat_member else None))
                        if chat and chat.type in ["group", "supergroup", "channel"]:
                            grupy[str(chat.id)] = chat.title or chat.username or str(chat.id)
                    if not grupy: st.warning("NO NODES FOUND")
                    else:
                        st.session_state.znalezione_grupy.update(grupy)
                        st.success(f"FOUND {len(grupy)} NODES")
                except Exception as e: st.error(f"SCAN ERROR: {e}")
    with col_info:
        st.caption(f"Status: {len(st.session_state.znalezione_grupy)} nodes cached.")

# Helper do wyboru grupy
def renderuj_wybor_grupy(label, current_value, key_prefix):
    opcje = {"[ MANUAL ENTRY ]": None}
    dla_selectbox = ["[ MANUAL ENTRY ]"]
    current_in_list = False
    for gid, gtitle in st.session_state.znalezione_grupy.items():
        label_opt = f"{gtitle} ({gid})"
        opcje[label_opt] = gid
        dla_selectbox.append(label_opt)
        if str(gid) == str(current_value): current_in_list = True
    index = 0
    if current_in_list:
        for i, opt in enumerate(dla_selectbox):
            if opcje[opt] == str(current_value):
                index = i; break
    wybor = st.selectbox(f"{label} Target", options=dla_selectbox, index=index, key=f"{key_prefix}_select")
    if wybor == "[ MANUAL ENTRY ]":
        return st.text_input(f"ID: {label} (Manual)", value=current_value, key=f"{key_prefix}_input")
    else:
        val = opcje[wybor]
        st.text_input(f"ID: {label} (Selected)", value=val, disabled=True, key=f"{key_prefix}_disabled")
        return val

with st.form("form_channels", border=True):
    col_tg1, col_tg2 = st.columns(2)
    with col_tg1:
        st.markdown("#### 📱 TELEGRAM GROUP 1")
        tg_wl = st.toggle("ENABLE GROUP 1", value=ust.wyslij_alerty_telegram)
        kanal = renderuj_wybor_grupy("Group 1", ust.kanal, "grp1")
    with col_tg2:
        st.markdown("#### 📱 TELEGRAM GROUP 2")
        tg_wl_2 = st.toggle("ENABLE GROUP 2", value=ust.wyslij_alerty_telegram_2)
        kanal_2 = renderuj_wybor_grupy("Group 2", ust.kanal_2, "grp2")

    st.markdown("---")
    col_dc, col_sl = st.columns(2)
    with col_dc:
        st.markdown("#### 💬 DISCORD")
        dc_wl = st.toggle("ENABLE DISCORD", value=ust.wyslij_alerty_discord)
        dc_id = st.text_input("DISCORD WEBHOOK ID/URL", value=ust.discord_webhook, type="password")
    with col_sl:
        st.markdown("#### 🔔 SLACK")
        sl_wl = st.toggle("ENABLE SLACK", value=ust.wyslij_alerty_slack)
        sl_id = st.text_input("SLACK WEBHOOK ID/URL", value=ust.slack_webhook, type="password")

    zapisz = st.form_submit_button("PERSIST CHANNEL SETTINGS", use_container_width=True)

if zapisz:
    stary_sec_key = ust.sec_key
    pola = {
        "WYSLIJ_ALERTY_TELEGRAM": str(tg_wl),
        "WYSLIJ_ALERTY_TELEGRAM_2": str(tg_wl_2),
        "KANAL": kanal,
        "KANAL_2": kanal_2,
        "WYSLIJ_ALERTY_DISCORD": str(dc_wl),
        "DISCORD_WEBHOOK": dc_id,
        "WYSLIJ_ALERTY_SLACK": str(sl_wl),
        "SLACK_WEBHOOK": sl_id,
    }
    bledy_zapisu = []
    for klucz, wartosc in pola.items():
        sukces, _, _ = set_key(SCIEZKA_ENV, klucz, wartosc)
        if not sukces: bledy_zapisu.append(klucz)
    if bledy_zapisu:
        st.error(f"WRITE FAILED: {', '.join(bledy_zapisu)}")
        st.stop()
    st.success("CHANNELS PERSISTED TO .ENV")
    st.toast("✅ Persisted!")
    try:
        resp = requests.post(f"{WEBHOOK_URL}/przeladuj-config", json={"key": stary_sec_key}, timeout=5)
        if resp.status_code == 200: st.success("WEBHOOK SERVER: CONFIG RELOADED")
        else: st.warning(f"WEBHOOK SERVER: RELOAD FAILED (HTTP {resp.status_code})")
    except Exception: st.info("WEBHOOK SERVER: UNREACHABLE")
