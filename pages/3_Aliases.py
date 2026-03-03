"""Webhook Aliases — Quick shortcuts for TradingView alerts."""

import html
import os
import re

import requests
import streamlit as st
import streamlit.components.v1 as components
from auth import check_login
from aliases import get_lock as get_aliases_lock, load_aliases, load_aliases_unlocked, save_aliases, validate_variable_names

def _check_template_vars(template: str, variables: list[str]) -> str | None:
    """Returns warning message if template placeholders don't match declared variables."""
    import re
    placeholders = set(re.findall(r"\{(\w+)\}", template))
    declared = set(variables)
    unused = declared - placeholders
    undeclared = placeholders - declared
    warnings = []
    if unused:
        warnings.append(f"Declared but unused in template: {', '.join(sorted(unused))}")
    if undeclared:
        warnings.append(f"Used in template but not declared: {', '.join(sorted(undeclared))}")
    return "; ".join(warnings) if warnings else None
from config import Settings
from ui_utils import WEBHOOK_URL

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="viking_logo.jpg", layout="wide")

check_login()

# Page-specific CSS for compact buttons
st.markdown("""
<style>
    .small-btn button {
        font-size: 10px !important;
        padding: 2px 6px !important;
        min-height: 24px !important;
        height: 24px !important;
        line-height: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

REGEX_NAME = re.compile(r"^[a-z0-9_-]{1,64}$")
MAX_ALIASES = 50

st.subheader("WEBHOOK ALIASES")

with st.expander("What are aliases?", expanded=False):
    st.caption("Type short aliases in TradingView Message field instead of complex JSON")
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"]:has(.alias-example) {
        align-items: center !important;
    }
    </style>
    """, unsafe_allow_html=True)
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        example_img = os.path.join(os.path.dirname(__file__), "..", "alias_example.png")
        if os.path.exists(example_img):
            st.markdown('<div class="alias-example"></div>', unsafe_allow_html=True)
            st.image(example_img, caption="TradingView alert message")
    with col_img2:
        output_img = os.path.join(os.path.dirname(__file__), "..", "alias_output_example.png")
        if os.path.exists(output_img):
            st.image(output_img, caption="Telegram output")

aliases = load_aliases()

# Edit and delete state
if "edit_alias" not in st.session_state:
    st.session_state.edit_alias = None
if "confirm_delete_alias" not in st.session_state:
    st.session_state.confirm_delete_alias = None
if "just_saved_alias" not in st.session_state:
    st.session_state.just_saved_alias = None

# --- Editor at the top when editing ---
editing = st.session_state.edit_alias
if editing and editing in aliases:
    st.markdown(
        f'<h3><span style="color: #00FF41;">EDITING:</span> /{html.escape(editing.upper())}</h3>',
        unsafe_allow_html=True,
    )
    if st.button("CANCEL"):
        st.session_state.edit_alias = None
        st.rerun()

    with st.form("form_edit_alias", border=True):
        new_name = st.text_input("ALIAS NAME (a-z, 0-9, _, -)", value=editing, max_chars=64)
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
            name_to_save = new_name.strip().lower().replace(" ", "_")
            if not name_to_save:
                st.error("ALIAS NAME REQUIRED")
                st.stop()
            if not REGEX_NAME.match(name_to_save):
                st.error("INVALID NAME: use only a-z, 0-9, _, - (max 64 chars)")
                st.stop()
            parsed_vars = [v.strip() for v in variables_str.split(",") if v.strip()]
            try:
                validate_variable_names(parsed_vars)
            except ValueError as e:
                st.error(str(e))
                st.stop()
            var_warning = _check_template_vars(template, parsed_vars)
            if var_warning:
                st.warning(f"Variable mismatch: {var_warning}")
            with get_aliases_lock():
                aliases = load_aliases_unlocked()
                if name_to_save != editing:
                    if name_to_save in aliases:
                        st.error(f"ALIAS '/{name_to_save}' ALREADY EXISTS")
                        st.stop()
                    aliases.pop(editing, None)
                aliases[name_to_save] = {
                    "template": template,
                    "variables": parsed_vars,
                }
                save_aliases(aliases)
            st.success(f"SAVED '/{name_to_save}'")
            st.session_state.edit_alias = None
            st.session_state.just_saved_alias = name_to_save
            st.rerun()

    st.markdown("---")

