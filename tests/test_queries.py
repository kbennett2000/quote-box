from __future__ import annotations

import sqlite3

import pytest

from app.queries import (
    ConflictError,
    delete_note,
    delete_profile,
    delete_quote,
    delete_tag,
    get_note,
    get_quote,
    get_tag,
    insert_note,
    insert_profile,
    insert_quote,
    list_authors_with_counts,
    list_notes_for_quote,
    list_profiles,
    list_quotes,
    list_tags_with_counts,
    random_quote,
    rename_tag,
    shuffle_ids,
    update_note,
    update_quote,
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
    assert tags[0]["name"] == "wisdom"
    assert tags[0]["count"] == 4
    assert isinstance(tags[0]["id"], int)
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


# ---------------------------------------------------------------------------
# Write-side query tests
# ---------------------------------------------------------------------------


def test_insert_quote_with_new_and_existing_tags(seeded_db: sqlite3.Connection) -> None:
    row = insert_quote(
        seeded_db,
        text="The unexamined life is not worth living.",
        author="Socrates",
        source=None,
        tags=["wisdom", "newly-coined"],  # wisdom exists; newly-coined is new
    )
    assert row["id"] == "socrates-the-unexamined-life-is-not"
    assert row["tags"] == ["newly-coined", "wisdom"]
    # 'newly-coined' inserted into tags table.
    assert (
        seeded_db.execute(
            "SELECT COUNT(*) AS n FROM tags WHERE name = ?", ("newly-coined",)
        ).fetchone()["n"]
        == 1
    )


def test_insert_quote_slug_collision_appends_suffix(seeded_db: sqlite3.Connection) -> None:
    first = insert_quote(seeded_db, text="Hello world", author="Alice", source=None, tags=None)
    second = insert_quote(seeded_db, text="Hello world", author="Alice", source=None, tags=None)
    assert first["id"] == "alice-hello-world"
    assert second["id"] == "alice-hello-world-2"


def test_update_quote_text_only_leaves_tags(seeded_db: sqlite3.Connection) -> None:
    before = get_quote(seeded_db, "seneca-luck-is-what-happens-when")
    assert before is not None
    updated = update_quote(
        seeded_db, "seneca-luck-is-what-happens-when", {"text": "Luck favors the prepared."}
    )
    assert updated is not None
    assert updated["text"] == "Luck favors the prepared."
    assert updated["tags"] == before["tags"]


def test_update_quote_empty_tags_clears_them(seeded_db: sqlite3.Connection) -> None:
    updated = update_quote(seeded_db, "marcus-aurelius-the-happiness-of-your-life", {"tags": []})
    assert updated is not None
    assert updated["tags"] == []


def test_update_quote_returns_none_for_missing(seeded_db: sqlite3.Connection) -> None:
    assert update_quote(seeded_db, "no-such-quote", {"text": "x"}) is None


def test_delete_quote_cascades(seeded_db: sqlite3.Connection) -> None:
    # Seed a profile + note + tag attachment on a known quote.
    profile = insert_profile(seeded_db, "alice")
    quote_id = "marcus-aurelius-the-happiness-of-your-life"
    insert_note(seeded_db, quote_id=quote_id, profile_id=profile["id"], body="memorable")

    assert delete_quote(seeded_db, quote_id) is True
    assert get_quote(seeded_db, quote_id) is None
    assert (
        seeded_db.execute(
            "SELECT COUNT(*) AS n FROM notes WHERE quote_id = ?", (quote_id,)
        ).fetchone()["n"]
        == 0
    )
    assert (
        seeded_db.execute(
            "SELECT COUNT(*) AS n FROM quote_tags WHERE quote_id = ?", (quote_id,)
        ).fetchone()["n"]
        == 0
    )


def test_delete_quote_missing_returns_false(seeded_db: sqlite3.Connection) -> None:
    assert delete_quote(seeded_db, "no-such-quote") is False


def test_rename_tag_happy_path(seeded_db: sqlite3.Connection) -> None:
    wisdom = seeded_db.execute("SELECT id FROM tags WHERE name = 'wisdom'").fetchone()
    renamed = rename_tag(seeded_db, int(wisdom["id"]), "sagacity")
    assert renamed is not None
    assert renamed["name"] == "sagacity"


def test_rename_tag_to_existing_raises_conflict(seeded_db: sqlite3.Connection) -> None:
    wisdom = seeded_db.execute("SELECT id FROM tags WHERE name = 'wisdom'").fetchone()
    with pytest.raises(ConflictError):
        rename_tag(seeded_db, int(wisdom["id"]), "life")


def test_rename_tag_idempotent_to_same_name(seeded_db: sqlite3.Connection) -> None:
    wisdom = seeded_db.execute("SELECT id FROM tags WHERE name = 'wisdom'").fetchone()
    result = rename_tag(seeded_db, int(wisdom["id"]), "wisdom")
    assert result == {"id": int(wisdom["id"]), "name": "wisdom"}


def test_rename_tag_missing_returns_none(seeded_db: sqlite3.Connection) -> None:
    assert rename_tag(seeded_db, 999_999, "anything") is None


def test_delete_tag_cascades_to_quote_tags_only(seeded_db: sqlite3.Connection) -> None:
    wisdom = seeded_db.execute("SELECT id FROM tags WHERE name = 'wisdom'").fetchone()
    assert delete_tag(seeded_db, int(wisdom["id"])) is True
    # The quote itself still exists with other tags intact.
    quote = get_quote(seeded_db, "marcus-aurelius-the-happiness-of-your-life")
    assert quote is not None
    assert "wisdom" not in quote["tags"]
    assert "life" in quote["tags"]


def test_insert_profile_collision_raises(seeded_db: sqlite3.Connection) -> None:
    insert_profile(seeded_db, "kasey")
    with pytest.raises(ConflictError):
        insert_profile(seeded_db, "kasey")


def test_list_profiles_after_inserts(seeded_db: sqlite3.Connection) -> None:
    a = insert_profile(seeded_db, "alice")
    b = insert_profile(seeded_db, "bob")
    profiles = list_profiles(seeded_db)
    assert [p["name"] for p in profiles] == ["alice", "bob"]
    assert profiles[0]["id"] == a["id"]
    assert profiles[1]["id"] == b["id"]


def test_delete_profile_cascades_to_notes(seeded_db: sqlite3.Connection) -> None:
    profile = insert_profile(seeded_db, "alice")
    quote_id = "marcus-aurelius-the-happiness-of-your-life"
    insert_note(seeded_db, quote_id=quote_id, profile_id=profile["id"], body="hi")
    assert delete_profile(seeded_db, profile["id"]) is True
    assert list_notes_for_quote(seeded_db, quote_id) == []


def test_notes_full_lifecycle_and_ordering(seeded_db: sqlite3.Connection) -> None:
    profile = insert_profile(seeded_db, "alice")
    quote_id = "marcus-aurelius-the-happiness-of-your-life"
    n1 = insert_note(seeded_db, quote_id=quote_id, profile_id=profile["id"], body="first")
    n2 = insert_note(seeded_db, quote_id=quote_id, profile_id=profile["id"], body="second")
    notes = list_notes_for_quote(seeded_db, quote_id)
    assert [n["id"] for n in notes] == [n1["id"], n2["id"]]
    assert notes[0]["profile_name"] == "alice"

    updated = update_note(seeded_db, n1["id"], "first (edited)")
    assert updated is not None
    assert updated["body"] == "first (edited)"

    assert get_note(seeded_db, n2["id"]) is not None
    assert delete_note(seeded_db, n2["id"]) is True
    assert get_note(seeded_db, n2["id"]) is None
    assert len(list_notes_for_quote(seeded_db, quote_id)) == 1


def test_update_note_missing_returns_none(seeded_db: sqlite3.Connection) -> None:
    assert update_note(seeded_db, 999_999, "no-op") is None


def test_delete_note_missing_returns_false(seeded_db: sqlite3.Connection) -> None:
    assert delete_note(seeded_db, 999_999) is False
