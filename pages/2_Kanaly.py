"""Strona kanalow — wlaczanie/wylaczanie kanalow i ustawienia specyficzne."""

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

st.title("📡 Kanaly powiadomien")
st.caption("Wlaczanie/wylaczanie kanalow i ich ustawienia")

ust = Ustawienia()

# --- Skanowanie grup Telegram ---
if "znalezione_grupy" not in st.session_state:
    st.session_state.znalezione_grupy = {}

col_scan, col_info = st.columns([1, 3])
with col_scan:
    if st.button("🔄 Skanuj dostępne grupy"):
        if not ust.tg_token:
            st.error("Brak tokena Telegram w konfiguracji!")
        else:
            try:
                bot = Bot(token=ust.tg_token)
                updates = bot.get_updates()
                grupy = {}
                for u in updates:
                    if u.message and u.message.chat.type in ["group", "supergroup", "channel"]:
                        chat = u.message.chat
                        grupy[str(chat.id)] = chat.title or chat.username or str(chat.id)
                
                if not grupy:
                    st.warning("Nie znaleziono nowych grup. Wyślij dowolną wiadomość do bota na grupie i spróbuj ponownie.")
                else:
                    st.session_state.znalezione_grupy = grupy
                    st.success(f"Znaleziono {len(grupy)} grup!")
            except Exception as e:
                st.error(f"Błąd podczas skanowania: {e}")

with col_info:
    if st.session_state.znalezione_grupy:
        st.info("Wybierz grupę z listy poniżej lub wpisz ID ręcznie.")
    else:
        st.caption("Aby grupa pojawiła się na liście, wyślij wiadomość do bota na tej grupie.")

# Helper do wyboru grupy
def renderuj_wybor_grupy(label, current_value, key_prefix):
    opcje = {"Wpisz ręcznie / Inna": None}
    dla_selectbox = ["Wpisz ręcznie / Inna"]
    
    # Budowanie listy opcji
    current_in_list = False
    for gid, gtitle in st.session_state.znalezione_grupy.items():
        label_opt = f"{gtitle} ({gid})"
        opcje[label_opt] = gid
        dla_selectbox.append(label_opt)
        if str(gid) == str(current_value):
            current_in_list = True

    # Wybor domyslnego indeksu
    index = 0
    if current_in_list:
        for i, opt in enumerate(dla_selectbox):
            if opcje[opt] == str(current_value):
                index = i
                break
    
    wybor = st.selectbox(
        f"Wybierz grupę ({label})", 
        options=dla_selectbox, 
        index=index,
        key=f"{key_prefix}_select"
    )

    final_val = current_value
    if wybor == "Wpisz ręcznie / Inna":
        final_val = st.text_input(f"ID grupy {label} (wpisz ręcznie)", value=current_value, key=f"{key_prefix}_input")
    else:
        final_val = opcje[wybor]
        st.text_input(f"ID grupy {label}", value=final_val, disabled=True, key=f"{key_prefix}_disabled")
    
    return final_val

with st.form("formularz_kanalow"):
    # --- Telegram — Grupa 1 ---
    st.markdown("### 📱 Telegram — Grupa 1")
    tg_wl = st.toggle("Wlacz Telegram / Grupa 1", value=ust.wyslij_alerty_telegram)
    
    # Wybor grupy 1
    kanal = renderuj_wybor_grupy("Telegram (domyślna)", ust.kanal, "grp1")

    st.markdown("---")

    # --- Telegram — Grupa 2 ---
    st.markdown("### 📱 Telegram — Grupa 2")
    tg_wl_2 = st.toggle("Wlacz Telegram / Grupa 2", value=ust.wyslij_alerty_telegram_2)
    
    # Wybor grupy 2
    kanal_2 = renderuj_wybor_grupy("Telegram (druga)", ust.kanal_2, "grp2")

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
        "WYSLIJ_ALERTY_TELEGRAM_2": str(tg_wl_2),
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
