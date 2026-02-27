"""Test Pipeline — Minimalist Terminal Style."""

import os
import streamlit as st
import requests
import json
from auth import sprawdz_logowanie
from config import Ustawienia

# Must be first Streamlit command
st.set_page_config(page_title="TV-BOT | TEST", page_icon="🧪", layout="wide")

sprawdz_logowanie()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
ust = Ustawienia()

st.subheader("🧪 WEBHOOK PIPELINE TEST")

with st.form("form_test", border=True):
    msg = st.text_area(
        "ALERT PAYLOAD (Plain Text or JSON Template)",
        value='{"szablon": "target_long_term", "ticker": "BTCUSDT", "exchange": "BINANCE", "close": "69000"}',
        max_chars=4000,
        height=150
    )

    st.markdown("#### OVERRIDE TARGETS (OPTIONAL)")
    c1, c2, c3 = st.columns(3)
    with c1: tg_override = st.text_input("TG ID")
    with c2: dc_override = st.text_input("DC ID")
    with c3: sl_override = st.text_input("SL ID")

    wyslij = st.form_submit_button("EXECUTE TEST ALERT", use_container_width=True)

if wyslij:
    if not ust.sec_key:
        st.error("MISSING SEC_KEY. Configure it first.")
        st.stop()

    # Determine payload
    try:
        potential_json = json.loads(msg.strip())
        if isinstance(potential_json, dict):
            payload = {"key": ust.sec_key, **potential_json}
        else: raise ValueError()
    except Exception:
        payload = {"key": ust.sec_key, "msg": msg}

    if tg_override.strip(): payload["telegram"] = tg_override.strip()
    if dc_override.strip(): payload["discord"] = dc_override.strip()
    if sl_override.strip(): payload["slack"] = sl_override.strip()

    st.markdown("#### EXECUTION LOG")
    try:
        resp = requests.post(f"{WEBHOOK_URL}/webhook", json=payload, timeout=30)
        if resp.status_code == 200:
            st.success("SUCCESS: ALERT DISPATCHED")
            st.markdown(f'<div class="terminal-log">{json.dumps(resp.json(), indent=2)}</div>', unsafe_allow_html=True)
        else:
            st.error(f"FAILURE: HTTP {resp.status_code}")
            st.markdown(f'<div class="terminal-log" style="color: #F85149 !important;">{resp.text}</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PIPELINE CRITICAL ERROR: {e}")
