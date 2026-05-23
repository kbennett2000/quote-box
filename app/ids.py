"""Slug-ID generation for quotes.

Format: ``{author-slug}-{first-5-words-of-text-slug}``. On collision with an
existing ID, a numeric suffix is appended (``-2``, ``-3``, ...). The seed file
already contains one such collision (``galileo-galilei-you-cannot-teach-a-man-2``).

Pure functions only — no DB dependency. The caller passes the set of existing
IDs and decides what to do with the result.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WORD = re.compile(r"\w+")
_ANONYMOUS = "anonymous"


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    return _NON_ALNUM.sub("-", stripped.lower()).strip("-")


def _first_words(text: str, n: int) -> list[str]:
    return _WORD.findall(text.lower())[:n]


def generate_slug(author: str | None, text: str, existing_ids: Iterable[str]) -> str:
    author_part = _slugify(author) if author else ""
    if not author_part:
        author_part = _ANONYMOUS
    text_part = _slugify(" ".join(_first_words(text, 5)))
    base = f"{author_part}-{text_part}" if text_part else author_part

    taken = set(existing_ids)
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"
