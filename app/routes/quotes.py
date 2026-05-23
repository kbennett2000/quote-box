"""Read-only HTTP routes for quotes.

Route handlers do parameter parsing/validation only; all DB work goes through
``app.queries``. Error responses use the shape ``{"error": "<message>"}``.
"""

from __future__ import annotations

from typing import Final

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app import queries
from app.db import get_db

bp = Blueprint("quotes", __name__)

_DEFAULT_LIMIT: Final[int] = 50
_MAX_LIMIT: Final[int] = 200


def _parse_int(
    raw: str | None,
    field: str,
    *,
    default: int,
    min_value: int,
    max_value: int | None,
) -> int | tuple[dict[str, str], int]:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return {"error": f"{field} must be an integer"}, 400
    if value < min_value:
        return {"error": f"{field} must be >= {min_value}"}, 400
    if max_value is not None and value > max_value:
        return max_value
    return value


def _parse_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    return trimmed or None


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


@bp.get("/api/quotes")
def list_quotes() -> ResponseReturnValue:
    limit = _parse_int(
        request.args.get("limit"),
        "limit",
        default=_DEFAULT_LIMIT,
        min_value=1,
        max_value=_MAX_LIMIT,
    )
    if isinstance(limit, tuple):
        return limit
    offset = _parse_int(
        request.args.get("offset"),
        "offset",
        default=0,
        min_value=0,
        max_value=None,
    )
    if isinstance(offset, tuple):
        return offset

    rows, total = queries.list_quotes(
        get_db(),
        q=_parse_str(request.args.get("q")),
        tags=_parse_tags(request.args.get("tags")) or None,
        author=_parse_str(request.args.get("author")),
        limit=limit,
        offset=offset,
    )
    return {"quotes": rows, "total": total, "limit": limit, "offset": offset}


@bp.get("/api/quotes/random")
def random_quote() -> ResponseReturnValue:
    row = queries.random_quote(
        get_db(),
        tags=_parse_tags(request.args.get("tags")) or None,
        author=_parse_str(request.args.get("author")),
    )
    if row is None:
        return {"error": "no quotes match"}, 404
    return row


@bp.get("/api/quotes/shuffle")
def shuffle_ids() -> ResponseReturnValue:
    ids = queries.shuffle_ids(
        get_db(),
        tags=_parse_tags(request.args.get("tags")) or None,
        author=_parse_str(request.args.get("author")),
    )
    return {"ids": ids}


@bp.get("/api/quotes/<quote_id>")
def get_quote(quote_id: str) -> ResponseReturnValue:
    row = queries.get_quote(get_db(), quote_id)
    if row is None:
        return {"error": "quote not found"}, 404
    return row
