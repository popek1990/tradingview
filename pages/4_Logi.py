"""Strona logow — podglad logow serwera webhook."""

import os
import streamlit as st
from auth import sprawdz_logowanie

sprawdz_logowanie()

SCIEZKA_LOGOW = "logs/webhook.log"

st.title("📋 Logi serwera")
st.caption("Podglad logow serwera webhook")

# Filtry
kol1, kol2 = st.columns([1, 2])
with kol1:
    poziom = st.selectbox("Filtruj poziom", ["Wszystkie", "ERROR", "WARNING", "INFO"])
with kol2:
    szukaj = st.text_input("Szukaj w logach")

ile_linii = st.slider("Liczba ostatnich linii", min_value=50, max_value=1000, value=200, step=50)

if st.button("Odswiez logi", use_container_width=True):
    st.rerun()

st.markdown("---")

if not os.path.exists(SCIEZKA_LOGOW):
    st.info("Plik logow nie istnieje jeszcze — pojawi sie po pierwszym uruchomieniu serwera webhook.")
else:
    try:
        with open(SCIEZKA_LOGOW, encoding="utf-8") as f:
            linie = f.readlines()

        # Ostatnie N linii
        linie = linie[-ile_linii:]

        # Filtrowanie po poziomie
        if poziom != "Wszystkie":
            linie = [l for l in linie if f"[{poziom}]" in l]

        # Filtrowanie po tekscie
        if szukaj:
            szukaj_lower = szukaj.lower()
            linie = [l for l in linie if szukaj_lower in l.lower()]

        if linie:
            st.text(f"Wyswietlam {len(linie)} linii")
            st.code("".join(linie), language="log")
        else:
            st.info("Brak logow pasujacych do filtrow")
    except Exception as e:
        st.error(f"Blad odczytu logow: {e}")
