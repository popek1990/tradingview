"""Wspoldzielony modul autoryzacji dla panelu Streamlit."""

import datetime
import hashlib
import hmac
import time

import extra_streamlit_components as stx
import streamlit as st
from config import Ustawienia

MAKS_PROB = 5
BLOKADA_SEKUND = 300  # 5 minut
COOKIE_NAME = "tv_bot_session"


def get_manager():
    """Zwraca instancje managera ciasteczek."""
    return stx.CookieManager()


@st.cache_resource
def get_global_lock():
    """Globalny licznik nieudanych logowan (wspoldzielony miedzy sesjami)."""
    return {"fail_count": 0, "block_until": 0.0}


def hash_token(password: str) -> str:
    """Tworzy stabilny hash hasla do zapisu w ciasteczku."""
    return hashlib.sha256(password.encode()).hexdigest()


def sprawdz_logowanie():
    """Wymusza logowanie haslem z obsluga ciasteczek i ochrona brute-force."""
    
    # Ukryj elementy interfejsu Streamlit
    st.markdown("""
        <style>
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    cookie_manager = get_manager()
    global_lock = get_global_lock()
    ust = Ustawienia()

    # Sprawdz czy wlasnie nie wylogowano (force logout flag)
    if st.session_state.get("force_logout", False):
        cookie_manager.delete(COOKIE_NAME)
        st.session_state["auth_success"] = False
        st.session_state["force_logout"] = False
        st.rerun()

    # Sprawdz ciasteczko
    cookies = cookie_manager.get_all()
    token = cookies.get(COOKIE_NAME)
    valid_token = hash_token(ust.dashboard_haslo)

    is_logged_in = False
    
    # Priorytet 1: Sesja tymczasowa (zaraz po wpisaniu hasla)
    if st.session_state.get("auth_success", False):
        is_logged_in = True
    # Priorytet 2: Ciasteczko (trwale logowanie)
    elif token and hmac.compare_digest(str(token), valid_token):
        is_logged_in = True

    if is_logged_in:
        with st.sidebar:
            if st.button("Wyloguj", key="logout_btn"):
                st.session_state["force_logout"] = True
                st.session_state["auth_success"] = False
                cookie_manager.delete(COOKIE_NAME)
                st.rerun()
        return

    # --- Ekran logowania ---
    st.title("🔒 Logowanie")

    # Sprawdz blokade globalna
    now = time.time()
    if global_lock["block_until"] > now:
        wait_s = int(global_lock["block_until"] - now)
        st.error(f"⚠️ Zbyt wiele nieudanych prob. System zablokowany na {wait_s}s.")
        st.stop()

    with st.form("login_form"):
        haslo = st.text_input("Haslo dostepu", type="password")
        submit = st.form_submit_button("Zaloguj")

    if submit:
        if hmac.compare_digest(haslo, ust.dashboard_haslo):
            # Sukces - reset licznika
            global_lock["fail_count"] = 0
            # Ustaw flagę w sesji (natychmiastowy dostęp)
            st.session_state["auth_success"] = True
            # Ustaw ciasteczko na 30 dni
            expires = datetime.datetime.now() + datetime.timedelta(days=30)
            cookie_manager.set(COOKIE_NAME, valid_token, expires_at=expires)
            st.success("Logowanie...")
            time.sleep(0.5)
            st.rerun()
        else:
            # Porazka - inkrementacja licznika
            global_lock["fail_count"] += 1
            if global_lock["fail_count"] >= MAKS_PROB:
                global_lock["block_until"] = time.time() + BLOKADA_SEKUND
                global_lock["fail_count"] = 0
                st.error(f"⛔ Blokada systemu na {BLOKADA_SEKUND}s!")
            else:
                prob = MAKS_PROB - global_lock["fail_count"]
                st.error(f"❌ Bledne haslo. Pozostalo prob: {prob}")

    st.stop()
