from __future__ import annotations

from app.ids import generate_slug


def test_slug_matches_seed_examples() -> None:
    # Reproduce IDs from the real data/quotes.json.
    assert (
        generate_slug(
            "Unknown",
            "A true man of realization can sit amidst the destruction of worlds and remain undisturbed",
            set(),
        )
        == "unknown-a-true-man-of-realization"
    )
    assert (
        generate_slug(
            "Socrates",
            "The only true wisdom is in knowing you know nothing.",
            set(),
        )
        == "socrates-the-only-true-wisdom-is"
    )
    assert (
        generate_slug(
            "Danta Young",
            "Man finds his purpose in isolation",
            set(),
        )
        == "danta-young-man-finds-his-purpose-in"
    )


def test_collision_appends_numeric_suffix() -> None:
    existing = {"galileo-galilei-you-cannot-teach-a-man"}
    second = generate_slug("Galileo Galilei", "You cannot teach a man anything", existing)
    assert second == "galileo-galilei-you-cannot-teach-a-man-2"
    existing.add(second)
    third = generate_slug("Galileo Galilei", "You cannot teach a man anything", existing)
    assert third == "galileo-galilei-you-cannot-teach-a-man-3"


def test_unicode_author_strips_accents() -> None:
    slug = generate_slug("André Gide", "Trust those who seek the truth", set())
    assert slug.startswith("andre-gide-")
    assert "é" not in slug


def test_short_text_does_not_crash() -> None:
    slug = generate_slug("Lao Tzu", "Be water", set())
    assert slug == "lao-tzu-be-water"


def test_empty_author_falls_back_to_anonymous() -> None:
    assert generate_slug(None, "Hello world", set()).startswith("anonymous-")
    assert generate_slug("", "Hello world", set()).startswith("anonymous-")
    assert generate_slug("   ", "Hello world", set()).startswith("anonymous-")


def test_accepts_any_iterable_of_existing_ids() -> None:
    # list
    assert generate_slug("A", "x y z", ["a-x-y-z"]) == "a-x-y-z-2"
    # set
    assert generate_slug("A", "x y z", {"a-x-y-z"}) == "a-x-y-z-2"
    # generator
    assert generate_slug("A", "x y z", (i for i in ["a-x-y-z"])) == "a-x-y-z-2"
