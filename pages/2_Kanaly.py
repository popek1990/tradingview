"""Strona kanalow — wlaczanie/wylaczanie kanalow i ustawienia specyficzne."""

import os
import streamlit as st
import requests
from dotenv import set_key
from auth import sprawdz_logowanie
from config import Ustawienia

sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
SCIEZKA_ENV = ".env"

st.title("📡 Kanaly powiadomien")
st.caption("Wlaczanie/wylaczanie kanalow i ich ustawienia")

ust = Ustawienia()

with st.form("formularz_kanalow"):
    # --- Telegram ---
    st.markdown("### 📱 Telegram")
    tg_wl = st.toggle("Wlacz Telegram", value=ust.wyslij_alerty_telegram)
    kanal = st.text_input("ID grupy Telegram (domyslna)", value=ust.kanal)

    st.markdown("---")

    # --- Telegram — Grupa 2 ---
    st.markdown("### 📱 Telegram — Grupa 2")
    st.caption("Opcjonalna druga grupa — alerty beda wysylane na obie grupy jednoczesnie")
    kanal_2 = st.text_input("ID drugiej grupy Telegram (zostaw puste aby wylaczyc)", value=ust.kanal_2)

    st.markdown("---")

    # --- Discord ---
    st.markdown("### 💬 Discord")
    dc_wl = st.toggle("Wlacz Discord", value=ust.wyslij_alerty_discord)

    st.markdown("---")

    # --- Slack ---
    st.markdown("### 🔔 Slack")
    sl_wl = st.toggle("Wlacz Slack", value=ust.wyslij_alerty_slack)

    zapisz = st.form_submit_button("Zapisz ustawienia kanalow", use_container_width=True)

if zapisz:
    stary_sec_key = ust.sec_key

    pola = {
        "WYSLIJ_ALERTY_TELEGRAM": str(tg_wl),
        "KANAL": kanal,
        "KANAL_2": kanal_2,
        "WYSLIJ_ALERTY_DISCORD": str(dc_wl),
        "WYSLIJ_ALERTY_SLACK": str(sl_wl),
    }

    bledy_zapisu = []
    for klucz, wartosc in pola.items():
        sukces, _, _ = set_key(SCIEZKA_ENV, klucz, wartosc)
        if not sukces:
            bledy_zapisu.append(klucz)

    if bledy_zapisu:
        st.error(f"Nie udalo sie zapisac: {', '.join(bledy_zapisu)}")
        st.stop()

    st.success("Ustawienia kanalow zapisane do .env")
    st.toast("✅ Kanaly zapisane!")

    try:
        resp = requests.post(
            f"{WEBHOOK_URL}/przeladuj-config",
            json={"key": stary_sec_key},
            timeout=5,
        )
        if resp.status_code == 200:
            st.success("Serwer webhook przeladowal konfiguracje")
        else:
            st.warning(f"Serwer webhook zwrocil status {resp.status_code}")
    except Exception:
        st.info("Nie udalo sie polaczyc z serwerem webhook — przeladuj recznie lub zrestartuj kontener")
