from __future__ import annotations

from typing import Final

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app import queries
from app.db import get_db
from app.validation import ValidationError, reject_unknown_fields, require_str

bp = Blueprint("profiles", __name__)

_MAX_NAME_LEN: Final[int] = 50


@bp.get("/api/profiles")
def list_profiles() -> ResponseReturnValue:
    return {"profiles": queries.list_profiles(get_db())}


@bp.post("/api/profiles")
def create_profile() -> ResponseReturnValue:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return {"error": "request body must be a JSON object"}, 400
    try:
        reject_unknown_fields(body, {"name"})
        name = require_str(body, "name", max_len=_MAX_NAME_LEN)
    except ValidationError as e:
        return {"error": e.message}, 400

    try:
        profile = queries.insert_profile(get_db(), name)
    except queries.ConflictError as e:
        return {"error": str(e)}, 409
    return profile, 201


@bp.delete("/api/profiles/<int:profile_id>")
def delete_profile(profile_id: int) -> ResponseReturnValue:
    if not queries.delete_profile(get_db(), profile_id):
        return {"error": "profile not found"}, 404
    return "", 204
