from __future__ import annotations

from flask.testing import FlaskClient

NON_NULL_AUTHORS = 11


def test_list_authors_returns_all(client: FlaskClient) -> None:
    resp = client.get("/api/authors")
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body, list)
    assert len(body) == NON_NULL_AUTHORS
    for entry in body:
        assert set(entry.keys()) == {"name", "count"}


def test_list_authors_excludes_null(client: FlaskClient) -> None:
    body = client.get("/api/authors").get_json()
    names = [entry["name"] for entry in body]
    assert None not in names
    assert all(isinstance(n, str) for n in names)


def test_list_authors_sort_order(client: FlaskClient) -> None:
    body = client.get("/api/authors").get_json()
    # Every fixture author appears exactly once, so the sort is purely alphabetical.
    assert all(entry["count"] == 1 for entry in body)
    names = [entry["name"] for entry in body]
    assert names == sorted(names)
