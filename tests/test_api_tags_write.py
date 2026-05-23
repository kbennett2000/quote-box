from __future__ import annotations

import sqlite3

from flask.testing import FlaskClient


def _tag_id(db: sqlite3.Connection, name: str) -> int:
    row = db.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    assert row is not None, f"tag {name!r} not in fixture"
    return int(row["id"])


def test_rename_happy_path_updates_quote_tag_lists(
    client: FlaskClient, seeded_db: sqlite3.Connection
) -> None:
    tag_id = _tag_id(seeded_db, "wisdom")
    resp = client.put(f"/api/tags/{tag_id}", json={"name": "sagacity"})
    assert resp.status_code == 200
    assert resp.get_json() == {"id": tag_id, "name": "sagacity"}
    quote = client.get("/api/quotes/marcus-aurelius-the-happiness-of-your-life").get_json()
    assert "sagacity" in quote["tags"]
    assert "wisdom" not in quote["tags"]


def test_rename_to_same_name_is_idempotent(
    client: FlaskClient, seeded_db: sqlite3.Connection
) -> None:
    tag_id = _tag_id(seeded_db, "wisdom")
    resp = client.put(f"/api/tags/{tag_id}", json={"name": "wisdom"})
    assert resp.status_code == 200


def test_rename_collision_returns_409(client: FlaskClient, seeded_db: sqlite3.Connection) -> None:
    tag_id = _tag_id(seeded_db, "wisdom")
    resp = client.put(f"/api/tags/{tag_id}", json={"name": "life"})
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_rename_normalizes_case(client: FlaskClient, seeded_db: sqlite3.Connection) -> None:
    tag_id = _tag_id(seeded_db, "wisdom")
    resp = client.put(f"/api/tags/{tag_id}", json={"name": "  SAGACITY  "})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "sagacity"


def test_delete_cascade(client: FlaskClient, seeded_db: sqlite3.Connection) -> None:
    tag_id = _tag_id(seeded_db, "wisdom")
    resp = client.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 204
    quote = client.get("/api/quotes/marcus-aurelius-the-happiness-of-your-life").get_json()
    assert "wisdom" not in quote["tags"]
    # Quote itself untouched.
    assert quote["text"].startswith("The happiness of your life")


def test_delete_404_on_missing(client: FlaskClient) -> None:
    resp = client.delete("/api/tags/999999")
    assert resp.status_code == 404
