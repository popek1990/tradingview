# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : templates.py            #
# ----------------------------------------------- #

"""CRUD and rendering of message templates."""

import json
import logging
import os
import re
import tempfile
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
    """Saves templates to JSON file atomically (tempfile + os.replace)."""
    with _lock:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(TEMPLATES_FILE_PATH.parent), suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(TEMPLATES_FILE_PATH))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    logger.info("Templates saved (%d templates)", len(templates))


def render(name: str, variables: dict) -> str:
    """Renders a template by name with given variables.

    Raises:
        KeyError: if template doesn't exist
    """
    templates = load_templates()
    if name not in templates:
        raise KeyError(f"Template '{name}' does not exist")

    template = templates[name]
    if "content" not in template:
        raise KeyError(f"Template '{name}' is malformed (missing 'content' key)")
    content = template["content"]
    required = template.get("variables", [])

    # Simultaneous replacement — prevents variable value injection
    replacements = {f"{{{k}}}": str(variables.get(k, "")) for k in required}
    if not replacements:
        return content
    pattern = "|".join(re.escape(k) for k in replacements)
    return re.sub(pattern, lambda m: replacements[m.group(0)], content)
