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


class QuoteRow(TypedDict):
    id: str
    text: str
    author: str | None
    source: str | None
    tags: list[str]


class TagCount(TypedDict):
    name: str
    count: int


class AuthorCount(TypedDict):
    name: str
    count: int


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
        "SELECT t.name, COUNT(qt.quote_id) AS count "
        "FROM tags t LEFT JOIN quote_tags qt ON qt.tag_id = t.id "
        "GROUP BY t.id, t.name "
        "ORDER BY count DESC, name ASC"
    ).fetchall()
    return [TagCount(name=r["name"], count=int(r["count"])) for r in rows]


def list_authors_with_counts(conn: sqlite3.Connection) -> list[AuthorCount]:
    rows = conn.execute(
        "SELECT author AS name, COUNT(*) AS count "
        "FROM quotes WHERE author IS NOT NULL "
        "GROUP BY author "
        "ORDER BY count DESC, name ASC"
    ).fetchall()
    return [AuthorCount(name=r["name"], count=int(r["count"])) for r in rows]
