import html
import os

import requests
import streamlit as st
from dotenv import set_key

from config import Settings

# Shared constants — single source of truth for frontend
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
ENV_FILE_PATH = ".env"


@st.cache_data(ttl=30)
def check_system_status():
    """Checks connection statuses for header (cached 30s)."""
    settings = Settings()
    status = {
        "tg": bool(settings.tg_token and settings.channel),
        "dc": bool(settings.discord_webhook),
        "sl": bool(settings.slack_webhook),
        "key": bool(settings.sec_key),
        "srv": False
    }

    try:
        resp = requests.get(f"{WEBHOOK_URL}/health", timeout=1)
        if resp.status_code == 200:
            status["srv"] = True
    except Exception:
        pass

    return status


def save_and_reload(fields: dict) -> None:
    """Saves fields to .env and reloads webhook server config.

    Displays st.success/error/warning messages.
    """
    settings = Settings()
    old_sec_key = settings.sec_key

    write_errors = []
    for key, value in fields.items():
        success, _, _ = set_key(ENV_FILE_PATH, key, value)
        if not success:
            write_errors.append(key)

    if write_errors:
        st.error(f"WRITE FAILED: {', '.join(write_errors)}")
        st.stop()

    st.success("CONFIGURATION PERSISTED TO .ENV")
    st.toast("Persisted!")

    try:
        resp = requests.post(
            f"{WEBHOOK_URL}/reload-config",
            json={"key": old_sec_key},
            timeout=5,
        )
        if resp.status_code == 200:
            st.success("WEBHOOK SERVER: CONFIG RELOADED")
        else:
            st.warning(f"WEBHOOK SERVER: RELOAD FAILED (HTTP {resp.status_code})")
    except Exception:
        st.info("WEBHOOK SERVER: UNREACHABLE (Manual restart required)")


def safe_html(text: str) -> str:
    """Escapes HTML — protects against XSS in unsafe_allow_html."""
    return html.escape(text)

def render_ui_header():
    """Renders shared header and injects global CSS Matrix Style."""

    # Global CSS Matrix/Minimalist
    st.markdown("""
        <style>
        .stApp {
            background-color: #0D1117;
            color: #C9D1D9;
        }

        /* Medium width constraint */
        [data-testid="stMainViewContainer"] > div:first-child {
            max-width: 1200px;
            margin: 0 auto;
        }

        html, body, [class*="css"] { font-family: 'Courier New', Courier, monospace !important; }

        /* Logout button styling in header */
        div[data-testid="column"]:nth-child(3) {
            display: flex;
            justify-content: flex-end;
            align-items: flex-end;
            padding-bottom: 5px;
        }

        div[data-testid="column"]:nth-child(3) button {
            font-size: 11px !important;
            padding: 2px 10px !important;
            min-height: 25px !important;
            line-height: 1 !important;
        }

        h1, h2, h3, .stMetric label { color: #00FF41 !important; text-transform: uppercase; letter-spacing: 1px; }

        .stButton > button {
            background-color: #161B22 !important;
            color: #00FF41 !important;
            border: 1px solid #00FF41 !important;
            border-radius: 2px !important;
            transition: all 0.3s ease;
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background-color: #00FF41 !important;
            color: #0D1117 !important;
            box-shadow: 0 0 10px #00FF41;
        }

        .stFormSubmitButton > button {
            background-color: #161B22 !important;
            color: #00FF41 !important;
            border: 1px solid #00FF41 !important;
            border-radius: 2px !important;
            transition: all 0.3s ease;
        }

        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            background-color: #21262D !important;
            color: #C9D1D9 !important;
            border: 1px solid #30363D !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        .terminal-log {
            background-color: #000000 !important;
            color: #00FF41 !important;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            border: 1px solid #30363D;
        }

        [data-testid="stSidebar"] { background-color: #161B22 !important; border-right: 1px solid #30363D; }

        /* Tooltip style */
        .status-dot { cursor: help; border-bottom: 1px dotted rgba(255,255,255,0.2); padding: 2px; }
        </style>
    """, unsafe_allow_html=True)

    # Header: Logo + Title + Logout
    c1, c2, c3 = st.columns([0.1, 1, 0.15])
    with c1:
        logo_path = os.path.join(os.path.dirname(__file__), "viking_logo.jpg")
        if os.path.exists(logo_path):
            st.image(logo_path, width=80)
        else:
            pass
    with c2:
        st.markdown(f"""
            <div style="padding-top: 5px;">
                <h1 style="margin: 0; font-size: 28px;">TradingView Alerts to Discord, Telegram or Slack</h1>
            </div>
        """, unsafe_allow_html=True)

        # Status dots
        stats = check_system_status()
        s_tg = "🟢" if stats["tg"] else "🔴"
        s_dc = "🟢" if stats["dc"] else "🔴"
        s_sl = "🟢" if stats["sl"] else "🔴"
        s_key = "🟢" if stats["key"] else "🔴"
        s_srv = "🟢" if stats["srv"] else "🔴"

        t_tg = "Telegram: Connected" if stats["tg"] else "Telegram: Missing Token/Channel"
        t_dc = "Discord: Ready" if stats["dc"] else "Discord: Missing Webhook"
        t_sl = "Slack: Ready" if stats["sl"] else "Slack: Missing Webhook"
        t_key = "Auth Key: Configured" if stats["key"] else "Auth Key: MISSING SEC_KEY"
        t_srv = "Server: Online" if stats["srv"] else "Server: Offline/Connection Error"

        st.markdown(f"""
            <div style="font-size: 13px; opacity: 0.9; margin-top: 5px; margin-bottom: 10px;">
                <span title="{safe_html(t_srv)}" class="status-dot">{s_srv} Webhook Server</span> |
                <span title="{safe_html(t_key)}" class="status-dot">{s_key} Auth Key</span> |
                <span title="{safe_html(t_tg)}" class="status-dot">{s_tg} Telegram</span> |
                <span title="{safe_html(t_dc)}" class="status-dot">{s_dc} Discord</span> |
                <span title="{safe_html(t_sl)}" class="status-dot">{s_sl} Slack</span>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    return c3  # Return column for logout button

def render_sidebar_info():
    """Displays additional info in sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.code("SYSTEM:  POPEK-LAB-CORE\nKERNEL:  3.12-DOCKER\nUPTIME:  ACTIVE", language=None)
        st.markdown(
            '<a href="https://github.com/popek1990/Tradingview" target="_blank" '
            'style="font-size: 10px; color: #484F58;">GitHub Repository</a>',
            unsafe_allow_html=True,
        )
