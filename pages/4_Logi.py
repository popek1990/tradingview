"""System Logs — Minimalist Terminal Style."""

import os
import streamlit as st
from auth import sprawdz_logowanie

# Must be first Streamlit command
st.set_page_config(page_title="TV-BOT | LOGS", page_icon="📋", layout="wide")

sprawdz_logowanie()

SCIEZKA_LOGOW = "logs/webhook.log"
st.subheader("📋 SYSTEM OPERATIONAL LOGS")

# Filtry
with st.container(border=True):
    kol1, kol2, kol3 = st.columns([1, 2, 1])
    with kol1:
        poziom = st.selectbox("LEVEL FILTER", ["ALL", "ERROR", "WARNING", "INFO"])
    with kol2:
        szukaj = st.text_input("SEARCH PATTERN")
    with kol3:
        ile_linii = st.number_input("LINES TO TAIL", min_value=10, max_value=5000, value=200, step=50)

if st.button("REFRESH LOG STREAM", use_container_width=True):
    st.rerun()

st.markdown("---")

if not os.path.exists(SCIEZKA_LOGOW):
    st.warning("LOG FILE NOT FOUND. Server may not have initialized yet.")
else:
    try:
        with open(SCIEZKA_LOGOW, encoding="utf-8") as f:
            linie = f.readlines()

        # Ostatnie N linii
        linie = linie[-ile_linii:]

        # Filtrowanie po poziomie
        if poziom != "ALL":
            linie = [l for l in linie if f"[{poziom}]" in l]

        # Filtrowanie po tekscie
        if szukaj:
            szukaj_lower = szukaj.lower()
            linie = [l for l in linie if szukaj_lower in l.lower()]

        if linie:
            st.caption(f"STREAMING {len(linie)} LINES...")
            # Styl terminala
            log_text = "".join(linie)
            st.markdown(f'<div class="terminal-log" style="height: 500px; overflow-y: scroll; white-space: pre-wrap; font-size: 12px;">{log_text}</div>', unsafe_allow_html=True)
        else:
            st.info("NO LOGS MATCHING CRITERIA")
    except Exception as e:
        st.error(f"IO ERROR: {e}")
