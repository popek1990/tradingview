# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : aliases.py              #
# ----------------------------------------------- #

"""Alias system — TradingView message shortcuts.

Instead of pasting complex JSON in TradingView's Message field,
use short aliases like: /spot {{ticker}} {{exchange}} {{close}}

TradingView substitutes {{...}} placeholders before sending,
so the webhook receives: /spot 1INCHUSDT BINANCE 0.0964
"""

import json
import logging
import os
import re
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

ALIASES_FILE = Path(__file__).parent / "data" / "aliases.json"
REGEX_VAR_NAME = re.compile(r"^[a-zA-Z0-9_]{1,64}$")
_lock = threading.RLock()


def get_lock():
    """Returns the module lock for external read-modify-write operations."""
    return _lock


def load_aliases() -> dict:
    """Loads aliases from JSON file. Returns empty dict if missing."""
    try:
        with _lock:
            return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_aliases_unlocked() -> dict:
    """Loads aliases WITHOUT acquiring lock. Use only inside `with get_lock():`."""
    try:
        return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def validate_variable_names(variables: list[str]) -> None:
    """Validates variable names (alphanumeric + underscore only).

    Raises ValueError if any name is invalid.
    """
    for v in variables:
        if not REGEX_VAR_NAME.match(v):
            raise ValueError(f"Invalid variable name: '{v}' (use a-z, A-Z, 0-9, _)")


def save_aliases(aliases: dict) -> None:
    """Saves aliases to JSON file atomically (tempfile + os.replace)."""
    with _lock:
        ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(ALIASES_FILE.parent), suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(aliases, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(ALIASES_FILE))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    logger.info("Aliases saved (%d aliases)", len(aliases))


def humanize_interval(value: str) -> str:
    """Convert TradingView interval to human-readable format.

    TradingView sends numeric minutes (e.g., "60") or text ("1D", "1W", "1M").
    Converts: 1 → 1min, 60 → 1h, 240 → 4h, etc.
    Text values (D/W/M) are returned unchanged.
    """
    if not value.isdigit():
        return value

    minutes = int(value)
    if minutes < 60:
        return f"{minutes}min"
    hours, remainder = divmod(minutes, 60)
    if remainder == 0:
        return f"{hours}h"
    return f"{hours}h{remainder}min"


def parse_alias(text: str) -> str | None:
    """Parse alias command and render template.

    Input:  "/spot 1INCHUSDT BINANCE 0.0964"
    Output: "🎯 *Target* #1INCHUSDT na giełdzie *BINANCE* ✔️..."

    Returns None if text doesn't start with '/'.
    Raises KeyError if alias not found.
    Raises ValueError if wrong number of arguments.
    """
    text = text.strip()
    if not text.startswith("/"):
        return None

    parts = text.split()
    alias_name = parts[0][1:]  # strip leading "/"
    args = parts[1:]

    aliases = load_aliases()
    if alias_name not in aliases:
        raise KeyError(f"Unknown alias: /{alias_name}")

    alias_def = aliases[alias_name]
    if "template" not in alias_def:
        raise ValueError(f"Alias /{alias_name} is malformed (missing 'template' key)")
    variables = alias_def.get("variables", [])
    template = alias_def["template"]

    if len(args) != len(variables):
        raise ValueError(
            f"/{alias_name} expects {len(variables)} args "
            f"({', '.join(variables)}), got {len(args)}"
        )

    # Auto-convert interval variable to human-readable format
    # and inject {interval_raw} with original value (for TradingView chart URLs)
    replacements = {}
    for v, a in zip(variables, args):
        if v == "interval":
            replacements["{interval_raw}"] = a
            replacements[f"{{{v}}}"] = humanize_interval(a)
        else:
            replacements[f"{{{v}}}"] = a
    if not replacements:
        return template
    pattern = "|".join(re.escape(k) for k in replacements)
    result = re.sub(pattern, lambda m: replacements[m.group(0)], template)

    return result
