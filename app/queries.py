"""Read-only query layer for quotes, tags, and authors.

Pure functions over a ``sqlite3.Connection`` — no Flask globals, no app context.
HTTP route handlers in ``app/routes/`` parse and validate query strings and then
delegate to these functions. All SQL uses ``?`` placeholders.

The ``WHERE`` fragment is built in one place (``_build_filter_clause``) and
reused by ``list_quotes``, the matching ``COUNT(*)``, ``random_quote``, and
``shuffle_ids`` so the filters can never drift out of sync between code paths.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from typing import Any, TypedDict

from app.ids import generate_slug


class ConflictError(Exception):
    """Raised when a write would violate a UNIQUE constraint (tag/profile name)."""


class QuoteRow(TypedDict):
    id: str
    text: str
    author: str | None
    source: str | None
    tags: list[str]


class TagCount(TypedDict):
    id: int
    name: str
    count: int


class AuthorCount(TypedDict):
    name: str
    count: int


class TagRow(TypedDict):
    id: int
    name: str


class ProfileRow(TypedDict):
    id: int
    name: str
    created_at: str


class NoteRow(TypedDict):
    id: int
    quote_id: str
    profile_id: int
    profile_name: str
    body: str
    created_at: str
    updated_at: str


_LIKE_ESCAPE = "\\"


def _escape_like(value: str) -> str:
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


def _dedup_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _build_filter_clause(
    q: str | None,
    tags: Sequence[str] | None,
    author: str | None,
) -> tuple[str, list[Any]]:
    """Return a ``WHERE ...`` SQL fragment and parameters for filtering quotes.

    The fragment is built around the ``quotes q`` alias and includes a subquery
    join for tag-AND so the caller does not need to add its own GROUP BY.
    Returns ``("", [])`` when no filters apply.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if q:
        like = f"%{_escape_like(q.lower())}%"
        clauses.append(
            "(LOWER(q.text) LIKE ? ESCAPE '\\' "
            "OR LOWER(q.author) LIKE ? ESCAPE '\\' "
            "OR LOWER(q.source) LIKE ? ESCAPE '\\')"
        )
        params.extend([like, like, like])

    if author:
        clauses.append("q.author = ?")
        params.append(author)

    if tags:
        unique_tags = _dedup_preserve_order(tags)
        placeholders = ", ".join("?" for _ in unique_tags)
        clauses.append(
            f"q.id IN ("
            f"SELECT qt.quote_id FROM quote_tags qt "
            f"JOIN tags t ON t.id = qt.tag_id "
            f"WHERE t.name IN ({placeholders}) "
            f"GROUP BY qt.quote_id "
            f"HAVING COUNT(DISTINCT t.name) = ?)"
        )
        params.extend(unique_tags)
        params.append(len(unique_tags))

    if not clauses:
        return "", []
    return "WHERE " + " AND ".join(clauses), params


def _hydrate_tags(conn: sqlite3.Connection, quote_ids: Sequence[str]) -> dict[str, list[str]]:
    if not quote_ids:
        return {}
    placeholders = ", ".join("?" for _ in quote_ids)
    rows = conn.execute(
        f"SELECT qt.quote_id, t.name "
        f"FROM quote_tags qt JOIN tags t ON t.id = qt.tag_id "
        f"WHERE qt.quote_id IN ({placeholders}) "
        f"ORDER BY qt.quote_id, t.name",
        list(quote_ids),
    ).fetchall()
    result: dict[str, list[str]] = {qid: [] for qid in quote_ids}
    for row in rows:
        result[row["quote_id"]].append(row["name"])
    return result


def _row_to_quote(row: sqlite3.Row, tags: list[str]) -> QuoteRow:
    return QuoteRow(
        id=row["id"],
        text=row["text"],
        author=row["author"],
        source=row["source"],
        tags=tags,
    )


