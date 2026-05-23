"""One-shot seeding of the quote DB from ``data/quotes.json``.

Run at app-factory startup. No-ops if the ``quotes`` table is already populated,
so re-running on a warm DB is safe. If the JSON file is missing the app still
boots (logged as a warning) — the DB is simply left empty.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeedCounts:
    quotes: int
    tags: int
    quote_tags: int


def _connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def seed_if_empty(db_path: str | Path, json_path: str | Path) -> SeedCounts | None:
    json_path = Path(json_path)
    if not json_path.exists():
        logger.warning("seed file missing, leaving db empty", extra={"path": str(json_path)})
        return None

    conn = _connect(db_path)
    try:
        existing = conn.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"]
        if existing > 0:
            return None

        with json_path.open(encoding="utf-8") as f:
            quotes: list[dict[str, Any]] = json.load(f)

        unique_tag_names = sorted({tag for q in quotes for tag in q.get("tags") or []})

        with conn:
            conn.executemany(
                "INSERT INTO quotes (id, text, author, source) VALUES (?, ?, ?, ?)",
                [(q["id"], q["text"], q.get("author"), q.get("source")) for q in quotes],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                [(name,) for name in unique_tag_names],
            )
            tag_id_by_name = {
                row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM tags")
            }
            quote_tag_rows = [
                (q["id"], tag_id_by_name[tag]) for q in quotes for tag in q.get("tags") or []
            ]
            conn.executemany(
                "INSERT INTO quote_tags (quote_id, tag_id) VALUES (?, ?)",
                quote_tag_rows,
            )

        return SeedCounts(
            quotes=len(quotes),
            tags=len(unique_tag_names),
            quote_tags=len(quote_tag_rows),
        )
    finally:
        conn.close()
