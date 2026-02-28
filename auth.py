"""Shared authentication module for the Streamlit panel."""

import datetime
import hmac
import secrets
import time

import extra_streamlit_components as stx
import streamlit as st
from config import Settings
from ui_utils import render_ui_header, render_sidebar_info

MAX_ATTEMPTS = 10
LOCKOUT_SECONDS = 900  # 15 minutes
COOKIE_NAME = "tv_bot_session"
SESSION_TTL_DAYS = 1


def get_manager():
    """Returns cookie manager instance."""
    return stx.CookieManager(key="tv_bot_cookie_manager")


@st.cache_resource
def get_global_lock():
    """Global failed login counter (shared between sessions)."""
    return {"fail_count": 0, "block_until": 0.0}


@st.cache_resource
def get_active_sessions():
    """Server-side storage of active session tokens."""
    return {}  # {token_hex: expiry_timestamp}


def _generate_session_token() -> str:
    """Generates a random session token (instead of SHA-256 password hash)."""
    return secrets.token_hex(32)


def _save_session(token: str) -> None:
    """Saves session token server-side with expiration date."""
    sessions = get_active_sessions()
    expiry = datetime.datetime.now() + datetime.timedelta(days=SESSION_TTL_DAYS)
    sessions[token] = expiry.timestamp()
    # Clean up expired sessions
    now = datetime.datetime.now().timestamp()
    expired = [t for t, exp in sessions.items() if exp < now]
    for t in expired:
        del sessions[t]


def _validate_session(token: str) -> bool:
    """Checks if session token is active and not expired."""
    sessions = get_active_sessions()
    if token not in sessions:
        return False
    now = datetime.datetime.now().timestamp()
    if sessions[token] < now:
        del sessions[token]
        return False
    return True


def _invalidate_session(token: str) -> None:
    """Removes session token (logout)."""
    sessions = get_active_sessions()
    sessions.pop(token, None)


def check_login():
    """Enforces password login with cookie handling and brute-force protection."""

    # Global UI and CSS (shared across all pages)
    logout_col = render_ui_header()
    render_sidebar_info()

    cookie_manager = get_manager()
    global_lock = get_global_lock()
    settings = Settings()

    # Check if just logged out (force logout flag)
    if st.session_state.get("force_logout", False):
        # Invalidate session server-side
        cookies = cookie_manager.get_all()
        old_token = cookies.get(COOKIE_NAME)
        if old_token:
            _invalidate_session(str(old_token))
        cookie_manager.delete(COOKIE_NAME)
        st.session_state["auth_success"] = False
        st.session_state["force_logout"] = False
        st.rerun()

    # Check cookie
    cookies = cookie_manager.get_all()
    token = cookies.get(COOKIE_NAME)

    is_logged_in = False

    # Priority 1: Temporary session (right after entering password)
    if st.session_state.get("auth_success", False):
        is_logged_in = True
    # Priority 2: Cookie with server-side validation
    elif token and _validate_session(str(token)):
        is_logged_in = True

    if is_logged_in:
        # Logout button inside the header column
        with logout_col:
            if st.button("Logout", key="logout_btn"):
                st.session_state["force_logout"] = True
                st.session_state["auth_success"] = False
                cookie_manager.delete(COOKIE_NAME)
                st.rerun()
        return

    # --- Login screen ---
    st.title("Login")

    # Check global lockout
    now = time.time()
    if global_lock["block_until"] > now:
        wait_s = int(global_lock["block_until"] - now)
        st.error(f"Too many failed attempts. System locked for {wait_s}s.")
        st.stop()

    with st.form("login_form"):
        password = st.text_input("Access Password", type="password")
        submit = st.form_submit_button("Log In")

    if submit:
        if hmac.compare_digest(password, settings.dashboard_password):
            # Success — reset counter
            global_lock["fail_count"] = 0
            # Set session flag (immediate access)
            st.session_state["auth_success"] = True
            # Generate random token and save server-side
            new_token = _generate_session_token()
            _save_session(new_token)
            expires = datetime.datetime.now() + datetime.timedelta(days=SESSION_TTL_DAYS)
            cookie_manager.set(COOKIE_NAME, new_token, expires_at=expires)
            st.success("Logging in...")
            st.rerun()
        else:
            # Failure — increment counter
            global_lock["fail_count"] += 1
            if global_lock["fail_count"] >= MAX_ATTEMPTS:
                global_lock["block_until"] = time.time() + LOCKOUT_SECONDS
                global_lock["fail_count"] = 0
                st.error(f"System locked for {LOCKOUT_SECONDS // 60} minutes!")
            else:
                remaining = MAX_ATTEMPTS - global_lock["fail_count"]
                st.error(f"Incorrect password. Attempts remaining: {remaining}")

    st.stop()
