"""Profile-cookie plumbing: read, validate, set, clear, and a route decorator.

The cookie holds the integer profile id as a string. No signing, no
encryption — LAN deployment, no threat model. Every HTML-page render
validates the id still exists in the DB; stale cookies (profile deleted)
are cleared transparently and the user is sent back to the picker.

API routes are never decorated — they accept profile_id in the request body
or query string and return 4xx if it's missing. Keeping auth-flow concerns
out of /api/* keeps the HTTP contract clean for non-browser clients.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, cast
from urllib.parse import quote_plus

from flask import g, redirect, request, url_for
from flask.typing import ResponseReturnValue
from werkzeug.wrappers import Response

from app import queries
from app.db import get_db
from app.queries import ProfileRow

COOKIE_NAME = "quote_box_profile_id"
COOKIE_MAX_AGE = 365 * 24 * 3600


def _g_profile_cached() -> tuple[bool, ProfileRow | None]:
    if "current_profile_cached" in g:
        return True, cast(ProfileRow | None, g.current_profile)
    return False, None


def load_current_profile() -> ProfileRow | None:
    cached, value = _g_profile_cached()
    if cached:
        return value

    raw = request.cookies.get(COOKIE_NAME)
    profile: ProfileRow | None = None
    if raw:
        try:
            pid = int(raw)
        except ValueError:
            pid = -1
        if pid > 0:
            profile = queries.get_profile(get_db(), pid)

    g.current_profile_cached = True
    g.current_profile = profile
    return profile


def safe_next(raw: str | None) -> str:
    if not raw:
        return "/"
    if not raw.startswith("/"):
        return "/"
    if raw.startswith("//"):
        return "/"
    return raw


def set_profile_cookie(response: Response, profile_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        str(profile_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        path="/",
    )


def clear_profile_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def require_profile(view: Callable[..., ResponseReturnValue]) -> Callable[..., ResponseReturnValue]:
    @functools.wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        if load_current_profile() is not None:
            return view(*args, **kwargs)
        next_url = request.full_path.rstrip("?") if request.path else "/"
        location = url_for("pages.profile") + "?next=" + quote_plus(next_url)
        resp = redirect(location)
        # Stale cookies (profile deleted) are wiped on the way out so the
        # user doesn't loop through the redirect forever.
        if request.cookies.get(COOKIE_NAME):
            clear_profile_cookie(resp)
        return resp

    return wrapper
