"""Webhook Aliases — Quick shortcuts for TradingView alerts."""

import re

import requests
import streamlit as st
from auth import check_login
from aliases import load_aliases, save_aliases
from config import Settings
from ui_utils import WEBHOOK_URL, safe_html

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="⚡", layout="wide")

check_login()

REGEX_NAME = re.compile(r"^[a-z0-9_-]{1,64}$")
MAX_ALIASES = 50

st.subheader("WEBHOOK ALIASES")
st.caption("Type short aliases in TradingView Message field instead of complex JSON")

aliases = load_aliases()

# Edit and delete state
if "edit_alias" not in st.session_state:
    st.session_state.edit_alias = None
if "confirm_delete_alias" not in st.session_state:
    st.session_state.confirm_delete_alias = None

# --- Editor at the top when editing ---
editing = st.session_state.edit_alias
if editing and editing in aliases:
    st.markdown(f"### EDITING: /{editing.upper()}")
    if st.button("CANCEL"):
        st.session_state.edit_alias = None
        st.rerun()

    with st.form("form_edit_alias", border=True):
        st.text_input("ALIAS NAME", value=editing, disabled=True)
        template = st.text_area("TEMPLATE CONTENT", value=aliases[editing]["template"],
                                height=150, max_chars=4000,
                                help="Use {variable} for placeholders, e.g. {ticker}")
        variables_str = st.text_input("VARIABLES (comma-separated)",
                                      value=", ".join(aliases[editing].get("variables", [])),
                                      help="Must match {placeholders} in template")
        if st.form_submit_button("SAVE", use_container_width=True):
            if not template.strip():
                st.error("TEMPLATE CONTENT REQUIRED")
                st.stop()
            aliases[editing] = {
                "template": template,
                "variables": [v.strip() for v in variables_str.split(",") if v.strip()],
            }
            save_aliases(aliases)
            st.success(f"UPDATED '/{editing}'")
            st.session_state.edit_alias = None
            st.rerun()

    st.markdown("---")

# --- List of Aliases ---
if aliases:
    st.markdown("### ACTIVE ALIASES")
    for name, data in aliases.items():
        with st.expander(f"[/{name.upper()}]", expanded=False):
            col_preview, col_controls = st.columns([3, 1])
            with col_preview:
                variables = data.get("variables", [])
                st.markdown("**VARIABLES:** " + (", ".join(f"`{v}`" for v in variables) if variables else "_none_"))

                preview = data["template"]
                for v in variables:
                    preview = preview.replace(f"{{{v}}}", f"[{v}]")
                st.code(preview, language=None)

            with col_controls:
                if st.button("EDIT", key=f"aedit_{name}", use_container_width=True):
                    st.session_state.edit_alias = name
                    st.rerun()
                if st.button("TEST", key=f"atest_{name}", use_container_width=True):
                    settings = Settings()
                    defaults = {"ticker": "BTCUSDT", "exchange": "BINANCE", "close": "69000.00",
                                "open": "68000.00", "high": "70000.00", "low": "67000.00",
                                "volume": "1234.56", "interval": "1D", "time": "2026-02-28"}
                    test_values = {v: defaults.get(v, f"TEST_{v.upper()}") for v in variables}
                    test_msg = f"/{name} " + " ".join(test_values[v] for v in variables) if variables else f"/{name}"
                    try:
                        resp = requests.post(
                            f"{WEBHOOK_URL}/webhook",
                            json={"key": settings.sec_key, "msg": test_msg},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            st.success("SENT TO TELEGRAM")
                        else:
                            st.error(f"FAILED: HTTP {resp.status_code}")
                    except Exception as e:
                        st.error(f"ERROR: {e}")
                # Two-step delete
                if st.session_state.confirm_delete_alias == name:
                    st.warning("Are you sure?")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("YES", key=f"ayes_{name}", use_container_width=True):
                            del aliases[name]
                            save_aliases(aliases)
                            st.session_state.confirm_delete_alias = None
                            st.rerun()
                    with c_no:
                        if st.button("NO", key=f"ano_{name}", use_container_width=True):
                            st.session_state.confirm_delete_alias = None
                            st.rerun()
                else:
                    if st.button("DELETE", key=f"adel_{name}", use_container_width=True):
                        st.session_state.confirm_delete_alias = name
                        st.rerun()

            # TradingView shortcut
            variables = data.get("variables", [])
            tv_shortcut = f"/{name}"
            if variables:
                tv_shortcut += " " + " ".join(f"{{{{{v}}}}}" for v in variables)
            safe_shortcut = safe_html(tv_shortcut)
            st.markdown(
                f'<div class="terminal-log" style="font-size: 12px; padding: 10px;">'
                f'<strong>TradingView Message:</strong> {safe_shortcut}</div>',
                unsafe_allow_html=True,
            )
else:
    st.info("NO ALIASES DEFINED")

# --- New Alias (only when not editing) ---
if not editing:
    st.markdown("---")
    st.markdown("### NEW ALIAS")
    with st.form("form_new_alias", border=True):
        new_name = st.text_input("ALIAS NAME (a-z, 0-9, _, -)", max_chars=64)
        new_template = st.text_area("TEMPLATE CONTENT", height=150, max_chars=4000,
                                    help="Use {variable} for placeholders, e.g. {ticker}")
        new_variables = st.text_input("VARIABLES (comma-separated)",
                                      help="Must match {placeholders} in template")
        if st.form_submit_button("CREATE", use_container_width=True):
            name_to_save = new_name.strip().lower().replace(" ", "_")
            if not name_to_save or not new_template.strip():
                st.error("FIELDS REQUIRED")
                st.stop()
            if not REGEX_NAME.match(name_to_save):
                st.error("INVALID NAME: use only a-z, 0-9, _, - (max 64 chars)")
                st.stop()
            if len(aliases) >= MAX_ALIASES:
                st.error(f"MAX ALIASES REACHED ({MAX_ALIASES})")
                st.stop()
            if name_to_save in aliases:
                st.error(f"ALIAS '/{name_to_save}' ALREADY EXISTS — use EDIT instead")
                st.stop()
            aliases[name_to_save] = {
                "template": new_template,
                "variables": [v.strip() for v in new_variables.split(",") if v.strip()],
            }
            save_aliases(aliases)
            st.success(f"CREATED '/{name_to_save}'")
            st.rerun()
