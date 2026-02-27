"""Strona testowa — reczne wysylanie alertow testowych."""

import os
import streamlit as st
import requests
from auth import sprawdz_logowanie
from config import Ustawienia

sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")

st.title("🧪 Wyslij alert testowy")
st.caption("Wysyla testowy alert przez serwer webhook (pelny pipeline)")

ust = Ustawienia()

with st.form("formularz_testu"):
    msg = st.text_area(
        "Tresc wiadomosci",
        value="Test *alert* z panelu Streamlit `{{close}}`",
        max_chars=4000,
    )

    st.markdown("#### Opcjonalne nadpisania kanalow")
    st.caption("Zostaw puste aby uzyc domyslnych wartosci z konfiguracji")

    telegram_override = st.text_input("ID kanalu Telegram (opcjonalnie)")
    discord_override = st.text_input("ID webhooka Discord (opcjonalnie)")
    slack_override = st.text_input("ID webhooka Slack (opcjonalnie)")

    wyslij = st.form_submit_button("Wyslij testowy alert", use_container_width=True)

if wyslij:
    if not ust.sec_key:
        st.error("Brak SEC_KEY w .env — skonfiguruj klucz na stronie Konfiguracja")
        st.stop()

    import json
    
    # Proba parsowania jako JSON (np. jesli wklejono szablon z TV)
    msg_to_send = msg
    try:
        potential_json = json.loads(msg.strip())
        if isinstance(potential_json, dict):
            # To jest JSON - przygotuj payload scalony
            payload = {
                "key": ust.sec_key,
                **potential_json
            }
        else:
            raise ValueError()
    except Exception:
        # To nie jest JSON - uzyj starego formatu
        payload = {
            "key": ust.sec_key,
            "msg": msg,
        }

    if telegram_override.strip():
        payload["telegram"] = telegram_override.strip()
    if discord_override.strip():
        payload["discord"] = discord_override.strip()
    if slack_override.strip():
        payload["slack"] = slack_override.strip()

    try:
        resp = requests.post(
            f"{WEBHOOK_URL}/webhook",
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            st.success("Alert testowy wyslany pomyslnie!")
            st.toast("✅ Alert wyslany!")
            st.json(resp.json())
        else:
            st.error(f"Blad: HTTP {resp.status_code}")
            try:
                st.json(resp.json())
            except Exception:
                st.code(resp.text)
    except requests.ConnectionError:
        st.error("Nie mozna polaczyc sie z serwerem webhook")
    except Exception as e:
        st.error(f"Blad: {e}")
