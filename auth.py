"""Shared authentication module for the Streamlit panel.

Uses HMAC-signed session tokens that are self-validating — no server-side
session storage needed.  Token is persisted in both st.session_state (survives
page navigation) and st.query_params (survives browser F5 refresh).
"""

import hashlib
import hmac
import json
import logging
import threading
import time
from pathlib import Path

import streamlit as st
from config import Settings
from ui_utils import render_ui_header, render_sidebar_info

logger = logging.getLogger(__name__)

INVALIDATED_TOKENS_FILE = Path(__file__).parent / "invalidated_tokens.json"
IP_LOCKS_FILE = Path(__file__).parent / "logs" / "auth_locks.json"

MAX_ATTEMPTS = 10
LOCKOUT_SECONDS = 900  # 15 minutes
SESSION_PARAM = "s"  # query param name for session token
SESSION_TTL = 14400  # 4 hours in seconds

_auth_lock = threading.Lock()
_ip_locks_lock = threading.Lock()


def _load_ip_locks() -> dict:
    """Loads IP lockout data from JSON file. Prunes expired entries on load."""
    try:
        with _ip_locks_lock:
            data = json.loads(IP_LOCKS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    now = time.time()
    return {
        ip: info for ip, info in data.items()
        if info.get("block_until", 0) > now or info.get("fail_count", 0) > 0
    }


def _save_ip_locks(locks: dict) -> None:
    """Saves IP lockout data to JSON file atomically."""
    import os
    import tempfile
    with _ip_locks_lock:
        now = time.time()
        clean = {
            ip: info for ip, info in locks.items()
            if info.get("block_until", 0) > now or info.get("fail_count", 0) > 0
        }
        IP_LOCKS_FILE.parent.mkdir(mode=0o750, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(IP_LOCKS_FILE.parent), suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(clean, f)
            os.replace(tmp_path, str(IP_LOCKS_FILE))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


@st.cache_resource
def _get_ip_locks():
    """Per-IP failed login counters: {ip: {"fail_count": int, "block_until": float}}.

    Loaded from persistent file on first access.
    """
    return _load_ip_locks()


_token_lock = threading.Lock()


def _load_invalidated_tokens() -> dict:
    """Loads token blacklist from JSON file. Prunes expired entries on load."""
    try:
        with _token_lock:
            data = json.loads(INVALIDATED_TOKENS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    now = time.time()
    return {t: exp for t, exp in data.items() if exp > now}


def _save_invalidated_tokens(tokens: dict) -> None:
    """Saves token blacklist to JSON file atomically."""
    import os
    import tempfile
    with _token_lock:
        now = time.time()
        clean = {t: exp for t, exp in tokens.items() if exp > now}
        fd, tmp_path = tempfile.mkstemp(
            dir=str(INVALIDATED_TOKENS_FILE.parent), suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(clean, f)
            os.replace(tmp_path, str(INVALIDATED_TOKENS_FILE))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


@st.cache_resource
def _get_invalidated_tokens():
    """Blacklist for logged-out tokens: {token: expiry_timestamp}.

    Loaded from persistent file on first access.
    """
    return _load_invalidated_tokens()


# ── Token helpers ────────────────────────────────────────────────

def _create_token(secret: str) -> str:
    """Creates a self-signed session token: ``timestamp.signature``.

    No server-side storage needed — validated purely via HMAC.
    """
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
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
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False

        return token not in _get_invalidated_tokens()
    except (ValueError, TypeError):
        return False


def _get_client_ip() -> str:
    """Best-effort client IP for per-IP brute-force tracking in Streamlit.

    Uses socket IP (peer address) when available, since Streamlit typically
    runs without a reverse proxy in local/LAN deployments. This prevents
    IP spoofing via X-Forwarded-For headers.
    Falls back to X-Forwarded-For only when socket IP is a loopback address
    (indicating a real reverse proxy in front).
    """
    try:
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and hasattr(ctx, "request") and ctx.request:
            headers = getattr(ctx.request, "headers", {})

            # Prefer socket IP (not spoofable) for brute-force tracking
            peer_ip = headers.get("X-Real-Ip", "")

            # Only trust forwarded headers when behind a known proxy (loopback peer)
            if not peer_ip or peer_ip.startswith("127.") or peer_ip == "::1":
                forwarded = headers.get("X-Forwarded-For", "").split(",")[0].strip()
                if forwarded:
                    return forwarded

            if peer_ip:
                return peer_ip
    except Exception:
        pass
    return "unknown"


def _prune_expired_tokens():
    """Removes expired tokens from blacklist and persists to disk."""
    tokens = _get_invalidated_tokens()
    now = time.time()
    expired = [t for t, exp in tokens.items() if now > exp]
    if expired:
        for t in expired:
            tokens.pop(t, None)
        try:
            _save_invalidated_tokens(tokens)
        except Exception as e:
            logger.warning("Failed to persist token blacklist: %s", e)


def _prune_expired_locks():
    """Removes expired IP lockout entries to prevent memory leak."""
    ip_locks = _get_ip_locks()
    now = time.time()
    expired = [
        ip for ip, info in ip_locks.items()
        if info["block_until"] > 0 and info["block_until"] <= now and info["fail_count"] == 0
    ]
    if expired:
        for ip in expired:
            ip_locks.pop(ip, None)
        try:
            _save_ip_locks(ip_locks)
        except Exception as e:
            logger.warning("Failed to persist IP locks: %s", e)


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
                tokens = _get_invalidated_tokens()
                tokens[str(old_token)] = time.time() + SESSION_TTL
                try:
                    _save_invalidated_tokens(tokens)
                except Exception as e:
                    logger.warning("Failed to persist token blacklist: %s", e)
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

    # Prune expired entries periodically
    _prune_expired_tokens()
    _prune_expired_locks()

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
            try:
                _save_ip_locks(ip_locks)
            except Exception as e:
                logger.warning("Failed to persist IP locks: %s", e)
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
            try:
                _save_ip_locks(ip_locks)
            except Exception as e:
                logger.warning("Failed to persist IP locks: %s", e)

    st.stop()
