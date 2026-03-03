"""Shared authentication module for the Streamlit panel.

Uses HMAC-signed session tokens that are self-validating — no server-side
session storage needed.  Token is persisted in both st.session_state (survives
page navigation) and st.query_params (survives browser F5 refresh).
"""

import hashlib
import hmac
import threading
import time

import streamlit as st
from config import Settings
from ui_utils import render_ui_header, render_sidebar_info

MAX_ATTEMPTS = 10
LOCKOUT_SECONDS = 900  # 15 minutes
SESSION_PARAM = "s"  # query param name for session token
SESSION_TTL = 86400  # 24 hours in seconds

_auth_lock = threading.Lock()


@st.cache_resource
def _get_ip_locks():
    """Per-IP failed login counters: {ip: {"fail_count": int, "block_until": float}}."""
    return {}


@st.cache_resource
def _get_invalidated_tokens():
    """Blacklist for logged-out tokens: {token: expiry_timestamp}."""
    return {}


# ── Token helpers ────────────────────────────────────────────────

def _create_token(secret: str) -> str:
    """Creates a self-signed session token: ``timestamp.signature``.

    No server-side storage needed — validated purely via HMAC.
    """
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{ts}.{sig}"


def _validate_token(token: str, secret: str) -> bool:
    """Validates HMAC signature, checks expiry and logout blacklist."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        ts_str, sig = parts
        ts = int(ts_str)

        if time.time() - ts > SESSION_TTL:
            return False

        expected = hmac.new(
            secret.encode(), ts_str.encode(), hashlib.sha256,
        ).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return False

        return token not in _get_invalidated_tokens()
    except (ValueError, TypeError):
        return False


def _get_client_ip() -> str:
    """Best-effort client IP for per-IP brute-force tracking in Streamlit."""
    try:
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and hasattr(ctx, "request") and ctx.request:
            headers = getattr(ctx.request, "headers", {})
            ip = headers.get("X-Forwarded-For", "").split(",")[0].strip()
            if ip:
                return ip
            ip = headers.get("X-Real-Ip", "")
            if ip:
                return ip
    except Exception:
        pass
    return "unknown"


def _prune_expired_tokens():
    """Removes expired tokens from blacklist (called periodically)."""
    tokens = _get_invalidated_tokens()
    now = time.time()
    expired = [t for t, exp in tokens.items() if now > exp]
    for t in expired:
        tokens.pop(t, None)


# ── Main entry point ─────────────────────────────────────────────

def check_login():
    """Enforces password login with self-signed token session persistence."""

    # Global UI and CSS (rendered for all users, including login screen)
    logout_col = render_ui_header()
    render_sidebar_info()

    ip_locks = _get_ip_locks()
    client_ip = _get_client_ip()
    settings = Settings()
    secret = settings.dashboard_password

    if not secret:
        st.error("DASHBOARD_PASSWORD is not set. Configure it in .env before accessing the panel.")
        st.stop()

    # ── Handle logout ────────────────────────────────────────────
    if st.session_state.get("force_logout"):
        old_token = (
            st.session_state.get("session_token")
            or st.query_params.get(SESSION_PARAM)
        )
        if old_token:
            with _auth_lock:
                _get_invalidated_tokens()[str(old_token)] = time.time() + SESSION_TTL
        if SESSION_PARAM in st.query_params:
            del st.query_params[SESSION_PARAM]
        st.session_state.pop("session_token", None)
        st.session_state.pop("force_logout", None)
        st.rerun()

    # ── Restore token ────────────────────────────────────────────
    # Priority: session_state (page navigation) > query_params (F5 refresh)
    token = (
        st.session_state.get("session_token")
        or st.query_params.get(SESSION_PARAM)
    )

    if token and _validate_token(str(token), secret):
        token = str(token)

        # Sync → session_state (survives sidebar page navigation)
        if st.session_state.get("session_token") != token:
            st.session_state["session_token"] = token

        # Sync → query_params (survives F5 refresh)
        if st.query_params.get(SESSION_PARAM) != token:
            st.query_params[SESSION_PARAM] = token

        with logout_col:
            if st.button("Logout", key="logout_btn"):
                st.session_state["force_logout"] = True
                st.rerun()
        return

    # ── Login screen ─────────────────────────────────────────────
    st.title("Login")

    # Prune expired tokens periodically
    _prune_expired_tokens()

    now = time.time()
    with _auth_lock:
        ip_info = ip_locks.get(client_ip, {"fail_count": 0, "block_until": 0.0})

    if ip_info["block_until"] > now:
        wait_s = int(ip_info["block_until"] - now)
        st.error(f"Too many failed attempts. Locked for {wait_s}s.")
        st.stop()

    with st.form("login_form"):
        password = st.text_input("Access Password", type="password")
        submit = st.form_submit_button("Log In")

    if submit:
        if hmac.compare_digest(password, secret):
            with _auth_lock:
                ip_locks.pop(client_ip, None)
            new_token = _create_token(secret)
            st.session_state["session_token"] = new_token
            st.query_params[SESSION_PARAM] = new_token
            st.rerun()
        else:
            with _auth_lock:
                if client_ip not in ip_locks:
                    ip_locks[client_ip] = {"fail_count": 0, "block_until": 0.0}
                ip_locks[client_ip]["fail_count"] += 1
                if ip_locks[client_ip]["fail_count"] >= MAX_ATTEMPTS:
                    ip_locks[client_ip]["block_until"] = time.time() + LOCKOUT_SECONDS
                    ip_locks[client_ip]["fail_count"] = 0
                    st.error(f"Locked for {LOCKOUT_SECONDS // 60} minutes!")
                else:
                    remaining = MAX_ATTEMPTS - ip_locks[client_ip]["fail_count"]
                    st.error(f"Incorrect password. Attempts remaining: {remaining}")

    st.stop()
