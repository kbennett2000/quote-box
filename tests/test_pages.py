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
