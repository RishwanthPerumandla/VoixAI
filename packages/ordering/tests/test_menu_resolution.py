"""Tests for robust menu item resolution.

Regression coverage for the bug where natural combo phrasings ("6 piece classic
combo") failed to resolve and the agent claimed the item was not on the menu.
"""

from __future__ import annotations

import pytest

from voix_ordering.menu import _resolve_item_id, suggest_item_names


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
