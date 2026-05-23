from __future__ import annotations

from flask.testing import FlaskClient


def test_health(client: FlaskClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
