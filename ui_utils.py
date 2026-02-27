import streamlit as st
import os
import requests
from config import Ustawienia

def check_system_status():
    """Sprawdza statusy polaczen dla naglowka."""
    ust = Ustawienia()
    status = {
        "tg": bool(ust.tg_token and ust.kanal),
        "dc": bool(ust.discord_webhook),
        "sl": bool(ust.slack_webhook),
        "srv": False
    }
    
    # Check Webhook Server (FastAPI)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:80")
    try:
        resp = requests.get(f"{WEBHOOK_URL}/health", timeout=1)
        if resp.status_code == 200:
            status["srv"] = True
    except Exception:
        pass
        
    return status

def render_ui_header():
    """Renderuje wspolny naglowek i wstrzykuje globalny CSS Matrix Style."""
    
    # Globalny CSS Matrix/Minimalist
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

        /* Logout button in top right */
        .logout-container {
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 999999;
        }
        
        h1, h2, h3, .stMetric label { color: #00FF41 !important; text-transform: uppercase; letter-spacing: 1px; }

        .stButton > button {
            background-color: #161B22 !important;
            color: #00FF41 !important;
            border: 1px solid #00FF41 !important;
            border-radius: 2px !important;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #00FF41 !important;
            color: #0D1117 !important;
            box-shadow: 0 0 10px #00FF41;
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

    # Naglowek Logo + Tytul
    c1, c2 = st.columns([0.15, 1])
    with c1:
        if os.path.exists("viking_logo.jpg"):
            st.image("viking_logo.jpg", width=80)
    with c2:
        st.markdown(f"""
            <div style="padding-top: 5px;">
                <h1 style="margin: 0; font-size: 28px;">⚠️ TradingView Alerts to Discord, Telegram or Slack</h1>
            </div>
        """, unsafe_allow_html=True)
        
        # Status dots like tgramai
        stats = check_system_status()
        s_tg = "🟢" if stats["tg"] else "🔴"
        s_dc = "🟢" if stats["dc"] else "🔴"
        s_sl = "🟢" if stats["sl"] else "🔴"
        s_srv = "🟢" if stats["srv"] else "🔴"

        t_tg = "Telegram: Connected" if stats["tg"] else "Telegram: Missing Token/Channel"
        t_dc = "Discord: Ready" if stats["dc"] else "Discord: Missing Webhook"
        t_sl = "Slack: Ready" if stats["sl"] else "Slack: Missing Webhook"
        t_srv = "Server: Online" if stats["srv"] else "Server: Offline/Connection Error"

        st.markdown(f"""
            <div style="font-size: 13px; opacity: 0.9; margin-top: 5px; margin-bottom: 10px;">
                <span title="{t_tg}" class="status-dot">{s_tg} Telegram</span> |
                <span title="{t_dc}" class="status-dot">{s_dc} Discord</span> |
                <span title="{t_sl}" class="status-dot">{s_sl} Slack</span> |
                <span title="{t_srv}" class="status-dot">{s_srv} Webhook Server</span>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

def render_sidebar_info():
    """Wyswietla dodatkowe info w sidebarze."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("""
            <div style="font-size: 10px; color: #484F58;">
                SYSTEM: POPEK-LAB-CORE<br>
                KERNEL: 3.12-DOCKER<br>
                UPTIME: ACTIVE
            </div>
        """, unsafe_allow_html=True)
