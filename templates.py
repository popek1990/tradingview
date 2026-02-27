# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : templates.py            #
# ----------------------------------------------- #

"""CRUD and rendering of message templates."""

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATES_FILE_PATH = Path(__file__).parent / "templates.json"
_lock = threading.Lock()


def load_templates() -> dict:
    """Loads templates from JSON file. Returns empty dict if file doesn't exist."""
    try:
        with _lock:
            return json.loads(TEMPLATES_FILE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_templates(templates: dict) -> None:
    """Saves templates to JSON file."""
    with _lock:
        TEMPLATES_FILE_PATH.write_text(
            json.dumps(templates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    logger.info("Templates saved (%d templates)", len(templates))


def render(name: str, variables: dict) -> str:
    """Renders a template by name with given variables.

    Raises:
        KeyError: if template doesn't exist
        ValueError: if a required variable is missing
    """
    templates = load_templates()
    if name not in templates:
        raise KeyError(f"Template '{name}' does not exist")

    template = templates[name]
    content = template["content"]
    required = template.get("variables", [])

    # Substitute variables — safe str.replace() instead of str.format()
    result = content
    for k in required:
        result = result.replace(f"{{{k}}}", str(variables.get(k, "")))
    return result
