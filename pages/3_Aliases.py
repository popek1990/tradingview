"""Webhook Aliases — Quick shortcuts for TradingView alerts."""

import html
import os
import re

import requests
import streamlit as st
import streamlit.components.v1 as components
from auth import check_login
from aliases import get_lock as get_aliases_lock, load_aliases, find_bracketed_vars, load_aliases_unlocked, save_aliases, validate_variable_names

def _check_template_vars(template: str, variables: list[str]) -> str | None:
    """Returns warning message if template placeholders don't match declared variables."""
    import re
    placeholders = set(re.findall(r"\{(\w+)\}", template))
    declared = set(variables)
    # {interval_raw} is auto-generated when "interval" is declared — not a real variable
    if "interval" in declared:
        placeholders.discard("interval_raw")
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

# Common TradingView placeholders for quick-add
TV_PLACEHOLDERS = ["ticker", "exchange", "close", "open", "high", "low", "volume", "interval", "interval_raw", "time"]

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

# --- Backup: export / import (the data volume is the only copy of aliases) ---
with st.expander("BACKUP: EXPORT / IMPORT", expanded=False):
    import json as _json
    from datetime import datetime as _dt
    st.download_button(
        "EXPORT ALIASES (JSON)",
        data=_json.dumps(aliases, ensure_ascii=False, indent=2),
        file_name=f"aliases-{_dt.now():%Y-%m-%d}.json",
        mime="application/json",
        use_container_width=True,
    )
    uploaded = st.file_uploader("IMPORT FROM FILE (replaces all aliases)", type="json")
    confirm_import = st.checkbox("I understand the current aliases will be replaced")
    if uploaded is not None and st.button("IMPORT", disabled=not confirm_import,
                                          use_container_width=True):
        try:
            imported = _json.loads(uploaded.getvalue().decode("utf-8"))
            if not isinstance(imported, dict) or len(imported) > MAX_ALIASES:
                raise ValueError(f"expected an object with at most {MAX_ALIASES} aliases")
            for alias_name, alias_def in imported.items():
                if not REGEX_NAME.match(alias_name):
                    raise ValueError(f"invalid alias name '{alias_name}'")
                if (not isinstance(alias_def, dict)
                        or not isinstance(alias_def.get("template"), str)
                        or not isinstance(alias_def.get("variables", []), list)):
                    raise ValueError(f"/{alias_name}: needs 'template' (text) and 'variables' (list)")
                validate_variable_names(alias_def.get("variables", []))
                bracketed = find_bracketed_vars(alias_def["template"], alias_def.get("variables", []))
                if bracketed:
                    raise ValueError(f"/{alias_name}: uses [{bracketed[0]}] instead of {{{bracketed[0]}}}")
        except (ValueError, UnicodeDecodeError) as e:
            st.error(f"IMPORT REJECTED: {e}")
            st.stop()
        with get_aliases_lock():
            save_aliases(imported)
        st.success(f"IMPORTED {len(imported)} ALIASES")
        st.rerun()

# Edit and delete state
if "edit_alias" not in st.session_state:
    st.session_state.edit_alias = None
if "confirm_delete_alias" not in st.session_state:
    st.session_state.confirm_delete_alias = None
if "just_saved_alias" not in st.session_state:
    st.session_state.just_saved_alias = None

