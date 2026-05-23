"""HTML page routes.

Each handler reads URL params, calls the query layer, and renders a Jinja2
template. JS on the browse page progressively enhances the page; the
server-rendered initial state must be useful without JS.

Profile flow lives here too: `/profile`, `/profile/select`, `/profile/switch`.
The `@require_profile` decorator (from app.profile) redirects HTML pages
without a valid cookie to the picker. The blueprint's `after_request` hook
slide-renews the cookie on every successful request that uses it, and a
`context_processor` exposes ``current_profile`` to every template.
"""

from __future__ import annotations

from typing import Any, Final

from flask import Blueprint, abort, redirect, render_template, request
from flask.typing import ResponseReturnValue
from werkzeug.wrappers import Response

from app import queries
from app.db import get_db
from app.profile import (
    COOKIE_NAME,
    clear_profile_cookie,
    load_current_profile,
    require_profile,
    safe_next,
    set_profile_cookie,
)
from app.queries import ConflictError
from app.validation import ValidationError, require_str

bp = Blueprint("pages", __name__)

_DEFAULT_LIMIT: Final[int] = 50
_MAX_PROFILE_NAME_LEN: Final[int] = 50


@bp.context_processor
def inject_current_profile() -> dict[str, Any]:
    return {"current_profile": load_current_profile()}


@bp.after_request
def slide_renew_cookie(response: Response) -> Response:
    profile = load_current_profile()
    if profile is not None and request.cookies.get(COOKIE_NAME) == str(profile["id"]):
        set_profile_cookie(response, profile["id"])
    return response


@bp.app_template_filter("to_iso8601")
def to_iso8601(value: str | None) -> str:
    """Convert SQLite ``YYYY-MM-DD HH:MM:SS`` (UTC) into a strict ISO-8601 string.

    SQLite's ``CURRENT_TIMESTAMP`` is UTC but emits no timezone marker; we
    append ``Z`` so the value parses identically in every browser.
    """
    if not value:
        return ""
    if "T" in value:
        return value if value.endswith("Z") else value + "Z"
    return value.replace(" ", "T") + "Z"


@bp.get("/")
@require_profile
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
@require_profile
def quote_detail(quote_id: str) -> ResponseReturnValue:
    db = get_db()
    quote = queries.get_quote(db, quote_id)
    if quote is None:
        abort(404)
    notes = queries.list_notes_for_quote(db, quote_id)
    return render_template("quote_detail.html", quote=quote, notes=notes)


@bp.get("/profile")
def profile() -> ResponseReturnValue:
    next_url = safe_next(request.args.get("next"))
    if load_current_profile() is not None:
        return redirect(next_url)
    return render_template(
        "profile_picker.html",
        profiles=queries.list_profiles(get_db()),
        next=next_url,
        form_name="",
        error=None,
    )


def _render_picker_with_error(form_name: str, error: str, next_url: str) -> ResponseReturnValue:
    return (
        render_template(
            "profile_picker.html",
            profiles=queries.list_profiles(get_db()),
            next=next_url,
            form_name=form_name,
            error=error,
        ),
        400,
    )


@bp.post("/profile/select")
def profile_select() -> ResponseReturnValue:
    next_url = safe_next(request.form.get("next"))
    raw_existing = request.form.get("existing_id", "").strip()
    raw_name = request.form.get("name", "")

    if raw_existing:
        try:
            existing_id = int(raw_existing)
        except ValueError:
            return _render_picker_with_error("", "Invalid profile selection.", next_url)
        if queries.get_profile(get_db(), existing_id) is None:
            return _render_picker_with_error("", "That profile no longer exists.", next_url)
        resp = redirect(next_url)
        set_profile_cookie(resp, existing_id)
        return resp

    try:
        name = require_str({"name": raw_name}, "name", max_len=_MAX_PROFILE_NAME_LEN)
    except ValidationError as e:
        return _render_picker_with_error(raw_name, e.message, next_url)

    try:
        created = queries.insert_profile(get_db(), name)
    except ConflictError:
        return _render_picker_with_error(name, f"Profile '{name}' already exists.", next_url)

    resp = redirect(next_url)
    set_profile_cookie(resp, created["id"])
    return resp


@bp.post("/profile/switch")
def profile_switch() -> ResponseReturnValue:
    resp = redirect("/profile")
    clear_profile_cookie(resp)
    return resp
