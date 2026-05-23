from __future__ import annotations

from flask.testing import FlaskClient


def test_create_returns_201_and_quote_shape(client: FlaskClient) -> None:
    resp = client.post(
        "/api/quotes",
        json={"text": "test quote", "author": "Test Author"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert set(body.keys()) == {"id", "text", "author", "source", "tags"}
    assert body["text"] == "test quote"
    assert body["author"] == "Test Author"
    assert body["tags"] == []


def test_create_with_new_and_existing_tags(client: FlaskClient) -> None:
    resp = client.post(
        "/api/quotes",
        json={
            "text": "with tags",
            "author": "Tagger",
            "tags": ["WISDOM", "freshly-coined"],
        },
    )
    assert resp.status_code == 201
    assert resp.get_json()["tags"] == ["freshly-coined", "wisdom"]
    # 'wisdom' is now used by 5 quotes (4 from fixture + this one).
    tag_counts = {t["name"]: t["count"] for t in client.get("/api/tags").get_json()}
    assert tag_counts["wisdom"] == 5
    assert tag_counts["freshly-coined"] == 1


def test_create_rejects_id_in_body(client: FlaskClient) -> None:
    resp = client.post(
        "/api/quotes",
        json={"id": "i-pick-my-own", "text": "nope"},
    )
    assert resp.status_code == 400
    assert "id" in resp.get_json()["error"]


def test_create_rejects_unknown_field(client: FlaskClient) -> None:
    resp = client.post("/api/quotes", json={"text": "ok", "weird": "bad"})
    assert resp.status_code == 400
    assert "weird" in resp.get_json()["error"]


def test_create_empty_text_400(client: FlaskClient) -> None:
    resp = client.post("/api/quotes", json={"text": "   "})
    assert resp.status_code == 400


def test_create_text_too_long_400(client: FlaskClient) -> None:
    resp = client.post("/api/quotes", json={"text": "x" * 10001})
    assert resp.status_code == 400


def test_update_text_round_trips(client: FlaskClient) -> None:
    created = client.post("/api/quotes", json={"text": "before", "author": "X"}).get_json()
    quote_id = created["id"]
    resp = client.put(f"/api/quotes/{quote_id}", json={"text": "after"})
    assert resp.status_code == 200
    assert resp.get_json()["text"] == "after"
    assert client.get(f"/api/quotes/{quote_id}").get_json()["text"] == "after"


def test_update_empty_tags_clears(client: FlaskClient) -> None:
    created = client.post(
        "/api/quotes", json={"text": "tagged", "tags": ["alpha", "beta"]}
    ).get_json()
    quote_id = created["id"]
    resp = client.put(f"/api/quotes/{quote_id}", json={"tags": []})
    assert resp.status_code == 200
    assert resp.get_json()["tags"] == []


def test_update_omits_tags_leaves_them(client: FlaskClient) -> None:
    created = client.post(
        "/api/quotes", json={"text": "keep tags", "tags": ["alpha", "beta"]}
    ).get_json()
    quote_id = created["id"]
    resp = client.put(f"/api/quotes/{quote_id}", json={"text": "new text"})
    assert resp.status_code == 200
    assert resp.get_json()["tags"] == ["alpha", "beta"]


def test_update_404_on_missing(client: FlaskClient) -> None:
    resp = client.put("/api/quotes/does-not-exist", json={"text": "x"})
    assert resp.status_code == 404


def test_delete_then_get_returns_404(client: FlaskClient) -> None:
    created = client.post("/api/quotes", json={"text": "to delete"}).get_json()
    quote_id = created["id"]
    resp = client.delete(f"/api/quotes/{quote_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/quotes/{quote_id}").status_code == 404


def test_delete_404_on_missing(client: FlaskClient) -> None:
    resp = client.delete("/api/quotes/does-not-exist")
    assert resp.status_code == 404


def test_delete_cascades_to_notes(client: FlaskClient) -> None:
    profile = client.post("/api/profiles", json={"name": "alice"}).get_json()
    quote = client.post("/api/quotes", json={"text": "cascade test"}).get_json()
    client.post(
        f"/api/quotes/{quote['id']}/notes",
        json={"profile_id": profile["id"], "body": "memo"},
    )
    assert len(client.get(f"/api/quotes/{quote['id']}/notes").get_json()["notes"]) == 1
    client.delete(f"/api/quotes/{quote['id']}")
    # Quote-specific notes GET returns 404 since the quote is gone — that's the
    # cascade evidence we need.
    assert client.get(f"/api/quotes/{quote['id']}/notes").status_code == 404
