"""Message Templates — Minimalist Terminal Style."""

import streamlit as st
from auth import sprawdz_logowanie
from szablony import wczytaj_szablony, zapisz_szablony

sprawdz_logowanie()

st.subheader("📝 PAYLOAD TEMPLATES")
szablony = wczytaj_szablony()

# Stan edycji
if "edytuj_szablon" not in st.session_state:
    st.session_state.edytuj_szablon = None

# --- Sekcja 1: ACTIVE TEMPLATES ---
if szablony:
    st.markdown("### ACTIVE TEMPLATES")
    for nazwa, dane in szablony.items():
        with st.expander(f"📄 TEMPLATE: {nazwa.upper()}", expanded=False):
            st.markdown("**VARIABLES:** " + ", ".join(f"`{z}`" for z in dane.get("zmienne", [])))
            
            # Podglad
            podglad = dane["tresc"]
            for z in dane.get("zmienne", []):
                podglad = podglad.replace(f"{{{z}}}", f"[{z}]")
            st.markdown("#### RENDER PREVIEW")
            st.code(podglad, language=None)

            # JSON dla TradingView
            zmienne_json = ", ".join(f'"{z}": "{{{{{{{z}}}}}}}"' for z in dane.get("zmienne", []))
            tv_json = '{"szablon": "' + nazwa + '"'
            if zmienne_json: tv_json += ", " + zmienne_json
            tv_json += "}"
            
            st.markdown("#### TRADINGVIEW MESSAGE (JSON)")
            st.markdown(f'<div class="terminal-log" style="font-size: 11px;">{tv_json}</div>', unsafe_allow_html=True)

            # Controls
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"EDIT {nazwa.upper()}", key=f"edytuj_{nazwa}", use_container_width=True):
                    st.session_state.edytuj_szablon = nazwa
                    st.rerun()
            with c2:
                if st.button(f"DELETE {nazwa.upper()}", key=f"usun_{nazwa}", use_container_width=True):
                    del szablony[nazwa]
                    zapisz_szablony(szablony)
                    st.rerun()
else:
    st.info("NO TEMPLATES DEFINED")

st.markdown("---")

# --- Sekcja 2: EDITOR ---
edytowany = st.session_state.edytuj_szablon
if edytowany and edytowany in szablony:
    st.markdown(f"### ✏️ TEMPLATE EDITOR: {edytowany.upper()}")
    domyslna_nazwa = edytowany
    domyslna_tresc = szablony[edytowany]["tresc"]
    domyslne_zmienne = ", ".join(szablony[edytowany].get("zmienne", []))
    if st.button("ABORT EDIT"):
        st.session_state.edytuj_szablon = None
        st.rerun()
else:
    st.markdown("### ➕ ADD NEW TEMPLATE")
    domyslna_nazwa = ""
    domyslna_tresc = ""
    domyslne_zmienne = ""

with st.form("form_template", border=True):
    nazwa = st.text_input("TEMPLATE ID", value=domyslna_nazwa, disabled=bool(edytowany))
    tresc = st.text_area("CONTENT (Markdown supported)", value=domyslna_tresc, height=180)
    zmienne_str = st.text_input("VARIABLES (comma-separated)", value=domyslne_zmienne)

    zapisz = st.form_submit_button("PERSIST TEMPLATE", use_container_width=True)

if zapisz:
    nazwa_do_zapisu = (edytowany or nazwa).strip().lower().replace(" ", "_")
    if not nazwa_do_zapisu or not tresc.strip():
        st.error("REQUIRED FIELDS MISSING")
        st.stop()

    zmienne = [z.strip() for z in zmienne_str.split(",") if z.strip()]
    szablony[nazwa_do_zapisu] = {"tresc": tresc, "zmienne": zmienne}
    zapisz_szablony(szablony)

    st.success(f"TEMPLATE '{nazwa_do_zapisu}' PERSISTED")
    st.session_state.edytuj_szablon = None
    st.rerun()
