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

# --- List of Templates ---
if szablony:
    st.markdown("### 📄 ACTIVE TEMPLATES")
    for nazwa, dane in szablony.items():
        with st.expander(f"[{nazwa.upper()}]", expanded=False):
            col_preview, col_controls = st.columns([3, 1])
            with col_preview:
                st.markdown("**VARIABLES:** " + ", ".join(f"`{z}`" for z in dane.get("zmienne", [])))
                podglad = dane["tresc"]
                for z in dane.get("zmienne", []): podglad = podglad.replace(f"{{{z}}}", f"[{z}]")
                st.code(podglad, language=None)
            with col_controls:
                if st.button(f"EDIT", key=f"edytuj_{nazwa}", use_container_width=True):
                    st.session_state.edytuj_szablon = nazwa; st.rerun()
                if st.button(f"DELETE", key=f"usun_{nazwa}", use_container_width=True):
                    del szablony[nazwa]; zapisz_szablony(szablony); st.rerun()
            
            # TradingView JSON
            zmienne_json = ", ".join(f'"{z}": "{{{{{{{z}}}}}}}"' for z in dane.get("zmienne", []))
            tv_json = '{"szablon": "' + nazwa + '"'
            if zmienne_json: tv_json += ", " + zmienne_json
            tv_json += "}"
            st.markdown(f'<div class="terminal-log" style="font-size: 10px; padding: 10px;">TV MSG: {tv_json}</div>', unsafe_allow_html=True)
else:
    st.info("NO TEMPLATES DEFINED")

st.markdown("---")

# --- Editor ---
edytowany = st.session_state.edytuj_szablon
if edytowany and edytowany in szablony:
    st.markdown(f"### ✏️ EDITOR: {edytowany.upper()}")
    domyslna_nazwa, domyslna_tresc, domyslne_zmienne = edytowany, szablony[edytowany]["tresc"], ", ".join(szablony[edytowany].get("zmienne", []))
    if st.button("CANCEL"): st.session_state.edytuj_szablon = None; st.rerun()
else:
    st.markdown("### ➕ NEW TEMPLATE")
    domyslna_nazwa, domyslna_tresc, domyslne_zmienne = "", "", ""

with st.form("form_template", border=True):
    nazwa = st.text_input("ID", value=domyslna_nazwa, disabled=bool(edytowany))
    tresc = st.text_area("CONTENT", value=domyslna_tresc, height=150)
    zmienne_str = st.text_input("VARIABLES (comma-separated)", value=domyslne_zmienne)
    if st.form_submit_button("SUBMIT", use_container_width=True):
        nazwa_do_zapisu = (edytowany or nazwa).strip().lower().replace(" ", "_")
        if not nazwa_do_zapisu or not tresc.strip(): st.error("FIELDS REQUIRED"); st.stop()
        szablony[nazwa_do_zapisu] = {"tresc": tresc, "zmienne": [z.strip() for z in zmienne_str.split(",") if z.strip()]}
        zapisz_szablony(szablony); st.success(f"PERSISTED '{nazwa_do_zapisu}'"); st.session_state.edytuj_szablon = None; st.rerun()
