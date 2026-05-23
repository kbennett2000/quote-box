from __future__ import annotations

from flask import Blueprint
from flask.typing import ResponseReturnValue

from app.db import get_db
from app.queries import list_tags_with_counts

bp = Blueprint("tags", __name__)


@bp.get("/api/tags")
def list_tags() -> ResponseReturnValue:
    return list_tags_with_counts(get_db())
