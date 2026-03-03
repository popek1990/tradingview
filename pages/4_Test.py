"""Test Pipeline — Minimalist Terminal Style."""

import json

import requests
import streamlit as st
from auth import check_login
from config import Settings
from ui_utils import WEBHOOK_URL, safe_html

# Must be first Streamlit command
st.set_page_config(page_title="TradingView Alerts", page_icon="viking_logo.jpg", layout="wide")

check_login()

# Settings loaded after login check
settings = Settings()

st.subheader("WEBHOOK PIPELINE TEST")

with st.form("form_test", border=True):
    msg = st.text_area(
        "ALERT PAYLOAD (Plain Text or JSON Template)",
        value="\u2705 Webhook connection test - PASSED",
        max_chars=4000,
        height=150
    )

    st.markdown("#### OVERRIDE TARGETS (OPTIONAL)")
    c1, c2, c3 = st.columns(3)
    with c1: tg_override = st.text_input("TG ID")
    with c2: dc_override = st.text_input("DC ID")
    with c3: sl_override = st.text_input("SL ID")

    submit = st.form_submit_button("EXECUTE TEST ALERT", use_container_width=True)

if submit:
    if not settings.sec_key:
        st.error("MISSING SEC_KEY. Configure it first.")
        st.stop()

    # Determine payload (strip "key" from user JSON to prevent accidental override)
    try:
        potential_json = json.loads(msg.strip())
        if isinstance(potential_json, dict):
            potential_json.pop("key", None)
            payload = {"key": settings.sec_key, **potential_json}
        else: raise ValueError()
    except Exception:
        payload = {"key": settings.sec_key, "msg": msg}

    if tg_override.strip(): payload["telegram"] = tg_override.strip()
    if dc_override.strip(): payload["discord"] = dc_override.strip()
    if sl_override.strip(): payload["slack"] = sl_override.strip()

    st.markdown("#### EXECUTION LOG")
    try:
        resp = requests.post(f"{WEBHOOK_URL}/webhook", json=payload, timeout=30)
        if resp.status_code == 200:
            st.success("SUCCESS: ALERT DISPATCHED")
            safe_json = safe_html(json.dumps(resp.json(), indent=2))
            st.markdown(f'<div class="terminal-log">{safe_json}</div>', unsafe_allow_html=True)
        else:
            st.error(f"FAILURE: HTTP {resp.status_code}")
            safe_text = safe_html(resp.text)
            st.markdown(f'<div class="terminal-log" style="color: #F85149 !important;">{safe_text}</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PIPELINE CRITICAL ERROR: {e}")
