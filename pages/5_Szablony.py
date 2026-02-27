"""Strona szablonow — zarzadzanie szablonami wiadomosci."""

import streamlit as st
from auth import sprawdz_logowanie
from szablony import wczytaj_szablony, zapisz_szablony

sprawdz_logowanie()

st.title("📝 Szablony wiadomosci")
st.caption("Definiuj szablony raz — uzywaj w TradingView bez formatowania")

szablony = wczytaj_szablony()

# Stan edycji — przechowywany w session_state
if "edytuj_szablon" not in st.session_state:
    st.session_state.edytuj_szablon = None

# --- Lista istniejacych szablonow ---
if szablony:
    st.markdown("### Istniejace szablony")
    for nazwa, dane in szablony.items():
        with st.expander(f"📄 {nazwa}", expanded=False):
            st.markdown("**Zmienne:** " + ", ".join(f"`{z}`" for z in dane.get("zmienne", [])))
            st.markdown("**Podglad:**")
            # Podglad z przykladowymi danymi
            podglad = dane["tresc"]
            for z in dane.get("zmienne", []):
                podglad = podglad.replace(f"{{{z}}}", f"[{z}]")
            st.code(podglad, language=None)

            # Gotowy JSON do wklejenia w TradingView
            zmienne_json = ", ".join(
                f'"{z}": "{{{{{{{z}}}}}}}"' for z in dane.get("zmienne", [])
            )
            tv_json = '{"szablon": "' + nazwa + '"'
            if zmienne_json:
                tv_json += ", " + zmienne_json
            tv_json += "}"
            st.markdown("**Do wklejenia w TradingView (Message):**")
            st.code(tv_json, language="json")

            # Przyciski edycji i usuwania
            kol1, kol2 = st.columns(2)
            with kol1:
                if st.button(f"✏️ Edytuj", key=f"edytuj_{nazwa}", use_container_width=True):
                    st.session_state.edytuj_szablon = nazwa
                    st.rerun()
            with kol2:
                if st.button(f"🗑️ Usun", key=f"usun_{nazwa}", use_container_width=True):
                    del szablony[nazwa]
                    zapisz_szablony(szablony)
                    st.toast(f"✅ Szablon '{nazwa}' usuniety!")
                    st.rerun()
else:
    st.info("Brak szablonow — dodaj pierwszy ponizej")

st.markdown("---")

# --- Formularz dodawania/edycji ---
edytowany = st.session_state.edytuj_szablon
if edytowany and edytowany in szablony:
    st.markdown(f"### ✏️ Edytuj szablon: {edytowany}")
    domyslna_nazwa = edytowany
    domyslna_tresc = szablony[edytowany]["tresc"]
    domyslne_zmienne = ", ".join(szablony[edytowany].get("zmienne", []))
    if st.button("Anuluj edycje"):
        st.session_state.edytuj_szablon = None
        st.rerun()
else:
    st.markdown("### Dodaj nowy szablon")
    domyslna_nazwa = ""
    domyslna_tresc = ""
    domyslne_zmienne = ""

with st.form("formularz_szablonu"):
    nazwa = st.text_input(
        "Nazwa szablonu",
        value=domyslna_nazwa,
        placeholder="np. target, buy, sell",
        help="Krotka nazwa bez spacji — uzyjesz jej w TradingView",
        disabled=bool(edytowany),
    )

    tresc = st.text_area(
        "Tresc szablonu",
        value=domyslna_tresc,
        height=200,
        placeholder=(
            "🎯 *Target* — *{ticker}*\n"
            "Cena: *${close}* | Gielda: _{exchange}_\n\n"
            "_Trzymaj sie planu, Popek!_"
        ),
        help="Uzyj {nazwa_zmiennej} jako placeholder. Markdown TG: *bold*, _italic_, `code`",
    )

    zmienne_str = st.text_input(
        "Zmienne (oddzielone przecinkiem)",
        value=domyslne_zmienne,
        placeholder="ticker, exchange, close",
        help="Nazwy zmiennych uzytych w szablonie jako {zmienna}",
    )

    zapisz = st.form_submit_button("Zapisz szablon", use_container_width=True)

if zapisz:
    nazwa_do_zapisu = (edytowany or nazwa).strip().lower().replace(" ", "_")
    if not nazwa_do_zapisu:
        st.error("Podaj nazwe szablonu")
        st.stop()
    if not tresc.strip():
        st.error("Podaj tresc szablonu")
        st.stop()

    zmienne = [z.strip() for z in zmienne_str.split(",") if z.strip()]

    szablony[nazwa_do_zapisu] = {
        "tresc": tresc,
        "zmienne": zmienne,
    }
    zapisz_szablony(szablony)

    st.success(f"Szablon '{nazwa_do_zapisu}' zapisany!")
    st.toast(f"✅ Szablon '{nazwa_do_zapisu}' zapisany!")

    # Pokaz gotowy JSON
    if zmienne:
        zmienne_json = ", ".join(
            f'"{z}": "{{{{{{{z}}}}}}}"' for z in zmienne
        )
        tv_json = f'{{"szablon": "{nazwa_do_zapisu}", {zmienne_json}}}'
    else:
        tv_json = f'{{"szablon": "{nazwa_do_zapisu}"}}'

    st.markdown("**Gotowy JSON do wklejenia w TradingView:**")
    st.code(tv_json, language="json")

    st.session_state.edytuj_szablon = None
    st.rerun()
