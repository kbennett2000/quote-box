"""Read-only HTTP routes for quotes.

Route handlers do parameter parsing/validation only; all DB work goes through
``app.queries``. Error responses use the shape ``{"error": "<message>"}``.
"""

from __future__ import annotations

from typing import Any, Final

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app import queries
from app.db import get_db
from app.validation import (
    ValidationError,
    optional_str,
    parse_tags,
    reject_unknown_fields,
    require_str,
)

bp = Blueprint("quotes", __name__)

_DEFAULT_LIMIT: Final[int] = 50
_MAX_LIMIT: Final[int] = 200
_MAX_TEXT_LEN: Final[int] = 10000
_MAX_AUTHOR_LEN: Final[int] = 200
_MAX_SOURCE_LEN: Final[int] = 500
_QUOTE_FIELDS: Final[set[str]] = {"text", "author", "source", "tags"}


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


def _json_body() -> dict[str, Any] | tuple[dict[str, str], int]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return {"error": "request body must be a JSON object"}, 400
    return body


@bp.post("/api/quotes")
def create_quote() -> ResponseReturnValue:
    body = _json_body()
    if isinstance(body, tuple):
        return body
    try:
        reject_unknown_fields(body, _QUOTE_FIELDS)
        text = require_str(body, "text", max_len=_MAX_TEXT_LEN)
        author = optional_str(body, "author", max_len=_MAX_AUTHOR_LEN)
        source = optional_str(body, "source", max_len=_MAX_SOURCE_LEN)
        tags = parse_tags(body)
    except ValidationError as e:
        return {"error": e.message}, 400

    row = queries.insert_quote(get_db(), text=text, author=author, source=source, tags=tags)
    return row, 201


@bp.put("/api/quotes/<quote_id>")
def update_quote(quote_id: str) -> ResponseReturnValue:
    body = _json_body()
    if isinstance(body, tuple):
        return body
    try:
        reject_unknown_fields(body, _QUOTE_FIELDS)
        patch: dict[str, Any] = {}
        if "text" in body:
            patch["text"] = require_str(body, "text", max_len=_MAX_TEXT_LEN)
        if "author" in body:
            patch["author"] = optional_str(body, "author", max_len=_MAX_AUTHOR_LEN)
        if "source" in body:
            patch["source"] = optional_str(body, "source", max_len=_MAX_SOURCE_LEN)
        if "tags" in body:
            patch["tags"] = parse_tags(body)
    except ValidationError as e:
        return {"error": e.message}, 400

    updated = queries.update_quote(get_db(), quote_id, patch)
    if updated is None:
        return {"error": "quote not found"}, 404
    return updated


@bp.delete("/api/quotes/<quote_id>")
def delete_quote(quote_id: str) -> ResponseReturnValue:
    if not queries.delete_quote(get_db(), quote_id):
        return {"error": "quote not found"}, 404
    return "", 204
