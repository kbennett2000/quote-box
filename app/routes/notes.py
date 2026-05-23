"""Notes routes — covers per-quote note CRUD with profile ownership checks.

For PUT/DELETE on ``/api/notes/<id>``: existence is checked first (404), then
ownership (403). The ``profile_id`` is asserted via the JSON body on PUT and
via the ``?profile_id=N`` query parameter on DELETE.
"""

from __future__ import annotations

from typing import Final

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app import queries
from app.db import get_db
from app.validation import (
    ValidationError,
    reject_unknown_fields,
    require_int,
    require_str,
)

bp = Blueprint("notes", __name__)

_MAX_BODY_LEN: Final[int] = 10000


@bp.get("/api/quotes/<quote_id>/notes")
def list_notes(quote_id: str) -> ResponseReturnValue:
    if queries.get_quote(get_db(), quote_id) is None:
        return {"error": "quote not found"}, 404
    return {"notes": queries.list_notes_for_quote(get_db(), quote_id)}


@bp.post("/api/quotes/<quote_id>/notes")
def create_note(quote_id: str) -> ResponseReturnValue:
    if queries.get_quote(get_db(), quote_id) is None:
        return {"error": "quote not found"}, 404
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return {"error": "request body must be a JSON object"}, 400
    try:
        reject_unknown_fields(body, {"profile_id", "body"})
        profile_id = require_int(body, "profile_id")
        note_body = require_str(body, "body", max_len=_MAX_BODY_LEN)
    except ValidationError as e:
        return {"error": e.message}, 400

    if queries.get_profile(get_db(), profile_id) is None:
        return {"error": f"profile_id {profile_id} does not exist"}, 400

    note = queries.insert_note(get_db(), quote_id=quote_id, profile_id=profile_id, body=note_body)
    return note, 201


@bp.put("/api/notes/<int:note_id>")
def update_note(note_id: int) -> ResponseReturnValue:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return {"error": "request body must be a JSON object"}, 400
    try:
        reject_unknown_fields(body, {"profile_id", "body"})
        asserted_owner = require_int(body, "profile_id")
        note_body = require_str(body, "body", max_len=_MAX_BODY_LEN)
    except ValidationError as e:
        return {"error": e.message}, 400

    existing = queries.get_note(get_db(), note_id)
    if existing is None:
        return {"error": "note not found"}, 404
    if existing["profile_id"] != asserted_owner:
        return {"error": "profile_id does not match note owner"}, 403

    updated = queries.update_note(get_db(), note_id, note_body)
    assert updated is not None
    return updated


@bp.delete("/api/notes/<int:note_id>")
def delete_note(note_id: int) -> ResponseReturnValue:
    raw = request.args.get("profile_id")
    if raw is None or raw == "":
        return {"error": "profile_id query parameter is required"}, 400
    try:
        asserted_owner = int(raw)
    except ValueError:
        return {"error": "profile_id must be an integer"}, 400

    existing = queries.get_note(get_db(), note_id)
    if existing is None:
        return {"error": "note not found"}, 404
    if existing["profile_id"] != asserted_owner:
        return {"error": "profile_id does not match note owner"}, 403

    queries.delete_note(get_db(), note_id)
    return "", 204
