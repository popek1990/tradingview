"""Strona konfiguracji — edycja kluczy i tokenow w .env."""

import os
import streamlit as st
import requests
from dotenv import set_key
from auth import sprawdz_logowanie
from config import Ustawienia

sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
SCIEZKA_ENV = ".env"

st.title("🔑 Konfiguracja kluczy")
st.caption("Edycja wrazliwych danych zapisywanych w pliku .env")

ust = Ustawienia()

with st.form("formularz_kluczy"):
    st.markdown("#### Klucz bezpieczenstwa")
    sec_key = st.text_input(
        "SEC_KEY (musi pasowac do 'key' w alercie TradingView)",
        value=ust.sec_key,
        type="password",
    )

    st.markdown("---")
    st.markdown("#### Telegram")
    tg_token = st.text_input(
        "TG_TOKEN (token bota z @BotFather)",
        value=ust.tg_token,
        type="password",
    )

    st.markdown("---")
    st.markdown("#### Discord")
    discord_webhook = st.text_input(
        "DISCORD_WEBHOOK (ID webhooka, np. 789842.../BFeBBr...)",
        value=ust.discord_webhook,
        type="password",
    )

    st.markdown("---")
    st.markdown("#### Slack")
    slack_webhook = st.text_input(
        "SLACK_WEBHOOK (ID webhooka, np. T000/B000/XXXX)",
        value=ust.slack_webhook,
        type="password",
    )

    st.markdown("---")
    st.markdown("#### Panel Streamlit")
    dashboard_haslo = st.text_input(
        "DASHBOARD_HASLO (haslo dostepu do tego panelu)",
        value=ust.dashboard_haslo,
        type="password",
    )

    zapisz = st.form_submit_button("Zapisz konfiguracje", use_container_width=True)

if zapisz:
    if not dashboard_haslo.strip():
        st.error("Haslo panelu nie moze byc puste!")
        st.stop()

    # Zapamietaj stary klucz przed nadpisaniem (potrzebny do przeladowania configa)
    stary_sec_key = ust.sec_key

    pola = {
        "SEC_KEY": sec_key,
        "TG_TOKEN": tg_token,
        "DISCORD_WEBHOOK": discord_webhook,
        "SLACK_WEBHOOK": slack_webhook,
        "DASHBOARD_HASLO": dashboard_haslo,
    }

    bledy_zapisu = []
    for klucz, wartosc in pola.items():
        sukces, _, _ = set_key(SCIEZKA_ENV, klucz, wartosc)
        if not sukces:
            bledy_zapisu.append(klucz)

    if bledy_zapisu:
        st.error(f"Nie udalo sie zapisac: {', '.join(bledy_zapisu)}")
        st.stop()

    st.success("Konfiguracja zapisana do .env")
    st.toast("✅ Konfiguracja zapisana!")

    # Przeladuj config na serwerze webhook (uzywajac STAREGO klucza)
    try:
        resp = requests.post(
            f"{WEBHOOK_URL}/przeladuj-config",
            json={"key": stary_sec_key},
            timeout=5,
        )
        if resp.status_code == 200:
            st.success("Serwer webhook przeladowal konfiguracje")
        else:
            st.warning(f"Serwer webhook zwrocil status {resp.status_code} — moze wymagac restartu")
    except Exception:
        st.info("Nie udalo sie polaczyc z serwerem webhook — przeladuj recznie lub zrestartuj kontener")
