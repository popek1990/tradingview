"""Wspoldzielony modul autoryzacji dla panelu Streamlit."""

import hmac
import time

import streamlit as st
from config import Ustawienia

MAKS_PROB = 5
BLOKADA_SEKUND = 300  # 5 minut
TIMEOUT_SESJI = 1800  # 30 minut


def sprawdz_logowanie():
    """Wymusza logowanie haslem przed dostepem do strony."""
    if "zalogowany" not in st.session_state:
        st.session_state.zalogowany = False
    if "proby_logowania" not in st.session_state:
        st.session_state.proby_logowania = 0
    if "blokada_do" not in st.session_state:
        st.session_state.blokada_do = 0.0
    if "ostatnia_aktywnosc" not in st.session_state:
        st.session_state.ostatnia_aktywnosc = 0.0

    # Sprawdz timeout sesji
    if st.session_state.zalogowany:
        if time.time() - st.session_state.ostatnia_aktywnosc > TIMEOUT_SESJI:
            st.session_state.zalogowany = False
            st.toast("Sesja wygasla po 30 minutach nieaktywnosci")
        else:
            st.session_state.ostatnia_aktywnosc = time.time()

    # Przycisk wylogowania w sidebarze
    if st.session_state.zalogowany:
        with st.sidebar:
            if st.button("Wyloguj"):
                st.session_state.zalogowany = False
                st.session_state.ostatnia_aktywnosc = 0.0
                st.rerun()
        return

    st.title("Logowanie")

    # Sprawdz blokade czasowa
    if st.session_state.blokada_do > time.time():
        pozostalo = int(st.session_state.blokada_do - time.time())
        st.error(f"Zbyt wiele prob. Sprobuj za {pozostalo}s.")
        st.stop()

    # Reset licznika po wygasnieciu blokady
    if st.session_state.proby_logowania >= MAKS_PROB:
        st.session_state.proby_logowania = 0

    haslo = st.text_input("Haslo dostepu", type="password")
    if st.button("Zaloguj"):
        ust = Ustawienia()
        if hmac.compare_digest(haslo, ust.dashboard_haslo):
            st.session_state.zalogowany = True
            st.session_state.proby_logowania = 0
            st.session_state.ostatnia_aktywnosc = time.time()
            st.rerun()
        else:
            st.session_state.proby_logowania += 1
            if st.session_state.proby_logowania >= MAKS_PROB:
                st.session_state.blokada_do = time.time() + BLOKADA_SEKUND
                st.error(f"Zbyt wiele prob. Blokada na {BLOKADA_SEKUND // 60} minut.")
            else:
                pozostalo_prob = MAKS_PROB - st.session_state.proby_logowania
                st.error(f"Nieprawidlowe haslo (pozostalo prob: {pozostalo_prob})")
    st.stop()
