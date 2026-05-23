from __future__ import annotations

from collections.abc import Iterable

from flask.testing import FlaskClient


def _has_cookie(headers: Iterable[tuple[str, str]], name: str) -> bool:
    return any(h.lower() == "set-cookie" and v.split("=", 1)[0] == name for h, v in headers)


def _cookie_cleared(headers: Iterable[tuple[str, str]], name: str) -> bool:
    for h, v in headers:
        if h.lower() != "set-cookie":
            continue
        if v.split("=", 1)[0] != name:
            continue
        # Werkzeug emits Expires=Thu, 01-Jan-1970 ... + Max-Age=0 on delete.
        if "max-age=0" in v.lower() or "1970" in v:
            return True
    return False


def test_get_profile_no_cookie_renders_picker(client: FlaskClient) -> None:
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Who" in body and "reading" in body


def test_get_profile_with_valid_cookie_redirects(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_post_select_new_name_sets_cookie_and_redirects(client: FlaskClient) -> None:
    resp = client.post("/profile/select", data={"name": "alice", "next": "/"})
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"
    assert _has_cookie(resp.headers.items(), "quote_box_profile_id")
    follow = client.get("/")
    assert follow.status_code == 200


def test_post_select_duplicate_name_reraises_picker_with_error(client: FlaskClient) -> None:
    client.post("/profile/select", data={"name": "alice", "next": "/"})
    # Drop the freshly set cookie so the duplicate-create path runs without
    # auto-redirecting from /profile.
    client.delete_cookie("quote_box_profile_id")
    resp = client.post("/profile/select", data={"name": "alice", "next": "/"})
    assert resp.status_code == 400
    body = resp.get_data(as_text=True)
    assert "already exists" in body
    assert 'value="alice"' in body  # name pre-filled


def test_post_select_existing_id_sets_cookie(client: FlaskClient) -> None:
    profile = client.post("/api/profiles", json={"name": "bob"}).get_json()
    resp = client.post(
        "/profile/select",
        data={"existing_id": str(profile["id"]), "next": "/"},
    )
    assert resp.status_code == 302
    assert _has_cookie(resp.headers.items(), "quote_box_profile_id")


def test_post_select_unknown_existing_id_reraises_picker(client: FlaskClient) -> None:
    resp = client.post("/profile/select", data={"existing_id": "999999", "next": "/"})
    assert resp.status_code == 400
    assert "no longer exists" in resp.get_data(as_text=True)


def test_post_switch_clears_cookie(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.post("/profile/switch")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/profile"
    assert _cookie_cleared(resp.headers.items(), "quote_box_profile_id")


def test_stale_cookie_is_cleared_and_redirects_to_picker(client: FlaskClient) -> None:
    profile = client.post("/api/profiles", json={"name": "ghost"}).get_json()
    client.delete(f"/api/profiles/{profile['id']}")
    client.set_cookie("quote_box_profile_id", str(profile["id"]))
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/profile?next=")
    assert _cookie_cleared(resp.headers.items(), "quote_box_profile_id")


def test_next_protocol_relative_is_sanitized(client: FlaskClient) -> None:
    resp = client.post(
        "/profile/select",
        data={"name": "mallory", "next": "//evil.example.com/pwn"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_next_external_is_sanitized(client: FlaskClient) -> None:
    resp = client.post(
        "/profile/select",
        data={"name": "mallory2", "next": "https://evil.example.com/"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_api_endpoints_do_not_redirect_without_cookie(client: FlaskClient) -> None:
    assert client.get("/api/quotes").status_code == 200
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/tags").status_code == 200
