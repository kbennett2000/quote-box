from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db import _connect, init_db
from app.seed import seed_if_empty

# Constants matching tests/fixtures/quotes_sample.json:
EXPECTED_QUOTES = 12
EXPECTED_TAGS = 10
EXPECTED_QUOTE_TAGS = 17


def _row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "quotes": conn.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"],
        "tags": conn.execute("SELECT COUNT(*) AS n FROM tags").fetchone()["n"],
        "quote_tags": conn.execute("SELECT COUNT(*) AS n FROM quote_tags").fetchone()["n"],
    }


def test_seed_inserts_expected_counts(seeded_db: sqlite3.Connection) -> None:
    counts = _row_counts(seeded_db)
    assert counts == {
        "quotes": EXPECTED_QUOTES,
        "tags": EXPECTED_TAGS,
        "quote_tags": EXPECTED_QUOTE_TAGS,
    }


def test_seed_returns_counts(db_path: Path, seed_json: Path) -> None:
    init_db(db_path)
    counts = seed_if_empty(db_path, seed_json)
    assert counts is not None
    assert counts.quotes == EXPECTED_QUOTES
    assert counts.tags == EXPECTED_TAGS
    assert counts.quote_tags == EXPECTED_QUOTE_TAGS


def test_seed_idempotent_when_empty(db_path: Path, seed_json: Path) -> None:
    init_db(db_path)
    first = seed_if_empty(db_path, seed_json)
    second = seed_if_empty(db_path, seed_json)
    assert first is not None
    assert second is None
    conn = _connect(db_path)
    try:
        assert _row_counts(conn) == {
            "quotes": EXPECTED_QUOTES,
            "tags": EXPECTED_TAGS,
            "quote_tags": EXPECTED_QUOTE_TAGS,
        }
    finally:
        conn.close()


def test_seed_skips_when_quotes_present(db_path: Path, seed_json: Path) -> None:
    init_db(db_path)
    conn = _connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO quotes (id, text, author) VALUES (?, ?, ?)",
                ("preexisting", "I was here first", "Squatter"),
            )
    finally:
        conn.close()

    counts = seed_if_empty(db_path, seed_json)
    assert counts is None

    conn = _connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"] == 1
    finally:
        conn.close()


def test_seed_dedupes_tags(seeded_db: sqlite3.Connection) -> None:
    distinct = seeded_db.execute("SELECT COUNT(DISTINCT name) AS n FROM tags").fetchone()["n"]
    total = seeded_db.execute("SELECT COUNT(*) AS n FROM tags").fetchone()["n"]
    assert distinct == total == EXPECTED_TAGS


def test_seed_quote_tags_links_correct(seeded_db: sqlite3.Connection) -> None:
    rows = seeded_db.execute(
        """
        SELECT t.name FROM quote_tags qt
        JOIN tags t ON t.id = qt.tag_id
        WHERE qt.quote_id = ?
        ORDER BY t.name
        """,
        ("andre-gide-trust-those-who-seek-the",),
    ).fetchall()
    assert [r["name"] for r in rows] == ["doubt", "wisdom"]


def test_seed_handles_null_author_and_source(seeded_db: sqlite3.Connection) -> None:
    row = seeded_db.execute(
        "SELECT author, source FROM quotes WHERE id = ?",
        ("anonymous-the-only-way-to-do-great",),
    ).fetchone()
    assert row["author"] is None
    assert row["source"] is None


def test_seed_handles_empty_tags_list(seeded_db: sqlite3.Connection) -> None:
    row = seeded_db.execute(
        "SELECT COUNT(*) AS n FROM quote_tags WHERE quote_id = ?",
        ("unknown-be-yourself-everyone-else-is",),
    ).fetchone()
    assert row["n"] == 0


def test_seed_missing_json_logs_and_no_ops(db_path: Path, tmp_path: Path) -> None:
    init_db(db_path)
    nonexistent = tmp_path / "does-not-exist.json"
    counts = seed_if_empty(db_path, nonexistent)
    assert counts is None
    conn = _connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"] == 0
    finally:
        conn.close()