# --- New Alias (only when not editing) ---
if not editing:
    st.markdown("### ADD NEW ALIAS")
    with st.expander("Add", expanded=False):
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
            parsed_vars = [v.strip() for v in new_variables.split(",") if v.strip()]
            try:
                validate_variable_names(parsed_vars)
            except ValueError as e:
                st.error(str(e))
                st.stop()
            var_warning = _check_template_vars(new_template, parsed_vars)
            if var_warning:
                st.warning(f"Variable mismatch: {var_warning}")
            with get_aliases_lock():
                aliases = load_aliases_unlocked()
                aliases[name_to_save] = {
                    "template": new_template,
                    "variables": parsed_vars,
                }
                save_aliases(aliases)
            st.success(f"CREATED '/{name_to_save}'")
            st.rerun()

# --- List of Aliases ---
if aliases:
    st.markdown("### ACTIVE ALIASES")
    for name, data in aliases.items():
        just_saved = st.session_state.just_saved_alias == name
        if just_saved:
            st.session_state.just_saved_alias = None
        with st.expander(f"/`{name.upper()}`", expanded=just_saved):
            col_preview, col_controls = st.columns([5, 1])
            with col_preview:
                variables = data.get("variables", [])
                st.markdown("**VARIABLES:** " + (", ".join(f"`{v}`" for v in variables) if variables else "_none_"))

                preview = data["template"]
                for v in variables:
                    preview = preview.replace(f"{{{v}}}", f"[{v}]")
                st.code(preview, language=None)

            with col_controls:
                st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                st.write("")  # vertical spacer
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
                            st.success("SENT")
                        else:
                            st.error(f"HTTP {resp.status_code}")
                    except Exception as e:
                        st.error(f"{e}")
                if st.session_state.confirm_delete_alias == name:
                    st.warning("Sure?")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("YES", key=f"ayes_{name}", use_container_width=True):
                            with get_aliases_lock():
                                aliases = load_aliases_unlocked()
                                aliases.pop(name, None)
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
                st.markdown('</div>', unsafe_allow_html=True)

            # TradingView shortcut with always-visible copy button
            variables = data.get("variables", [])
            safe_name = html.escape(name)
            tv_shortcut = f"/{safe_name}"
            if variables:
                tv_shortcut += " " + " ".join(f"{{{{{html.escape(v)}}}}}" for v in variables)
            components.html(f"""
            <div style="display:flex;align-items:center;gap:10px;background:#000;
                        padding:8px 12px;border-radius:5px;border:1px solid #30363D;
                        font-family:'Courier New',monospace;">
                <span style="color:#8b949e;font-size:12px;white-space:nowrap;">TradingView Message:</span>
                <code id="tv_{safe_name}" style="color:#00FF41;font-size:13px;flex:1;background:none;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{tv_shortcut}</code>
                <button id="btn_{safe_name}" onclick="
                    navigator.clipboard.writeText(document.getElementById('tv_{safe_name}').innerText).then(()=>{{
                        document.getElementById('btn_{safe_name}').innerText='Copied!';
                        setTimeout(()=>document.getElementById('btn_{safe_name}').innerText='Copy',1500);
                    }})
                " style="background:#161B22;color:#00FF41;border:1px solid #30363D;border-radius:3px;
                         padding:3px 12px;cursor:pointer;font-family:'Courier New',monospace;
                         font-size:11px;white-space:nowrap;transition:all .2s;"
                   onmouseover="this.style.background='#00FF41';this.style.color='#0D1117'"
                   onmouseout="this.style.background='#161B22';this.style.color='#00FF41'">Copy</button>
            </div>
            """, height=42)
else:
    st.info("NO ALIASES DEFINED")
