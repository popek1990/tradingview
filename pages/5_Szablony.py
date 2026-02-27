"""Strona szablonow — zarzadzanie szablonami wiadomosci."""

import streamlit as st
from auth import sprawdz_logowanie
from szablony import wczytaj_szablony, zapisz_szablony

sprawdz_logowanie()

st.title("📝 Szablony wiadomosci")
st.caption("Definiuj szablony raz — uzywaj w TradingView bez formatowania")

szablony = wczytaj_szablony()

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

            # Przycisk usuwania
            if st.button(f"Usun szablon '{nazwa}'", key=f"usun_{nazwa}"):
                del szablony[nazwa]
                zapisz_szablony(szablony)
                st.toast(f"✅ Szablon '{nazwa}' usuniety!")
                st.rerun()
else:
    st.info("Brak szablonow — dodaj pierwszy ponizej")

st.markdown("---")

# --- Formularz dodawania/edycji ---
st.markdown("### Dodaj / edytuj szablon")

with st.form("formularz_szablonu"):
    nazwa = st.text_input(
        "Nazwa szablonu",
        placeholder="np. target, buy, sell",
        help="Krotka nazwa bez spacji — uzyjesz jej w TradingView",
    )

    tresc = st.text_area(
        "Tresc szablonu",
        height=200,
        placeholder=(
            "🎯 *Target* #{ticker} na gieldzie *{exchange}* ✔️\n\n"
            "🎯 *${ticker}* osiagnelo cene *{close}* ✔️\n\n"
            "_...Popek, trzymaj sie strategi!_"
        ),
        help="Uzyj {nazwa_zmiennej} jako placeholder. Markdown TG dziala: *bold*, _italic_, `code`",
    )

    zmienne_str = st.text_input(
        "Zmienne (oddzielone przecinkiem)",
        placeholder="ticker, exchange, close",
        help="Nazwy zmiennych uzytych w szablonie jako {zmienna}",
    )

    zapisz = st.form_submit_button("Zapisz szablon", use_container_width=True)

if zapisz:
    nazwa = nazwa.strip().lower().replace(" ", "_")
    if not nazwa:
        st.error("Podaj nazwe szablonu")
        st.stop()
    if not tresc.strip():
        st.error("Podaj tresc szablonu")
        st.stop()

    zmienne = [z.strip() for z in zmienne_str.split(",") if z.strip()]

    szablony[nazwa] = {
        "tresc": tresc,
        "zmienne": zmienne,
    }
    zapisz_szablony(szablony)

    st.success(f"Szablon '{nazwa}' zapisany!")
    st.toast(f"✅ Szablon '{nazwa}' zapisany!")

    # Pokaz gotowy JSON
    if zmienne:
        zmienne_json = ", ".join(
            f'"{z}": "{{{{{{{z}}}}}}}"' for z in zmienne
        )
        tv_json = f'{{"szablon": "{nazwa}", {zmienne_json}}}'
    else:
        tv_json = f'{{"szablon": "{nazwa}"}}'

    st.markdown("**Gotowy JSON do wklejenia w TradingView:**")
    st.code(tv_json, language="json")

    st.rerun()
