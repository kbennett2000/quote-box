"""Configuration loading for quote-box.

Reads ``config.json`` from the project root if present, otherwise falls back to
``DEFAULT_CONFIG``. Missing keys in a user-supplied file are filled from the
defaults so future config additions don't break older config files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "port": 8035,
    "bind_host": "0.0.0.0",
    "db_path": "data/quotes.db",
    "seed_json_path": "data/quotes.json",
    "display_rotation_seconds": 20,
    "display_transition_ms": 800,
}


def load_config(path: Path = Path("config.json")) -> dict[str, Any]:
    if not path.exists():
        logger.info(
            "config file missing, using defaults",
            extra={"path": str(path)},
        )
        return dict(DEFAULT_CONFIG)

    with path.open(encoding="utf-8") as f:
        user_config: dict[str, Any] = json.load(f)

    merged = dict(DEFAULT_CONFIG)
    merged.update(user_config)
    logger.info("config loaded", extra={"path": str(path)})
    return merged
