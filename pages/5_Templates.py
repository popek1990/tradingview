"""Message Templates — Minimalist Terminal Style."""

import re
import streamlit as st
from auth import check_login
from templates import load_templates, save_templates
from ui_utils import safe_html

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="📝", layout="wide")

check_login()

REGEX_NAME = re.compile(r"^[a-z0-9_-]{1,64}$")
MAX_TEMPLATES = 50

st.subheader("PAYLOAD TEMPLATES")
templates = load_templates()

# Edit and delete state
if "edit_template" not in st.session_state:
    st.session_state.edit_template = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

# --- List of Templates ---
if templates:
    st.markdown("### ACTIVE TEMPLATES")
    for name, data in templates.items():
        with st.expander(f"[{name.upper()}]", expanded=False):
            col_preview, col_controls = st.columns([3, 1])
            with col_preview:
                st.markdown("**VARIABLES:** " + ", ".join(f"`{v}`" for v in data.get("variables", [])))
                preview = data["content"]
                for v in data.get("variables", []): preview = preview.replace(f"{{{v}}}", f"[{v}]")
                st.code(preview, language=None)
            with col_controls:
                if st.button("EDIT", key=f"edit_{name}", use_container_width=True):
                    st.session_state.edit_template = name; st.rerun()
                # Two-step delete confirmation
                if st.session_state.confirm_delete == name:
                    st.warning("Are you sure?")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("YES", key=f"yes_{name}", use_container_width=True):
                            del templates[name]; save_templates(templates)
                            st.session_state.confirm_delete = None; st.rerun()
                    with c_no:
                        if st.button("NO", key=f"no_{name}", use_container_width=True):
                            st.session_state.confirm_delete = None; st.rerun()
                else:
                    if st.button("DELETE", key=f"del_{name}", use_container_width=True):
                        st.session_state.confirm_delete = name; st.rerun()

            # TradingView JSON
            variables_json = ", ".join('"' + v + '": "{{' + v + '}}"' for v in data.get("variables", []))
            tv_json = '{"template": "' + name + '"'
            if variables_json: tv_json += ", " + variables_json
            tv_json += "}"
            safe_tv_json = safe_html(tv_json)
            st.markdown(f'<div class="terminal-log" style="font-size: 10px; padding: 10px;">TV MSG: {safe_tv_json}</div>', unsafe_allow_html=True)
else:
    st.info("NO TEMPLATES DEFINED")

st.markdown("---")

# --- Editor ---
editing = st.session_state.edit_template
if editing and editing in templates:
    st.markdown(f"### EDITOR: {editing.upper()}")
    default_name, default_content, default_variables = editing, templates[editing]["content"], ", ".join(templates[editing].get("variables", []))
    if st.button("CANCEL"): st.session_state.edit_template = None; st.rerun()
else:
    st.markdown("### NEW TEMPLATE")
    default_name, default_content, default_variables = "", "", ""

with st.form("form_template", border=True):
    name = st.text_input("ID (a-z, 0-9, _, -)", value=default_name, max_chars=64, disabled=bool(editing))
    content = st.text_area("CONTENT", value=default_content, height=150, max_chars=4000)
    variables_str = st.text_input("VARIABLES (comma-separated)", value=default_variables)
    if st.form_submit_button("SUBMIT", use_container_width=True):
        name_to_save = (editing or name).strip().lower().replace(" ", "_")
        if not name_to_save or not content.strip():
            st.error("FIELDS REQUIRED"); st.stop()
        if not REGEX_NAME.match(name_to_save):
            st.error("INVALID NAME: use only a-z, 0-9, _, - (max 64 chars)"); st.stop()
        if not editing and len(templates) >= MAX_TEMPLATES:
            st.error(f"MAX TEMPLATES REACHED ({MAX_TEMPLATES})"); st.stop()
        templates[name_to_save] = {"content": content, "variables": [v.strip() for v in variables_str.split(",") if v.strip()]}
        save_templates(templates); st.success(f"PERSISTED '{name_to_save}'"); st.session_state.edit_template = None; st.rerun()