def list_quotes(
    conn: sqlite3.Connection,
    *,
    q: str | None = None,
    tags: Sequence[str] | None = None,
    author: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[QuoteRow], int]:
    where, params = _build_filter_clause(q, tags, author)

    total_row = conn.execute(f"SELECT COUNT(*) AS n FROM quotes q {where}", params).fetchone()
    total = int(total_row["n"])

    rows = conn.execute(
        f"SELECT q.id, q.text, q.author, q.source "
        f"FROM quotes q {where} "
        f"ORDER BY q.id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    tags_by_id = _hydrate_tags(conn, [r["id"] for r in rows])
    return [_row_to_quote(r, tags_by_id.get(r["id"], [])) for r in rows], total


def get_quote(conn: sqlite3.Connection, quote_id: str) -> QuoteRow | None:
    row = conn.execute(
        "SELECT id, text, author, source FROM quotes WHERE id = ?", (quote_id,)
    ).fetchone()
    if row is None:
        return None
    tags_by_id = _hydrate_tags(conn, [quote_id])
    return _row_to_quote(row, tags_by_id.get(quote_id, []))


def random_quote(
    conn: sqlite3.Connection,
    *,
    tags: Sequence[str] | None = None,
    author: str | None = None,
) -> QuoteRow | None:
    where, params = _build_filter_clause(None, tags, author)
    row = conn.execute(
        f"SELECT q.id FROM quotes q {where} ORDER BY RANDOM() LIMIT 1", params
    ).fetchone()
    if row is None:
        return None
    result = get_quote(conn, row["id"])
    return result


def shuffle_ids(
    conn: sqlite3.Connection,
    *,
    tags: Sequence[str] | None = None,
    author: str | None = None,
) -> list[str]:
    where, params = _build_filter_clause(None, tags, author)
    rows = conn.execute(f"SELECT q.id FROM quotes q {where} ORDER BY RANDOM()", params).fetchall()
    return [r["id"] for r in rows]


def list_tags_with_counts(conn: sqlite3.Connection) -> list[TagCount]:
    rows = conn.execute(
        "SELECT t.id AS id, t.name, COUNT(qt.quote_id) AS count "
        "FROM tags t LEFT JOIN quote_tags qt ON qt.tag_id = t.id "
        "GROUP BY t.id, t.name "
        "ORDER BY count DESC, name ASC"
    ).fetchall()
    return [TagCount(id=int(r["id"]), name=r["name"], count=int(r["count"])) for r in rows]


def list_authors_with_counts(conn: sqlite3.Connection) -> list[AuthorCount]:
    rows = conn.execute(
        "SELECT author AS name, COUNT(*) AS count "
        "FROM quotes WHERE author IS NOT NULL "
        "GROUP BY author "
        "ORDER BY count DESC, name ASC"
    ).fetchall()
    return [AuthorCount(name=r["name"], count=int(r["count"])) for r in rows]


def _upsert_tag_ids(conn: sqlite3.Connection, tag_names: Sequence[str]) -> list[int]:
    if not tag_names:
        return []
    conn.executemany(
        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
        [(name,) for name in tag_names],
    )
    placeholders = ", ".join("?" for _ in tag_names)
    rows = conn.execute(
        f"SELECT id, name FROM tags WHERE name IN ({placeholders})",
        list(tag_names),
    ).fetchall()
    name_to_id = {r["name"]: int(r["id"]) for r in rows}
    return [name_to_id[name] for name in tag_names]


def insert_quote(
    conn: sqlite3.Connection,
    *,
    text: str,
    author: str | None,
    source: str | None,
    tags: Sequence[str] | None,
) -> QuoteRow:
    with conn:
        existing_ids = {r["id"] for r in conn.execute("SELECT id FROM quotes").fetchall()}
        quote_id = generate_slug(author, text, existing_ids)
        conn.execute(
            "INSERT INTO quotes (id, text, author, source) VALUES (?, ?, ?, ?)",
            (quote_id, text, author, source),
        )
        if tags:
            tag_ids = _upsert_tag_ids(conn, list(tags))
            conn.executemany(
                "INSERT INTO quote_tags (quote_id, tag_id) VALUES (?, ?)",
                [(quote_id, tid) for tid in tag_ids],
            )
    row = get_quote(conn, quote_id)
    assert row is not None
    return row


def update_quote(
    conn: sqlite3.Connection,
    quote_id: str,
    patch: dict[str, Any],
) -> QuoteRow | None:
    existing = get_quote(conn, quote_id)
    if existing is None:
        return None
    if not patch:
        return existing

    column_updates: list[tuple[str, Any]] = [
        (col, patch[col]) for col in ("text", "author", "source") if col in patch
    ]

    with conn:
        set_parts = [f"{col} = ?" for col, _ in column_updates]
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        params: list[Any] = [val for _, val in column_updates]
        params.append(quote_id)
        conn.execute(
            f"UPDATE quotes SET {', '.join(set_parts)} WHERE id = ?",
            params,
        )

        if "tags" in patch:
            conn.execute("DELETE FROM quote_tags WHERE quote_id = ?", (quote_id,))
            new_tags = patch["tags"] or []
            if new_tags:
                tag_ids = _upsert_tag_ids(conn, list(new_tags))
                conn.executemany(
                    "INSERT INTO quote_tags (quote_id, tag_id) VALUES (?, ?)",
                    [(quote_id, tid) for tid in tag_ids],
                )

    return get_quote(conn, quote_id)


def delete_quote(conn: sqlite3.Connection, quote_id: str) -> bool:
    with conn:
        cur = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    return cur.rowcount > 0


def get_tag(conn: sqlite3.Connection, tag_id: int) -> TagRow | None:
    row = conn.execute("SELECT id, name FROM tags WHERE id = ?", (tag_id,)).fetchone()
    if row is None:
        return None
    return TagRow(id=int(row["id"]), name=row["name"])


def rename_tag(conn: sqlite3.Connection, tag_id: int, new_name: str) -> TagRow | None:
    current = get_tag(conn, tag_id)
    if current is None:
        return None
    if current["name"] == new_name:
        return current
    try:
        with conn:
            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (new_name, tag_id))
    except sqlite3.IntegrityError as e:
        raise ConflictError(f"tag name '{new_name}' already exists") from e
    return get_tag(conn, tag_id)


