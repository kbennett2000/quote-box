from __future__ import annotations

from flask import Blueprint
from flask.typing import ResponseReturnValue

from app.db import get_db
from app.queries import list_authors_with_counts

bp = Blueprint("authors", __name__)


@bp.get("/api/authors")
def list_authors() -> ResponseReturnValue:
    return list_authors_with_counts(get_db())
