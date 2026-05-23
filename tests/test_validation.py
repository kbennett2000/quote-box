from __future__ import annotations

import pytest

from app.validation import (
    ValidationError,
    normalize_tag_name,
    optional_str,
    parse_tags,
    reject_unknown_fields,
    require_int,
    require_str,
)

# require_str ----------------------------------------------------------------


def test_require_str_happy_path() -> None:
    assert require_str({"text": "  hello  "}, "text", max_len=100) == "hello"


def test_require_str_missing_key() -> None:
    with pytest.raises(ValidationError, match="text is required"):
        require_str({}, "text", max_len=100)


def test_require_str_wrong_type() -> None:
    with pytest.raises(ValidationError, match="text must be a string"):
        require_str({"text": 5}, "text", max_len=100)


def test_require_str_empty_after_trim() -> None:
    with pytest.raises(ValidationError, match="at least 1"):
        require_str({"text": "   "}, "text", max_len=100)


def test_require_str_too_long() -> None:
    with pytest.raises(ValidationError, match="at most 5"):
        require_str({"text": "hello!"}, "text", max_len=5)


# optional_str --------------------------------------------------------------


def test_optional_str_missing_returns_none() -> None:
    assert optional_str({}, "author", max_len=100) is None


def test_optional_str_null_returns_none() -> None:
    assert optional_str({"author": None}, "author", max_len=100) is None


def test_optional_str_empty_after_trim_returns_none() -> None:
    assert optional_str({"author": "   "}, "author", max_len=100) is None


def test_optional_str_present_trims() -> None:
    assert optional_str({"author": "  Plato  "}, "author", max_len=100) == "Plato"


def test_optional_str_too_long_raises() -> None:
    with pytest.raises(ValidationError, match="at most 3"):
        optional_str({"author": "abcd"}, "author", max_len=3)


# require_int ---------------------------------------------------------------


def test_require_int_happy_path() -> None:
    assert require_int({"profile_id": 7}, "profile_id") == 7


def test_require_int_missing() -> None:
    with pytest.raises(ValidationError, match="profile_id is required"):
        require_int({}, "profile_id")


def test_require_int_wrong_type() -> None:
    with pytest.raises(ValidationError, match="profile_id must be an integer"):
        require_int({"profile_id": "7"}, "profile_id")


def test_require_int_rejects_bool() -> None:
    with pytest.raises(ValidationError, match="profile_id must be an integer"):
        require_int({"profile_id": True}, "profile_id")


# parse_tags ----------------------------------------------------------------


def test_parse_tags_missing_returns_none() -> None:
    assert parse_tags({}) is None


def test_parse_tags_empty_list() -> None:
    assert parse_tags({"tags": []}) == []


def test_parse_tags_lowercases_and_dedupes() -> None:
    assert parse_tags({"tags": ["Wisdom", " WISDOM ", "Truth"]}) == ["wisdom", "truth"]


def test_parse_tags_rejects_non_list() -> None:
    with pytest.raises(ValidationError, match="tags must be a list"):
        parse_tags({"tags": "wisdom"})


def test_parse_tags_rejects_too_long_element() -> None:
    with pytest.raises(ValidationError, match="at most 50"):
        parse_tags({"tags": ["x" * 51]})


def test_parse_tags_rejects_empty_element() -> None:
    with pytest.raises(ValidationError, match="at least 1"):
        parse_tags({"tags": ["  "]})


# normalize_tag_name --------------------------------------------------------


def test_normalize_tag_name_strips_and_lowers() -> None:
    assert normalize_tag_name("  Wisdom  ") == "wisdom"


def test_normalize_tag_name_empty_raises() -> None:
    with pytest.raises(ValidationError, match="at least 1"):
        normalize_tag_name("   ")


def test_normalize_tag_name_too_long_raises() -> None:
    with pytest.raises(ValidationError, match="at most 50"):
        normalize_tag_name("x" * 51)


# reject_unknown_fields -----------------------------------------------------


def test_reject_unknown_fields_passes_when_subset() -> None:
    reject_unknown_fields({"text": "ok"}, {"text", "author"})


def test_reject_unknown_fields_raises_on_extras() -> None:
    with pytest.raises(ValidationError, match="unknown field"):
        reject_unknown_fields({"text": "ok", "weird": "bad"}, {"text"})


def test_reject_unknown_fields_lists_all_extras_sorted() -> None:
    with pytest.raises(ValidationError, match="banana, zebra"):
        reject_unknown_fields({"text": "ok", "zebra": 1, "banana": 2}, {"text"})