def delete_tag(conn: sqlite3.Connection, tag_id: int) -> bool:
    with conn:
        cur = conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    return cur.rowcount > 0


def list_profiles(conn: sqlite3.Connection) -> list[ProfileRow]:
    rows = conn.execute("SELECT id, name, created_at FROM profiles ORDER BY id").fetchall()
    return [ProfileRow(id=int(r["id"]), name=r["name"], created_at=r["created_at"]) for r in rows]


def get_profile(conn: sqlite3.Connection, profile_id: int) -> ProfileRow | None:
    row = conn.execute(
        "SELECT id, name, created_at FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    if row is None:
        return None
    return ProfileRow(id=int(row["id"]), name=row["name"], created_at=row["created_at"])


def insert_profile(conn: sqlite3.Connection, name: str) -> ProfileRow:
    try:
        with conn:
            cur = conn.execute("INSERT INTO profiles (name) VALUES (?)", (name,))
    except sqlite3.IntegrityError as e:
        raise ConflictError(f"profile name '{name}' already exists") from e
    profile_id = int(cur.lastrowid or 0)
    result = get_profile(conn, profile_id)
    assert result is not None
    return result


def delete_profile(conn: sqlite3.Connection, profile_id: int) -> bool:
    with conn:
        cur = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    return cur.rowcount > 0


def _row_to_note(row: sqlite3.Row) -> NoteRow:
    return NoteRow(
        id=int(row["id"]),
        quote_id=row["quote_id"],
        profile_id=int(row["profile_id"]),
        profile_name=row["profile_name"],
        body=row["body"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


_NOTE_SELECT = (
    "SELECT n.id, n.quote_id, n.profile_id, p.name AS profile_name, "
    "n.body, n.created_at, n.updated_at "
    "FROM notes n JOIN profiles p ON p.id = n.profile_id "
)


def list_notes_for_quote(conn: sqlite3.Connection, quote_id: str) -> list[NoteRow]:
    rows = conn.execute(
        _NOTE_SELECT + "WHERE n.quote_id = ? ORDER BY n.created_at ASC, n.id ASC",
        (quote_id,),
    ).fetchall()
    return [_row_to_note(r) for r in rows]


def get_note(conn: sqlite3.Connection, note_id: int) -> NoteRow | None:
    row = conn.execute(_NOTE_SELECT + "WHERE n.id = ?", (note_id,)).fetchone()
    if row is None:
        return None
    return _row_to_note(row)


def insert_note(conn: sqlite3.Connection, *, quote_id: str, profile_id: int, body: str) -> NoteRow:
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (quote_id, profile_id, body) VALUES (?, ?, ?)",
            (quote_id, profile_id, body),
        )
    note_id = int(cur.lastrowid or 0)
    result = get_note(conn, note_id)
    assert result is not None
    return result


def update_note(conn: sqlite3.Connection, note_id: int, body: str) -> NoteRow | None:
    with conn:
        cur = conn.execute(
            "UPDATE notes SET body = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (body, note_id),
        )
    if cur.rowcount == 0:
        return None
    return get_note(conn, note_id)


def delete_note(conn: sqlite3.Connection, note_id: int) -> bool:
    with conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    return cur.rowcount > 0
