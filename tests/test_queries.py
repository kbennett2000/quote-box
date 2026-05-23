from __future__ import annotations

import sqlite3

from app.queries import (
    get_quote,
    list_authors_with_counts,
    list_quotes,
    list_tags_with_counts,
    random_quote,
    shuffle_ids,
)

# Constants tracking tests/fixtures/quotes_sample.json:
TOTAL_QUOTES = 12
TOTAL_TAGS = 10
NON_NULL_AUTHORS = 11


def test_list_quotes_no_filters(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db)
    assert total == TOTAL_QUOTES
    assert len(rows) == TOTAL_QUOTES
    # Sanity: every row has the expected keys and tags are sorted.
    for row in rows:
        assert set(row.keys()) == {"id", "text", "author", "source", "tags"}
        assert row["tags"] == sorted(row["tags"])


def test_list_quotes_pagination(seeded_db: sqlite3.Connection) -> None:
    page1, total1 = list_quotes(seeded_db, limit=5, offset=0)
    page2, total2 = list_quotes(seeded_db, limit=5, offset=5)
    assert total1 == total2 == TOTAL_QUOTES
    assert len(page1) == 5
    assert len(page2) == 5
    # No overlap between pages.
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})


def test_list_quotes_q_matches_text_case_insensitive(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, q="COURAGE")
    assert total == 1
    assert rows[0]["id"] == "anais-nin-life-shrinks-or-expands-in"


def test_list_quotes_q_matches_author(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, q="Mark")
    assert total == 1
    assert rows[0]["author"] == "Mark Twain"


def test_list_quotes_q_matches_source(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, q="Long")
    assert total == 1
    assert rows[0]["source"] == "A Long Essay"


def test_list_quotes_q_literal_percent_escapes(seeded_db: sqlite3.Connection) -> None:
    # Fixture contains no '%' character anywhere; if escaping is broken, '%'
    # would behave as the SQL wildcard and match everything.
    _, total = list_quotes(seeded_db, q="%")
    assert total == 0


def test_list_quotes_author_exact_match_is_case_sensitive(seeded_db: sqlite3.Connection) -> None:
    _, exact = list_quotes(seeded_db, author="Seneca")
    assert exact == 1
    _, lower = list_quotes(seeded_db, author="seneca")
    assert lower == 0


def test_list_quotes_tags_single(seeded_db: sqlite3.Connection) -> None:
    _, total = list_quotes(seeded_db, tags=["wisdom"])
    assert total == 4


def test_list_quotes_tags_and_semantics(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, tags=["wisdom", "life"])
    assert total == 1
    assert rows[0]["id"] == "marcus-aurelius-the-happiness-of-your-life"


def test_list_quotes_tags_and_semantics_two(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, tags=["wisdom", "doubt"])
    assert total == 1
    assert rows[0]["id"] == "andre-gide-trust-those-who-seek-the"


def test_list_quotes_tags_deduplicate(seeded_db: sqlite3.Connection) -> None:
    _, total = list_quotes(seeded_db, tags=["wisdom", "wisdom"])
    assert total == 4


def test_list_quotes_combined_filters(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, q="Trust", tags=["doubt"], author="André Gide")
    assert total == 1
    assert rows[0]["id"] == "andre-gide-trust-those-who-seek-the"


def test_list_quotes_empty_result(seeded_db: sqlite3.Connection) -> None:
    rows, total = list_quotes(seeded_db, author="Nobody")
    assert rows == []
    assert total == 0


def test_get_quote_found(seeded_db: sqlite3.Connection) -> None:
    row = get_quote(seeded_db, "epicurus-death-is-nothing-to-us")
    assert row is not None
    assert row["author"] == "Epicurus"
    assert row["tags"] == ["death", "philosophy"]


def test_get_quote_not_found(seeded_db: sqlite3.Connection) -> None:
    assert get_quote(seeded_db, "nope") is None


def test_random_quote_respects_author_filter(seeded_db: sqlite3.Connection) -> None:
    row = random_quote(seeded_db, author="Seneca")
    assert row is not None
    assert row["author"] == "Seneca"


def test_random_quote_empty_filter_returns_none(seeded_db: sqlite3.Connection) -> None:
    assert random_quote(seeded_db, author="Nobody") is None


def test_shuffle_ids_returns_all_unique(seeded_db: sqlite3.Connection) -> None:
    ids = shuffle_ids(seeded_db)
    assert len(ids) == TOTAL_QUOTES
    assert len(set(ids)) == TOTAL_QUOTES


def test_shuffle_ids_with_tag_filter(seeded_db: sqlite3.Connection) -> None:
    ids = shuffle_ids(seeded_db, tags=["wisdom"])
    assert len(ids) == 4
    assert len(set(ids)) == 4


def test_list_tags_with_counts_sort_and_shape(seeded_db: sqlite3.Connection) -> None:
    tags = list_tags_with_counts(seeded_db)
    assert len(tags) == TOTAL_TAGS
    assert tags[0] == {"name": "wisdom", "count": 4}
    # Count=2 group ordered alphabetically: action, courage, life, philosophy
    count_2 = [t for t in tags if t["count"] == 2]
    assert [t["name"] for t in count_2] == ["action", "courage", "life", "philosophy"]
    # Sort is strictly non-increasing on count.
    counts = [t["count"] for t in tags]
    assert counts == sorted(counts, reverse=True)


def test_list_authors_with_counts_excludes_null(seeded_db: sqlite3.Connection) -> None:
    authors = list_authors_with_counts(seeded_db)
    assert len(authors) == NON_NULL_AUTHORS
    assert all(a["count"] == 1 for a in authors)
    # All count=1, so order is purely alphabetical (binary collation).
    names = [a["name"] for a in authors]
    assert names == sorted(names)
    assert None not in names
