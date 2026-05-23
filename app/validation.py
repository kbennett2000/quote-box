"""Body-parsing helpers for write endpoints.

Each helper raises ``ValidationError`` on bad input; route handlers catch the
exception and return ``({"error": <message>}, 400)``. Centralising the rules
here keeps validation consistent across POST/PUT bodies and ensures tag
normalisation (lowercase + trim) is identical at create and rename time.
"""

from __future__ import annotations

from typing import Any

_MAX_TAG_LEN = 50


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def reject_unknown_fields(body: dict[str, Any], allowed: set[str]) -> None:
    extras = sorted(set(body.keys()) - allowed)
    if extras:
        raise ValidationError(f"unknown field(s): {', '.join(extras)}")


def require_str(
    body: dict[str, Any],
    key: str,
    *,
    min_len: int = 1,
    max_len: int,
) -> str:
    if key not in body:
        raise ValidationError(f"{key} is required")
    raw = body[key]
    if not isinstance(raw, str):
        raise ValidationError(f"{key} must be a string")
    value = raw.strip()
    if len(value) < min_len:
        raise ValidationError(f"{key} must be at least {min_len} character(s)")
    if len(value) > max_len:
        raise ValidationError(f"{key} must be at most {max_len} character(s)")
    return value


def optional_str(body: dict[str, Any], key: str, *, max_len: int) -> str | None:
    if key not in body:
        return None
    raw = body[key]
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValidationError(f"{key} must be a string or null")
    value = raw.strip()
    if not value:
        return None
    if len(value) > max_len:
        raise ValidationError(f"{key} must be at most {max_len} character(s)")
    return value


def require_int(body: dict[str, Any], key: str) -> int:
    if key not in body:
        raise ValidationError(f"{key} is required")
    raw = body[key]
    # bool is a subclass of int; reject explicitly so True/False don't sneak in.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValidationError(f"{key} must be an integer")
    return raw


def normalize_tag_name(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValidationError("tag must be a string")
    value = raw.strip().lower()
    if not value:
        raise ValidationError("tag must be at least 1 character")
    if len(value) > _MAX_TAG_LEN:
        raise ValidationError(f"tag must be at most {_MAX_TAG_LEN} characters")
    return value


def parse_tags(body: dict[str, Any], key: str = "tags") -> list[str] | None:
    if key not in body:
        return None
    raw = body[key]
    if not isinstance(raw, list):
        raise ValidationError(f"{key} must be a list")
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        name = normalize_tag_name(item)
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result
