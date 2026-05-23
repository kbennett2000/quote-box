from __future__ import annotations

import pytest
from flask.testing import FlaskClient

QUOTE_ID = "marcus-aurelius-the-happiness-of-your-life"


@pytest.fixture
def profile_a(client: FlaskClient) -> int:
    return int(client.post("/api/profiles", json={"name": "alice"}).get_json()["id"])


@pytest.fixture
def profile_b(client: FlaskClient) -> int:
    return int(client.post("/api/profiles", json={"name": "bob"}).get_json()["id"])


def test_list_notes_empty(client: FlaskClient) -> None:
    resp = client.get(f"/api/quotes/{QUOTE_ID}/notes")
    assert resp.status_code == 200
    assert resp.get_json() == {"notes": []}


def test_list_notes_missing_quote_404(client: FlaskClient) -> None:
    resp = client.get("/api/quotes/no-such-quote/notes")
    assert resp.status_code == 404


def test_create_note_returns_201_with_profile_name(client: FlaskClient, profile_a: int) -> None:
    resp = client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile_a, "body": "great quote"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["profile_id"] == profile_a
    assert body["profile_name"] == "alice"
    assert body["body"] == "great quote"


def test_create_note_invalid_profile_id_400(client: FlaskClient) -> None:
    resp = client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": 999999, "body": "ghost"},
    )
    assert resp.status_code == 400


def test_create_note_against_missing_quote_404(client: FlaskClient, profile_a: int) -> None:
    resp = client.post(
        "/api/quotes/no-such-quote/notes",
        json={"profile_id": profile_a, "body": "lost"},
    )
    assert resp.status_code == 404


def test_update_note_happy_path(client: FlaskClient, profile_a: int) -> None:
    created = client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile_a, "body": "first"},
    ).get_json()
    resp = client.put(
        f"/api/notes/{created['id']}",
        json={"profile_id": profile_a, "body": "edited"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["body"] == "edited"


def test_update_note_404_if_missing(client: FlaskClient, profile_a: int) -> None:
    resp = client.put(
        "/api/notes/999999",
        json={"profile_id": profile_a, "body": "x"},
    )
    assert resp.status_code == 404


def test_update_note_403_on_ownership_mismatch(
    client: FlaskClient, profile_a: int, profile_b: int
) -> None:
    created = client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile_a, "body": "mine"},
    ).get_json()
    resp = client.put(
        f"/api/notes/{created['id']}",
        json={"profile_id": profile_b, "body": "stolen"},
    )
    assert resp.status_code == 403


def test_delete_note_204(client: FlaskClient, profile_a: int) -> None:
    created = client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile_a, "body": "to delete"},
    ).get_json()
    resp = client.delete(f"/api/notes/{created['id']}?profile_id={profile_a}")
    assert resp.status_code == 204
    assert client.get(f"/api/quotes/{QUOTE_ID}/notes").get_json()["notes"] == []


def test_delete_note_404_if_missing(client: FlaskClient, profile_a: int) -> None:
    resp = client.delete(f"/api/notes/999999?profile_id={profile_a}")
    assert resp.status_code == 404


def test_delete_note_403_on_ownership_mismatch(
    client: FlaskClient, profile_a: int, profile_b: int
) -> None:
    created = client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile_a, "body": "mine"},
    ).get_json()
    resp = client.delete(f"/api/notes/{created['id']}?profile_id={profile_b}")
    assert resp.status_code == 403


def test_delete_note_400_if_profile_id_missing(client: FlaskClient) -> None:
    resp = client.delete("/api/notes/1")
    assert resp.status_code == 400


def test_profile_delete_cascades_to_notes(client: FlaskClient, profile_a: int) -> None:
    client.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile_a, "body": "vanish me"},
    )
    assert len(client.get(f"/api/quotes/{QUOTE_ID}/notes").get_json()["notes"]) == 1
    client.delete(f"/api/profiles/{profile_a}")
    assert client.get(f"/api/quotes/{QUOTE_ID}/notes").get_json()["notes"] == []
