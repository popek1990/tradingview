import streamlit as st
import os

def render_ui_header():
    """Renderuje wspolny naglowek i wstrzykuje globalny CSS Matrix Style."""
    
    # Globalny CSS Matrix/Minimalist
    st.markdown("""
        <style>
        /* Styl terminala dla calej aplikacji */
        .stApp {
            background-color: #0D1117;
            color: #C9D1D9;
        }
        
        /* Monospace font everywhere */
        html, body, [class*="css"] {
            font-family: 'Courier New', Courier, monospace !important;
        }

        /* Styl naglowka - Vikings Logo + Title */
        .main-header {
            display: flex;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 2px solid #00FF41;
            margin-bottom: 2rem;
            background-color: #161B22;
            border-radius: 5px;
            padding: 10px;
        }
        
        /* Terminal green accent */
        h1, h2, h3, .stMetric label {
            color: #00FF41 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Custom buttons - minimalist & matrix */
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

        /* Inputs styling */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            background-color: #21262D !important;
            color: #C9D1D9 !important;
            border: 1px solid #30363D !important;
        }

        /* Metrics styling */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Log terminal look */
        .terminal-log {
            background-color: #000000 !important;
            color: #00FF41 !important;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            border: 1px solid #30363D;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #161B22 !important;
            border-right: 1px solid #30363D;
        }
        </style>
    """, unsafe_allow_html=True)

    # Naglowek Logo + Tytul
    c1, c2 = st.columns([0.15, 1])
    with c1:
        if os.path.exists("viking_logo.jpg"):
            st.image("viking_logo.jpg", width=80)
    with c2:
        st.markdown(f"""
            <div style="padding-top: 10px;">
                <h1 style="margin: 0; font-size: 24px;">📟 TV-WEBHOOK TERMINAL</h1>
                <p style="color: #8B949E; margin: 0; font-size: 14px;">Operative Interface v2.0 | popek1990.eth</p>
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
