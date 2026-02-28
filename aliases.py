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
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

ALIASES_FILE = Path(__file__).parent / "aliases.json"
_lock = threading.Lock()


def load_aliases() -> dict:
    """Loads aliases from JSON file. Returns empty dict if missing."""
    try:
        with _lock:
            return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_aliases(aliases: dict) -> None:
    """Saves aliases to JSON file."""
    with _lock:
        ALIASES_FILE.write_text(
            json.dumps(aliases, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    logger.info("Aliases saved (%d aliases)", len(aliases))


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
    variables = alias_def.get("variables", [])
    template = alias_def["template"]

    if len(args) != len(variables):
        raise ValueError(
            f"/{alias_name} expects {len(variables)} args "
            f"({', '.join(variables)}), got {len(args)}"
        )

    result = template
    for var_name, var_value in zip(variables, args):
        result = result.replace(f"{{{var_name}}}", var_value)

    return result
