from __future__ import annotations

from flask.testing import FlaskClient

TOTAL_TAGS = 10


def test_list_tags_returns_all(client: FlaskClient) -> None:
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body, list)
    assert len(body) == TOTAL_TAGS
    for entry in body:
        assert set(entry.keys()) == {"name", "count"}


def test_list_tags_first_entry_is_top_count(client: FlaskClient) -> None:
    body = client.get("/api/tags").get_json()
    assert body[0] == {"name": "wisdom", "count": 4}


def test_list_tags_sort_order(client: FlaskClient) -> None:
    body = client.get("/api/tags").get_json()
    counts = [entry["count"] for entry in body]
    assert counts == sorted(counts, reverse=True)
    # Count=2 ties broken alphabetically.
    twos = [entry["name"] for entry in body if entry["count"] == 2]
    assert twos == ["action", "courage", "life", "philosophy"]
