from __future__ import annotations

from flask.testing import FlaskClient


def test_list_profiles_empty(client: FlaskClient) -> None:
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.get_json() == {"profiles": []}


def test_create_profile_returns_201(client: FlaskClient) -> None:
    resp = client.post("/api/profiles", json={"name": "alice"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert set(body.keys()) == {"id", "name", "created_at"}
    assert body["name"] == "alice"


def test_create_profile_collision_409(client: FlaskClient) -> None:
    client.post("/api/profiles", json={"name": "alice"})
    resp = client.post("/api/profiles", json={"name": "alice"})
    assert resp.status_code == 409


def test_create_profile_missing_name_400(client: FlaskClient) -> None:
    resp = client.post("/api/profiles", json={})
    assert resp.status_code == 400


def test_create_profile_empty_name_400(client: FlaskClient) -> None:
    resp = client.post("/api/profiles", json={"name": "   "})
    assert resp.status_code == 400


def test_list_profiles_after_create(client: FlaskClient) -> None:
    a = client.post("/api/profiles", json={"name": "alice"}).get_json()
    b = client.post("/api/profiles", json={"name": "bob"}).get_json()
    listed = client.get("/api/profiles").get_json()["profiles"]
    assert [p["name"] for p in listed] == ["alice", "bob"]
    assert [p["id"] for p in listed] == [a["id"], b["id"]]


def test_delete_profile_204(client: FlaskClient) -> None:
    profile = client.post("/api/profiles", json={"name": "alice"}).get_json()
    resp = client.delete(f"/api/profiles/{profile['id']}")
    assert resp.status_code == 204
    assert client.get("/api/profiles").get_json() == {"profiles": []}


def test_delete_profile_404_on_missing(client: FlaskClient) -> None:
    resp = client.delete("/api/profiles/999999")
    assert resp.status_code == 404
