from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db import CURRENT_SCHEMA_VERSION, _connect, init_db

EXPECTED_TABLES = {"quotes", "tags", "quote_tags", "profiles", "notes", "schema_version"}


def test_schema_tables_exist(empty_db: sqlite3.Connection) -> None:
    rows = empty_db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = {r["name"] for r in rows}
    assert EXPECTED_TABLES <= names


def test_schema_version_recorded(empty_db: sqlite3.Connection) -> None:
    rows = empty_db.execute("SELECT version FROM schema_version").fetchall()
    assert len(rows) == 1
    assert rows[0]["version"] == CURRENT_SCHEMA_VERSION


def test_init_db_idempotent(db_path: Path) -> None:
    init_db(db_path)
    init_db(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
        assert len(rows) == 1
        assert rows[0]["version"] == CURRENT_SCHEMA_VERSION
    finally:
        conn.close()


def test_foreign_keys_enabled(empty_db: sqlite3.Connection) -> None:
    row = empty_db.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_cascade_delete_quote_removes_notes_and_quote_tags(empty_db: sqlite3.Connection) -> None:
    with empty_db:
        empty_db.execute(
            "INSERT INTO quotes (id, text, author) VALUES (?, ?, ?)",
            ("q1", "hello world", "Anon"),
        )
        empty_db.execute("INSERT INTO tags (name) VALUES (?)", ("greeting",))
        tag_id = empty_db.execute("SELECT id FROM tags WHERE name = ?", ("greeting",)).fetchone()[
            "id"
        ]
        empty_db.execute("INSERT INTO quote_tags (quote_id, tag_id) VALUES (?, ?)", ("q1", tag_id))
        empty_db.execute("INSERT INTO profiles (name) VALUES (?)", ("alice",))
        profile_id = empty_db.execute(
            "SELECT id FROM profiles WHERE name = ?", ("alice",)
        ).fetchone()["id"]
        empty_db.execute(
            "INSERT INTO notes (quote_id, profile_id, body) VALUES (?, ?, ?)",
            ("q1", profile_id, "nice"),
        )

    with empty_db:
        empty_db.execute("DELETE FROM quotes WHERE id = ?", ("q1",))

    assert empty_db.execute("SELECT COUNT(*) AS n FROM quote_tags").fetchone()["n"] == 0
    assert empty_db.execute("SELECT COUNT(*) AS n FROM notes").fetchone()["n"] == 0
    # The tag itself is not deleted — only the join row.
    assert empty_db.execute("SELECT COUNT(*) AS n FROM tags").fetchone()["n"] == 1


def test_cascade_delete_profile_removes_notes(empty_db: sqlite3.Connection) -> None:
    with empty_db:
        empty_db.execute("INSERT INTO quotes (id, text) VALUES (?, ?)", ("q1", "hi"))
        empty_db.execute("INSERT INTO profiles (name) VALUES (?)", ("bob",))
        profile_id = empty_db.execute(
            "SELECT id FROM profiles WHERE name = ?", ("bob",)
        ).fetchone()["id"]
        empty_db.execute(
            "INSERT INTO notes (quote_id, profile_id, body) VALUES (?, ?, ?)",
            ("q1", profile_id, "thoughts"),
        )

    with empty_db:
        empty_db.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))

    assert empty_db.execute("SELECT COUNT(*) AS n FROM notes").fetchone()["n"] == 0
    # The quote itself is untouched.
    assert empty_db.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"] == 1


def test_parameterized_query_safe_against_injection(empty_db: sqlite3.Connection) -> None:
    nasty = "'); DROP TABLE quotes; --"
    with empty_db:
        empty_db.execute(
            "INSERT INTO quotes (id, text, author) VALUES (?, ?, ?)",
            ("inj1", nasty, "Mallory"),
        )

    stored = empty_db.execute("SELECT text FROM quotes WHERE id = ?", ("inj1",)).fetchone()
    assert stored["text"] == nasty
    # The quotes table must still exist.
    tables = empty_db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'quotes'"
    ).fetchall()
    assert len(tables) == 1
