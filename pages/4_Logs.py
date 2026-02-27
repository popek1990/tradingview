"""System Logs — Minimalist Terminal Style."""

import os
from collections import deque

import streamlit as st
from auth import check_login
from ui_utils import safe_html

# Must be first Streamlit command
st.set_page_config(page_title="TV-BOT | LOGS", page_icon="📋", layout="wide")

check_login()

LOG_FILE_PATH = "logs/webhook.log"
st.subheader("SYSTEM OPERATIONAL LOGS")

# Filters
with st.container(border=True):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        level = st.selectbox("LEVEL FILTER", ["ALL", "ERROR", "WARNING", "INFO", "DEBUG"])
    with col2:
        search = st.text_input("SEARCH PATTERN")
    with col3:
        num_lines = st.number_input("LINES TO TAIL", min_value=10, max_value=5000, value=200, step=50)

if st.button("REFRESH LOG STREAM", use_container_width=True):
    st.rerun()

st.markdown("---")

if not os.path.exists(LOG_FILE_PATH):
    st.warning("LOG FILE NOT FOUND. Server may not have initialized yet.")
else:
    try:
        with open(LOG_FILE_PATH, encoding="utf-8") as f:
            # Efficient reading of last N lines (instead of readlines())
            lines = list(deque(f, maxlen=num_lines))

        # Filter by level
        if level != "ALL":
            lines = [l for l in lines if f"[{level}]" in l]

        # Filter by text
        if search:
            search_lower = search.lower()
            lines = [l for l in lines if search_lower in l.lower()]

        if lines:
            st.caption(f"STREAMING {len(lines)} LINES...")
            # html.escape() — XSS protection
            log_text = safe_html("".join(lines))
            st.markdown(f'<div class="terminal-log" style="height: 500px; overflow-y: scroll; white-space: pre-wrap; font-size: 12px;">{log_text}</div>', unsafe_allow_html=True)
        else:
            st.info("NO LOGS MATCHING CRITERIA")
    except Exception as e:
        st.error(f"IO ERROR: {e}")