# Warning from the last save — survives the st.rerun() that follows saving
_var_warning = st.session_state.pop("alias_var_warning", None)
if _var_warning:
    st.warning(f"SAVED, BUT VARIABLE MISMATCH — {_var_warning}")

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
                                height=180, max_chars=4000,
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
            bracketed = find_bracketed_vars(template, parsed_vars)
            if bracketed:
                st.error("USE {VAR}, NOT [VAR]: " + ", ".join(f"[{v}] → {{{v}}}" for v in bracketed))
                st.stop()
            var_warning = _check_template_vars(template, parsed_vars)
            if var_warning:
                # Shown after st.rerun() below — a plain st.warning would be wiped
                st.session_state.alias_var_warning = f"/{name_to_save}: {var_warning}"
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

    # Quick-add variable buttons (outside form — forms can't dynamically update)
    if "new_alias_vars" not in st.session_state:
        st.session_state.new_alias_vars = ""

    with st.expander("Add", expanded=bool(st.session_state.new_alias_vars)):
      with st.form("form_new_alias", border=True):
        new_name = st.text_input("ALIAS NAME (a-z, 0-9, _, -)", max_chars=64)
        new_template = st.text_area("TEMPLATE CONTENT", height=180, max_chars=4000,
                                    help="Use {variable} for placeholders, e.g. {ticker}")
        new_variables = st.text_input("VARIABLES (comma-separated)",
                                      value=st.session_state.new_alias_vars,
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
            bracketed = find_bracketed_vars(new_template, parsed_vars)
            if bracketed:
                st.error("USE {VAR}, NOT [VAR]: " + ", ".join(f"[{v}] → {{{v}}}" for v in bracketed))
                st.stop()
            var_warning = _check_template_vars(new_template, parsed_vars)
            if var_warning:
                # Shown after st.rerun() below — a plain st.warning would be wiped
                st.session_state.alias_var_warning = f"/{name_to_save}: {var_warning}"
            with get_aliases_lock():
                aliases = load_aliases_unlocked()
                aliases[name_to_save] = {
                    "template": new_template,
                    "variables": parsed_vars,
                }
                save_aliases(aliases)
            st.success(f"CREATED '/{name_to_save}'")
            st.session_state.new_alias_vars = ""
            st.rerun()

      st.caption("Quick-add TradingView variables:")
      pill_cols = st.columns(len(TV_PLACEHOLDERS))
      for i, var in enumerate(TV_PLACEHOLDERS):
          with pill_cols[i]:
              st.markdown('<div class="small-btn">', unsafe_allow_html=True)
              if st.button(f"{{{{{var}}}}}", key=f"qv_{var}", use_container_width=True):
                  current = st.session_state.new_alias_vars
                  existing = [v.strip() for v in current.split(",") if v.strip()]
                  # interval_raw is auto-generated — add "interval" to variables instead
                  var_to_add = "interval" if var == "interval_raw" else var
                  if var_to_add not in existing:
                      existing.append(var_to_add)
                      st.session_state.new_alias_vars = ", ".join(existing)
                      st.rerun()
              st.markdown('</div>', unsafe_allow_html=True)

# --- List of Aliases ---
if aliases:
    st.markdown("### ACTIVE ALIASES")
    for name, data in aliases.items():
        just_saved = st.session_state.just_saved_alias == name
        if just_saved:
            st.session_state.just_saved_alias = None
        keep_open = (just_saved or st.session_state.confirm_delete_alias == name
                     or st.session_state.get("reveal_json_alias") == name)
        with st.expander(f"/`{name.upper()}`", expanded=keep_open):
            col_preview, col_controls = st.columns([5, 1])
            with col_preview:
                variables = data.get("variables", [])
                st.markdown("**VARIABLES:** " + (", ".join(f"`{v}`" for v in variables) if variables else "_none_"))

                # Show the raw template — it gets copied back into templates,
                # so placeholders must stay as {var} (a "[var]" preview once
                # ended up verbatim in /strong's chart link)
                st.code(data["template"], language=None)

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

            # TradingView ready-to-paste JSON with SEC_KEY and alias.
            # SEC_KEY reaches the browser only for the alias the user asked for.
            if st.session_state.get("reveal_json_alias") != name:
                if st.button("SHOW TRADINGVIEW JSON (contains SEC_KEY)", key=f"ajson_{name}"):
                    st.session_state.reveal_json_alias = name
                    st.rerun()
                continue
            import json as _json
            variables = data.get("variables", [])
            safe_name = html.escape(name)
            settings = Settings()
            alias_cmd = f"/{name}"
            if variables:
                alias_cmd += " " + " ".join(f"{{{{{v}}}}}" for v in variables)
            tv_json_raw = _json.dumps({"key": settings.sec_key, "msg": alias_cmd})
            # Escape for safe embedding in JS string literal
            tv_json_js = tv_json_raw.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            alias_cmd_display = html.escape(alias_cmd)
            components.html(f"""
            <div style="display:flex;align-items:center;gap:10px;background:#000;
                        padding:8px 12px;border-radius:5px;border:1px solid #30363D;
                        font-family:'Courier New',monospace;">
                <span style="color:#8b949e;font-size:12px;white-space:nowrap;">TradingView Message:</span>
                <code style="color:#00FF41;font-size:13px;flex:1;background:none;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{alias_cmd_display}</code>
                <button id="btn_{safe_name}" style="background:#161B22;color:#00FF41;border:1px solid #30363D;border-radius:3px;
                         padding:3px 12px;cursor:pointer;font-family:'Courier New',monospace;
                         font-size:11px;white-space:nowrap;transition:all .2s;"
                   onmouseover="this.style.background='#00FF41';this.style.color='#0D1117'"
                   onmouseout="this.style.background='#161B22';this.style.color='#00FF41'">Copy JSON</button>
            </div>
            <script>
                document.getElementById('btn_{safe_name}').addEventListener('click', function() {{
                    var btn = this;
                    navigator.clipboard.writeText(`{tv_json_js}`).then(function() {{
                        btn.innerText = 'Copied!';
                        setTimeout(function() {{ btn.innerText = 'Copy JSON'; }}, 1500);
                    }});
                }});
            </script>
            """, height=42)
else:
    st.info("NO ALIASES DEFINED")
