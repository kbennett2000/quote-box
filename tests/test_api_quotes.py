from __future__ import annotations

from flask.testing import FlaskClient

TOTAL_QUOTES = 12


def test_list_returns_shape_and_total(client: FlaskClient) -> None:
    resp = client.get("/api/quotes")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body.keys()) == {"quotes", "total", "limit", "offset"}
    assert body["total"] == TOTAL_QUOTES
    assert len(body["quotes"]) == TOTAL_QUOTES
    assert body["limit"] == 50
    assert body["offset"] == 0
    # Each quote object has the expected keys.
    for q in body["quotes"]:
        assert set(q.keys()) == {"id", "text", "author", "source", "tags"}


def test_list_limit_clamps_to_max(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?limit=300")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["limit"] == 200
    assert len(body["quotes"]) == TOTAL_QUOTES  # all 12 still fit under 200


def test_list_limit_honored(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?limit=5")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["limit"] == 5
    assert len(body["quotes"]) == 5
    assert body["total"] == TOTAL_QUOTES


def test_list_offset_pages_through(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?offset=10")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["offset"] == 10
    assert len(body["quotes"]) == TOTAL_QUOTES - 10
    assert body["total"] == TOTAL_QUOTES


def test_list_invalid_limit_returns_400(client: FlaskClient) -> None:
    for bad in ("abc", "0", "-1"):
        resp = client.get(f"/api/quotes?limit={bad}")
        assert resp.status_code == 400, bad
        assert "error" in resp.get_json()


def test_list_invalid_offset_returns_400(client: FlaskClient) -> None:
    for bad in ("abc", "-1"):
        resp = client.get(f"/api/quotes?offset={bad}")
        assert resp.status_code == 400, bad
        assert "error" in resp.get_json()


def test_list_q_filter(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?q=courage")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1


def test_list_author_filter(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?author=Seneca")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["quotes"][0]["author"] == "Seneca"


def test_list_tags_single(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?tags=wisdom")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 4


def test_list_tags_and_semantics(client: FlaskClient) -> None:
    resp = client.get("/api/quotes?tags=wisdom,life")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["quotes"][0]["id"] == "marcus-aurelius-the-happiness-of-your-life"


def test_get_single_quote_found(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/epicurus-death-is-nothing-to-us")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["author"] == "Epicurus"
    assert body["tags"] == ["death", "philosophy"]


def test_get_single_quote_not_found(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/does-not-exist")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_random_returns_a_quote(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/random")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body.keys()) == {"id", "text", "author", "source", "tags"}


def test_random_respects_author_filter(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/random?author=Seneca")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Seneca"


def test_random_empty_filter_returns_404(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/random?author=Nobody")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "no quotes match"}


def test_shuffle_returns_all_ids(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/shuffle")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body.keys()) == {"ids"}
    assert len(body["ids"]) == TOTAL_QUOTES
    assert len(set(body["ids"])) == TOTAL_QUOTES


def test_shuffle_respects_tag_filter(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/shuffle?tags=wisdom")
    assert resp.status_code == 200
    assert len(resp.get_json()["ids"]) == 4


def test_shuffle_empty_filter_returns_empty_list_not_404(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/shuffle?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == {"ids": []}
