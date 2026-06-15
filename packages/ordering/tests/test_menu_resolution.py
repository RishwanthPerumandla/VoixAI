"""Tests for robust menu item resolution.

Regression coverage for the bug where natural combo phrasings ("6 piece classic
combo") failed to resolve and the agent claimed the item was not on the menu.
"""

from __future__ import annotations

import pytest

from voix_ordering.menu import (
    MENU_ITEMS,
    _resolve_item_id,
    build_menu_for_prompt,
    category_summary,
    find_category,
    menu_overview_summary,
    suggest_item_names,
)


@pytest.mark.parametrize(
    ("phrase", "expected_item_id"),
    [
        # Exact display name / alias still works.
        ("6 Piece Classic Wing Combo", "combo_classic_6"),
        ("6 piece classic combo", "combo_classic_6"),
        # Natural phrasings that previously failed.
        ("classic combo six piece", "combo_classic_6"),
        ("ten piece classic combo", "combo_classic_10"),
        ("10 piece classic combo", "combo_classic_10"),
        ("six piece boneless combo", "combo_boneless_6"),
        ("6 boneless combo", "combo_boneless_6"),
        # Plain wings by size.
        ("10 boneless wings", "boneless_10"),
        ("ten boneless wings", "boneless_10"),
        # Lenient size default backed by an explicit alias.
        ("classic combo", "combo_classic_6"),
        ("boneless combo", "combo_boneless_6"),
    ],
)
def test_resolve_item_id_handles_natural_phrasings(phrase: str, expected_item_id: str) -> None:
    assert _resolve_item_id(phrase) == expected_item_id


def test_resolve_item_id_does_not_cross_sizes() -> None:
    # A requested size must never resolve to a different size.
    assert _resolve_item_id("10 piece classic combo") != "combo_classic_6"
    assert _resolve_item_id("8 boneless wings") == "boneless_8"
    assert _resolve_item_id("20 boneless wings") == "boneless_20"


def test_resolve_item_id_returns_none_for_ambiguous_size() -> None:
    # "classic wings" without a size could be any of 6/8/10/15/20/... — ask, don't guess.
    assert _resolve_item_id("classic wings") is None


def test_resolve_item_id_returns_none_for_off_menu_and_non_items() -> None:
    assert _resolve_item_id("pizza") is None
    assert _resolve_item_id("lemon pepper") is None  # a flavor, not an item
    assert _resolve_item_id("") is None


def test_suggest_item_names_returns_relevant_options() -> None:
    suggestions = suggest_item_names("classic combo", limit=3)
    assert suggestions
    assert any("Classic Wing Combo" in name for name in suggestions)


@pytest.mark.parametrize(
    ("phrase", "expected_category"),
    [
        ("combos", "Wing Combos"),
        ("combo", "Wing Combos"),
        ("boneless", "Boneless Wings"),
        ("tenders", "Crispy Tenders"),
        ("desserts", "Desserts"),
        ("drinks", "Drinks"),
        ("group packs", "Group Packs"),
        ("Wing Combos", "Wing Combos"),  # exact still works
    ],
)
def test_find_category_matches_spoken_names(phrase: str, expected_category: str) -> None:
    assert find_category(phrase) == expected_category


def test_find_category_returns_none_when_ambiguous() -> None:
    # "wings" spans Wing Combos, Wings By The Piece, and Boneless Wings.
    assert find_category("wings") is None


def test_category_summary_lists_combos() -> None:
    summary = category_summary("combos")
    assert "Wing Combos options:" in summary
    assert "6 Piece Classic Wing Combo" in summary


def test_category_summary_falls_back_to_overview_when_unspecific() -> None:
    # An ambiguous or unknown category never claims "not available".
    assert category_summary("wings") == menu_overview_summary()
    assert category_summary("xyzzy") == menu_overview_summary()
    assert "Available categories are" in menu_overview_summary()


def test_build_menu_for_prompt_lists_every_item() -> None:
    # The menu given to the LLM must stay complete and in sync with the data.
    menu_text = build_menu_for_prompt()
    for item in MENU_ITEMS.values():
        assert item.display_name in menu_text
    assert "Flavors:" in menu_text
    assert "Combos include one flavor" in menu_text
