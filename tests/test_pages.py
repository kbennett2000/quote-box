from __future__ import annotations

from flask.testing import FlaskClient


def test_browse_returns_200_and_renders_quotes(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Marcus Aurelius" in body
    assert "Epicurus" in body


def test_browse_with_tag_filter(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.get("/?tags=wisdom")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Marcus Aurelius and Seneca both have the wisdom tag.
    assert "Marcus Aurelius" in body
    assert "Seneca" in body
    # Epicurus is tagged death + philosophy, not wisdom.
    assert "Death is nothing to us" not in body


def test_browse_with_invalid_page_falls_back_to_1(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.get("/?page=abc")
    assert resp.status_code == 200
    assert "Page 1 of" in resp.get_data(as_text=True)


def test_browse_links_self_hosted_assets(client_with_profile: FlaskClient) -> None:
    body = client_with_profile.get("/").get_data(as_text=True)
    assert "static/css/app.css" in body
    assert "static/js/browse.js" in body


def test_base_css_has_self_hosted_font_face(client: FlaskClient) -> None:
    # The CSS file is the source of truth for offline-only fonts.
    resp = client.get("/static/css/base.css")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "@font-face" in text
    assert "fonts/crimson-pro.woff2" in text
    assert "fonts/inter.woff2" in text
    # And absolutely no third-party origins.
    assert "fonts.googleapis.com" not in text
    assert "fonts.gstatic.com" not in text


def test_quote_detail_renders(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.get("/quotes/epicurus-death-is-nothing-to-us")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Death is nothing to us" in body
    assert "Epicurus" in body


def test_quote_detail_tags_link_to_browse(client_with_profile: FlaskClient) -> None:
    body = client_with_profile.get("/quotes/epicurus-death-is-nothing-to-us").get_data(as_text=True)
    assert 'href="/?tags=death"' in body
    assert 'href="/?tags=philosophy"' in body


def test_quote_detail_404(client_with_profile: FlaskClient) -> None:
    resp = client_with_profile.get("/quotes/does-not-exist")
    assert resp.status_code == 404


# --- profile-required redirects ---


def test_browse_without_profile_redirects_to_picker(client: FlaskClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/profile?next=")


def test_quote_detail_without_profile_redirects(client: FlaskClient) -> None:
    resp = client.get("/quotes/epicurus-death-is-nothing-to-us")
    assert resp.status_code == 302
    assert "/profile?next=" in resp.headers["Location"]
    assert "%2Fquotes%2Fepicurus" in resp.headers["Location"]


def test_browse_shows_profile_badge_in_nav(client_with_profile: FlaskClient) -> None:
    body = client_with_profile.get("/").get_data(as_text=True)
    assert 'class="profile-badge">tester</span>' in body
    assert "/profile/switch" in body


# --- notes section on detail page ---

QUOTE_ID = "epicurus-death-is-nothing-to-us"


def test_quote_detail_has_notes_section_and_add_form(
    client_with_profile: FlaskClient,
) -> None:
    body = client_with_profile.get(f"/quotes/{QUOTE_ID}").get_data(as_text=True)
    assert 'class="notes-section"' in body
    assert 'id="add-note-form"' in body
    assert "data-current-profile-id=" in body
    assert "No notes yet." in body  # empty state


def test_quote_detail_renders_existing_notes(
    client_with_profile: FlaskClient, profile: dict[str, object]
) -> None:
    client_with_profile.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": profile["id"], "body": "memorable line"},
    )
    body = client_with_profile.get(f"/quotes/{QUOTE_ID}").get_data(as_text=True)
    assert "memorable line" in body
    assert "tester" in body
    assert 'class="note note--mine"' in body
    assert 'class="note-edit"' in body
    assert 'class="note-delete"' in body
    assert "No notes yet." not in body


def test_quote_detail_marks_other_profile_notes_read_only(
    client_with_profile: FlaskClient, profile: dict[str, object]
) -> None:
    other = client_with_profile.post("/api/profiles", json={"name": "bystander"}).get_json()
    client_with_profile.post(
        f"/api/quotes/{QUOTE_ID}/notes",
        json={"profile_id": other["id"], "body": "by someone else"},
    )
    body = client_with_profile.get(f"/quotes/{QUOTE_ID}").get_data(as_text=True)
    assert "by someone else" in body
    assert "bystander" in body
    # The note exists but without action buttons for the current viewer.
    li_index = body.find("by someone else")
    snippet = body[max(0, li_index - 400) : li_index + 400]
    assert "note--mine" not in snippet
    assert "note-edit" not in snippet
    assert "note-delete" not in snippet
