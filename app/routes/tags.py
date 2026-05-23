from __future__ import annotations

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app import queries
from app.db import get_db
from app.validation import (
    ValidationError,
    normalize_tag_name,
    reject_unknown_fields,
)

bp = Blueprint("tags", __name__)


@bp.get("/api/tags")
def list_tags() -> ResponseReturnValue:
    return queries.list_tags_with_counts(get_db())


@bp.put("/api/tags/<int:tag_id>")
def rename_tag(tag_id: int) -> ResponseReturnValue:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return {"error": "request body must be a JSON object"}, 400
    try:
        reject_unknown_fields(body, {"name"})
        if "name" not in body:
            raise ValidationError("name is required")
        new_name = normalize_tag_name(body["name"])
    except ValidationError as e:
        return {"error": e.message}, 400

    try:
        result = queries.rename_tag(get_db(), tag_id, new_name)
    except queries.ConflictError as e:
        return {"error": str(e)}, 409
    if result is None:
        return {"error": "tag not found"}, 404
    return result


@bp.delete("/api/tags/<int:tag_id>")
def delete_tag(tag_id: int) -> ResponseReturnValue:
    if not queries.delete_tag(get_db(), tag_id):
        return {"error": "tag not found"}, 404
    return "", 204
