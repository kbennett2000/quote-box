"""SQLite connection helper, schema, and idempotent ``init_db``.

The schema mirrors SPEC §3. ``init_db`` runs ``CREATE TABLE IF NOT EXISTS`` for
every table and ensures the single-row ``schema_version`` table holds the
current version. Future schema bumps register migration callables keyed by
target version; the v1 release ships with none.

Connection management for HTTP handlers uses Flask's per-request ``g``; ``get_db``
opens lazily and ``close_db`` runs in ``teardown_appcontext``.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import cast

from flask import current_app, g

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION: int = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    author TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS quote_tags (
    quote_id TEXT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (quote_id, tag_id)
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    quote_id TEXT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Migration registry: MIGRATIONS[n] runs to upgrade FROM version n-1 TO n.
# Empty for v1; populate when bumping CURRENT_SCHEMA_VERSION.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def _connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = _connect(current_app.config["QUOTE_BOX"]["db_path"])
    return cast(sqlite3.Connection, g.db)


def close_db(e: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path: str | Path) -> None:
    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        cur = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cur.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (CURRENT_SCHEMA_VERSION,),
            )
        else:
            current = int(row["version"])
            for target in range(current + 1, CURRENT_SCHEMA_VERSION + 1):
                migration = MIGRATIONS.get(target)
                if migration is None:
                    raise RuntimeError(f"missing migration for schema version {target}")
                migration(conn)
                conn.execute("UPDATE schema_version SET version = ?", (target,))
        conn.commit()
    finally:
        conn.close()
