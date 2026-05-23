from __future__ import annotations

from flask import Blueprint

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}
