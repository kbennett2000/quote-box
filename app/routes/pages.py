"""HTML page routes.

Each handler reads URL params, calls the query layer, and renders a Jinja2
template. JS on the browse page progressively enhances the page; the
server-rendered initial state must be useful without JS.
"""

from __future__ import annotations

from typing import Final

from flask import Blueprint, abort, render_template, request
from flask.typing import ResponseReturnValue

from app import queries
from app.db import get_db

bp = Blueprint("pages", __name__)

_DEFAULT_LIMIT: Final[int] = 50


@bp.get("/")
def browse() -> ResponseReturnValue:
    db = get_db()
    q = request.args.get("q", "").strip() or None
    raw_tags = request.args.get("tags", "")
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()] or None
    author = request.args.get("author", "").strip() or None
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    offset = (page - 1) * _DEFAULT_LIMIT

    quotes, total = queries.list_quotes(
        db, q=q, tags=tags, author=author, limit=_DEFAULT_LIMIT, offset=offset
    )
    total_pages = max(1, (total + _DEFAULT_LIMIT - 1) // _DEFAULT_LIMIT)

    return render_template(
        "browse.html",
        quotes=quotes,
        total=total,
        page=page,
        total_pages=total_pages,
        all_tags=queries.list_tags_with_counts(db),
        all_authors=queries.list_authors_with_counts(db),
        selected_q=q or "",
        selected_tags=set(tags or []),
        selected_author=author or "",
    )


@bp.get("/quotes/<quote_id>")
def quote_detail(quote_id: str) -> ResponseReturnValue:
    quote = queries.get_quote(get_db(), quote_id)
    if quote is None:
        abort(404)
    return render_template("quote_detail.html", quote=quote)
