"""Webhook Aliases — Quick shortcuts for TradingView alerts."""

import re
import streamlit as st
from auth import check_login
from aliases import load_aliases, save_aliases
from ui_utils import safe_html

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

# --- List of Aliases ---
if aliases:
    st.markdown("### ACTIVE ALIASES")
    for name, data in aliases.items():
        with st.expander(f"[/{name.upper()}]", expanded=False):
            col_preview, col_controls = st.columns([3, 1])
            with col_preview:
                variables = data.get("variables", [])
                st.markdown("**VARIABLES:** " + (", ".join(f"`{v}`" for v in variables) if variables else "_none_"))

                # Preview with placeholders
                preview = data["template"]
                for v in variables:
                    preview = preview.replace(f"{{{v}}}", f"[{v}]")
                st.code(preview, language=None)

            with col_controls:
                if st.button("EDIT", key=f"aedit_{name}", use_container_width=True):
                    st.session_state.edit_alias = name
                    st.rerun()
                # Two-step delete confirmation
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

st.markdown("---")

# --- Editor ---
editing = st.session_state.edit_alias
if editing and editing in aliases:
    st.markdown(f"### EDITOR: /{editing.upper()}")
    default_name = editing
    default_template = aliases[editing]["template"]
    default_variables = ", ".join(aliases[editing].get("variables", []))
    if st.button("CANCEL"):
        st.session_state.edit_alias = None
        st.rerun()
else:
    st.markdown("### NEW ALIAS")
    default_name, default_template, default_variables = "", "", ""

with st.form("form_alias", border=True):
    name = st.text_input("ALIAS NAME (a-z, 0-9, _, -)", value=default_name, max_chars=64, disabled=bool(editing))
    template = st.text_area("TEMPLATE CONTENT", value=default_template, height=150, max_chars=4000,
                            help="Use {variable} for placeholders, e.g. {ticker}")
    variables_str = st.text_input("VARIABLES (comma-separated)", value=default_variables,
                                  help="Must match {placeholders} in template, e.g. ticker, exchange, close")
    if st.form_submit_button("SUBMIT", use_container_width=True):
        name_to_save = (editing or name).strip().lower().replace(" ", "_")
        if not name_to_save or not template.strip():
            st.error("FIELDS REQUIRED")
            st.stop()
        if not REGEX_NAME.match(name_to_save):
            st.error("INVALID NAME: use only a-z, 0-9, _, - (max 64 chars)")
            st.stop()
        if not editing and len(aliases) >= MAX_ALIASES:
            st.error(f"MAX ALIASES REACHED ({MAX_ALIASES})")
            st.stop()
        aliases[name_to_save] = {
            "template": template,
            "variables": [v.strip() for v in variables_str.split(",") if v.strip()],
        }
        save_aliases(aliases)
        st.success(f"PERSISTED '/{name_to_save}'")
        st.session_state.edit_alias = None
        st.rerun()
