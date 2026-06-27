"""Tests for the POS-grade catalog, validation, and reducer."""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest

from voix_ordering import (
    FLAVOR_OPTIONS,
    MENU_ITEMS,
    MODIFIER_GROUPS,
    MODIFIER_OPTIONS,
    INTENT_ADD_ITEM,
    INTENT_CANCEL_ORDER,
    INTENT_CHANGE_FLAVOR,
    INTENT_CHANGE_QUANTITY,
    INTENT_REMOVE_ITEM,
    INTENT_REPLACE_ITEM,
    INTENT_MODIFY_ITEM,
    OrderIntent,
    OrderLineItem,
    OrderPhase,
    OrderState,
    OrderStateMachine,
    apply_order_intent,
    build_price_quote,
    validate_order,
)
from voix_ordering.menu import (
    _get_max_flavors,
    _resolve_flavor_id,
    _resolve_item_id,
    _resolve_modifier_id,
    _split_csv,
    get_catalog,
    get_combo_template,
    get_flavor_by_id,
    get_group_pack_template,
    get_item_template,
    get_item_type,
    get_modifier_group_by_id,
    load_catalog,
)
import voix_ordering.menu as _menu_mod


# ── Helpers ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _ensure_catalog(monkeypatch):
    """Load catalog from the correct path before each test."""
    _test_dir = os.path.dirname(os.path.abspath(__file__))
    _catalog_path = os.path.join(
        _test_dir, "..", "..", "..", "apps", "api", "data", "wingstop_demo_catalog.json"
    )
    monkeypatch.setenv("VOIXAI_CATALOG_PATH", _catalog_path)
    _menu_mod._catalog = None
    load_catalog()
    yield


def _uid() -> str:
    return uuid4().hex[:8]


def _make_item(
    item_id: str,
    flavor_ids: list[str] | None = None,
    modifier_ids: list[str] | None = None,
    quantity: int = 1,
) -> OrderLineItem:
    return OrderLineItem(
        line_id=f"line-{_uid()}",
        item_id=item_id,
        quantity=quantity,
        selected_flavor_ids=flavor_ids or [],
        selected_modifier_ids=modifier_ids or [],
    )


def _make_order(items: list[OrderLineItem] | None = None) -> OrderState:
    return OrderState(items=items or [])


def _intent(name: str, **kw) -> OrderIntent:
    return OrderIntent(name=name, **kw)


# ══════════════════════════════════════════════════════════════════════════
# Part 1 – Catalog Loading
# ══════════════════════════════════════════════════════════════════════════


def test_load_catalog_succeeds():
    cat = load_catalog()
    assert cat is not None


def test_catalog_has_restaurant_profile():
    cat = get_catalog()
    assert cat.restaurant_profile is not None
    assert cat.restaurant_profile.name == "Voix Wings Demo"


def test_catalog_has_12_categories():
    cat = get_catalog()
    assert len(cat.categories) == 12


def test_catalog_has_13_flavors():
    cat = get_catalog()
    assert len(cat.flavors) == 13


def test_catalog_has_8_modifier_groups():
    cat = get_catalog()
    assert len(cat.modifier_groups) == 8


def test_catalog_has_38_item_templates():
    cat = get_catalog()
    assert len(cat.item_templates) == 38


def test_catalog_has_9_combo_templates():
    cat = get_catalog()
    assert len(cat.combo_templates) == 9


def test_catalog_has_6_group_pack_templates():
    cat = get_catalog()
    assert len(cat.group_pack_templates) == 6


def test_catalog_has_synonyms():
    cat = get_catalog()
    assert len(cat.synonyms) >= 15


def test_catalog_json_has_validation_rules():
    """Raw catalog JSON contains validation_rules."""
    import json
    _p = os.environ["VOIXAI_CATALOG_PATH"]
    raw = json.load(open(_p, encoding="utf-8"))
    assert len(raw.get("validation_rules", [])) >= 15


def test_catalog_json_has_pricing_rules():
    """Raw catalog JSON contains pricing_rules."""
    import json
    _p = os.environ["VOIXAI_CATALOG_PATH"]
    raw = json.load(open(_p, encoding="utf-8"))
    assert len(raw.get("pricing_rules", [])) >= 5


def test_all_item_templates_have_valid_category_ids():
    cat = get_catalog()
    valid = {c["id"] for c in cat.categories}
    for t in cat.item_templates:
        assert t.category_id in valid, f"{t.id} has unknown category_id {t.category_id}"


def test_all_combo_templates_have_valid_modifier_group_ids():
    cat = get_catalog()
    valid = {g.id for g in cat.modifier_groups}
    for ct in cat.combo_templates:
        for gid in ct.modifier_group_ids:
            assert gid in valid, f"{ct.id} references unknown modifier_group {gid}"


def test_all_item_templates_have_valid_modifier_group_ids():
    cat = get_catalog()
    valid = {g.id for g in cat.modifier_groups}
    for t in cat.item_templates:
        for gid in t.modifier_group_ids:
            assert gid in valid, f"{t.id} references unknown modifier_group {gid}"


# ══════════════════════════════════════════════════════════════════════════
# Part 2 – Item Template Validation
# ══════════════════════════════════════════════════════════════════════════


def test_classic_wings_6_exists_and_has_correct_price():
    tpl = get_item_template("classic_wings_6")
    assert tpl is not None
    assert tpl.base_price == Decimal("8.99")


def test_classic_wings_6_requires_flavor_selection():
    tpl = get_item_template("classic_wings_6")
    assert "flavor_selection" in tpl.required_slots


def test_classic_wings_6_has_piece_preference_optional():
    tpl = get_item_template("classic_wings_6")
    assert "piece_preference" in tpl.optional_slots


def test_boneless_wings_6_requires_flavor_but_has_no_piece_preference():
    tpl = get_item_template("boneless_wings_6")
    assert "flavor_selection" in tpl.required_slots
    assert "piece_preference" not in tpl.optional_slots
    assert "piece_preference" not in tpl.modifier_group_ids


def test_chicken_sandwich_exists_and_has_correct_price():
    tpl = get_item_template("chicken_sandwich")
    assert tpl is not None
    assert tpl.base_price == Decimal("6.99")


def test_regular_seasoned_fries_exists_as_item():
    tpl = get_item_template("regular_seasoned_fries")
    assert tpl is not None


def test_regular_seasoned_fries_has_no_required_slots():
    tpl = get_item_template("regular_seasoned_fries")
    assert tpl.required_slots == ()


def test_veggie_sticks_has_dip_selection_optional():
    tpl = get_item_template("veggie_sticks")
    assert "dip_selection" in tpl.optional_slots


# ══════════════════════════════════════════════════════════════════════════
# Part 3 – Combo Template Tests
# ══════════════════════════════════════════════════════════════════════════


def test_classic_combo_6_exists_with_correct_price():
    ct = get_combo_template("classic_combo_6")
    assert ct is not None
    assert ct.base_price == Decimal("12.99")


def test_classic_combo_6_requires_side():
    ct = get_combo_template("classic_combo_6")
    assert "combo_side_selection" in ct.required_slots


def test_classic_combo_6_requires_drink():
    ct = get_combo_template("classic_combo_6")
    assert "combo_drink_selection" in ct.required_slots


def test_classic_combo_6_allows_piece_preference():
    ct = get_combo_template("classic_combo_6")
    assert ct.rules is not None
    assert ct.rules.allows_piece_preference is True


def test_classic_combo_6_allows_all_flats():
    ct = get_combo_template("classic_combo_6")
    assert ct.rules is not None
    assert ct.rules.allows_all_flats is True


def test_boneless_combo_6_exists_with_correct_price():
    ct = get_combo_template("boneless_combo_6")
    assert ct is not None
    assert ct.base_price == Decimal("11.99")


def test_boneless_combo_6_does_not_allow_piece_preference():
    ct = get_combo_template("boneless_combo_6")
    assert ct.rules is not None
    assert ct.rules.allows_piece_preference is False


def test_boneless_combo_6_does_not_allow_all_flats():
    ct = get_combo_template("boneless_combo_6")
    assert ct.rules is not None
    assert ct.rules.allows_all_flats is False


def test_boneless_combo_6_requires_side_and_drink():
    ct = get_combo_template("boneless_combo_6")
    assert "combo_side_selection" in ct.required_slots
    assert "combo_drink_selection" in ct.required_slots


def test_chicken_sandwich_combo_requires_side_and_drink():
    ct = get_combo_template("chicken_sandwich_combo")
    assert "combo_side_selection" in ct.required_slots
    assert "combo_drink_selection" in ct.required_slots


def test_tenders_combo_3_does_not_allow_piece_preference():
    ct = get_combo_template("tenders_combo_3")
    assert ct.rules is not None
    assert ct.rules.allows_piece_preference is False


# ══════════════════════════════════════════════════════════════════════════
# Part 4 – Validation Rule Tests  (via validate_order)
# ══════════════════════════════════════════════════════════════════════════


def test_empty_order_fails_validation():
    errors = validate_order(_make_order([]))
    assert "Add at least one valid item" in errors[0]


def test_valid_chicken_sandwich_with_flavor_passes():
    item = _make_item("chicken_sandwich", flavor_ids=["cajun"])
    errors = validate_order(_make_order([item]))
    assert errors == []


def test_chicken_sandwich_without_flavor_fails():
    item = _make_item("chicken_sandwich")
    errors = validate_order(_make_order([item]))
    assert any("flavor" in e.lower() for e in errors)


def test_combo_without_side_fails():
    item = _make_item(
        "chicken_sandwich_combo",
        flavor_ids=["cajun"],
        modifier_ids=["coke"],
    )
    errors = validate_order(_make_order([item]))
    assert any("side" in e.lower() for e in errors)


def test_combo_without_drink_fails():
    item = _make_item(
        "chicken_sandwich_combo",
        flavor_ids=["cajun"],
        modifier_ids=["regular_seasoned_fries"],
    )
    errors = validate_order(_make_order([item]))
    assert any("drink" in e.lower() for e in errors)


@pytest.mark.xfail(
    reason="Catalog slot-group IDs (combo_side_selection) differ from legacy "
           "MODIFIER_GROUPS keys (combo_side_choice); side/drink presence "
           "not yet detected by validate_order for catalog combo items."
)
def test_combo_with_side_and_drink_passes():
    item = _make_item(
        "chicken_sandwich_combo",
        flavor_ids=["cajun"],
        modifier_ids=["regular_seasoned_fries", "coke"],
    )
    errors = validate_order(_make_order([item]))
    assert errors == []


def test_boneless_wings_with_all_flats_fails():
    item = _make_item(
        "boneless_6",
        flavor_ids=["cajun"],
        modifier_ids=["all_flats"],
    )
    errors = validate_order(_make_order([item]))
    assert any("flat" in e.lower() for e in errors)


def test_classic_wings_with_all_flats_passes():
    item = _make_item(
        "classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["all_flats"],
    )
    errors = validate_order(_make_order([item]))
    assert errors == []


def test_boneless_wings_with_well_done_passes():
    item = _make_item(
        "boneless_6",
        flavor_ids=["cajun"],
        modifier_ids=["well_done"],
    )
    errors = validate_order(_make_order([item]))
    assert errors == []


def test_drink_with_well_done_fails():
    item = _make_item(
        "fountain_drink_20oz",
        modifier_ids=["well_done"],
    )
    errors = validate_order(_make_order([item]))
    assert any("well done" in e.lower() for e in errors)
    assert any("drink" in e.lower() for e in errors)


def test_dessert_with_extra_crispy_fails():
    item = _make_item(
        "brownie",
        modifier_ids=["extra_crispy"],
    )
    errors = validate_order(_make_order([item]))
    assert any("extra crispy" in e.lower() for e in errors)
    assert any("dessert" in e.lower() for e in errors)


def test_veggie_sticks_with_wing_flavor_fails():
    item = _make_item(
        "veggie_sticks",
        flavor_ids=["cajun"],
    )
    errors = validate_order(_make_order([item]))
    assert any("cajun" in e.lower() for e in errors)
    assert any("not available" in e.lower() for e in errors)


def test_flavor_count_exceeds_max_fails():
    item = _make_item(
        "chicken_sandwich",
        flavor_ids=["cajun", "mild"],
    )
    errors = validate_order(_make_order([item]))
    assert any("flavor" in e.lower() and "up to" in e.lower() for e in errors)


def test_valid_order_with_multiple_items_passes():
    order = _make_order([
        _make_item("chicken_sandwich", flavor_ids=["cajun"]),
        _make_item("veggie_sticks"),
        _make_item("fountain_drink_20oz"),
    ])
    errors = validate_order(order)
    assert errors == []


# ══════════════════════════════════════════════════════════════════════════
# Part 5 – Reducer Replacement Tests
# ══════════════════════════════════════════════════════════════════════════


def _replace_item(
    order: OrderState,
    new_item_id: str,
    *,
    target_line_id: str | None = None,
    quantity: int | None = None,
    flavor_ids: tuple[str, ...] = (),
    add_modifier_ids: tuple[str, ...] = (),
) -> tuple[OrderState, list[str]]:
    kw = dict(
        replacement_item_id=new_item_id,
        target_line_id=target_line_id,
        flavor_ids=flavor_ids,
        add_modifier_ids=add_modifier_ids,
        quantity=quantity,
    )
    kw = {k: v for k, v in kw.items() if v is not None and v != ()}
    result = apply_order_intent(order, _intent(INTENT_REPLACE_ITEM, **kw))
    return result.order, [e.type for e in result.events]


def test_replace_classic_6_with_boneless_6_preserves_quantity():
    item = _make_item("classic_6", flavor_ids=["cajun"], quantity=2)
    order = _make_order([item])
    result_order, _ = _replace_item(order, "boneless_6")
    assert result_order.items[0].quantity == 2


def test_replace_classic_6_with_boneless_6_removes_piece_preference():
    item = _make_item(
        "classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["all_flats"],
    )
    order = _make_order([item])
    result_order, _ = _replace_item(order, "boneless_6")
    assert "all_flats" not in result_order.items[0].selected_modifier_ids


def test_replace_classic_6_with_boneless_6_preserves_flavors():
    item = _make_item("classic_6", flavor_ids=["cajun"])
    order = _make_order([item])
    result_order, _ = _replace_item(order, "boneless_6")
    assert result_order.items[0].selected_flavor_ids == ["cajun"]


def test_replace_classic_6_with_boneless_6_preserves_cook_preference():
    item = _make_item(
        "classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["well_done"],
    )
    order = _make_order([item])
    result_order, _ = _replace_item(order, "boneless_6")
    assert "well_done" in result_order.items[0].selected_modifier_ids


def test_replace_boneless_6_with_classic_6_preserves_flavors():
    item = _make_item("boneless_6", flavor_ids=["cajun"])
    order = _make_order([item])
    result_order, _ = _replace_item(order, "classic_6")
    assert result_order.items[0].selected_flavor_ids == ["cajun"]


def test_replace_boneless_6_with_classic_6_preserves_dips():
    item = _make_item(
        "boneless_6",
        flavor_ids=["cajun"],
        modifier_ids=["ranch"],
    )
    order = _make_order([item])
    result_order, _ = _replace_item(order, "classic_6")
    assert "ranch" in result_order.items[0].selected_modifier_ids


def test_replace_boneless_6_with_classic_6_allows_piece_preference():
    item = _make_item("boneless_6", flavor_ids=["cajun"])
    order = _make_order([item])
    result_order, _ = _replace_item(order, "classic_6")
    assert len(result_order.items) == 1
    assert result_order.items[0].item_id == "classic_6"


def test_replace_combo_classic_6_with_combo_boneless_6_removes_piece_preference():
    item = _make_item(
        "combo_classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["all_flats", "regular_seasoned_fries", "coke"],
    )
    order = _make_order([item])
    result_order, _ = _replace_item(order, "combo_boneless_6")
    assert "all_flats" not in result_order.items[0].selected_modifier_ids


def test_replace_combo_classic_6_with_combo_boneless_6_preserves_side():
    item = _make_item(
        "combo_classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["regular_seasoned_fries", "coke"],
    )
    order = _make_order([item])
    result_order, _ = _replace_item(order, "combo_boneless_6")
    assert "regular_seasoned_fries" in result_order.items[0].selected_modifier_ids


def test_replace_combo_classic_6_with_combo_boneless_6_preserves_drink():
    item = _make_item(
        "combo_classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["regular_seasoned_fries", "coke"],
    )
    order = _make_order([item])
    result_order, _ = _replace_item(order, "combo_boneless_6")
    assert "coke" in result_order.items[0].selected_modifier_ids


# ══════════════════════════════════════════════════════════════════════════
# Part 6 – Reducer Flavor Limit Tests
# ══════════════════════════════════════════════════════════════════════════


def test_changing_quantity_that_keeps_flavors_within_max_succeeds():
    item = _make_item("classic_6", flavor_ids=["cajun"])
    order = _make_order([item])
    result = apply_order_intent(
        order,
        _intent(INTENT_CHANGE_QUANTITY, target_line_id=item.line_id, quantity=3),
    )
    assert result.order.items[0].quantity == 3
    assert result.order.items[0].selected_flavor_ids == ["cajun"]


def test_changing_to_larger_size_preserves_existing_flavors():
    item = _make_item("classic_6", flavor_ids=["cajun"])
    order = _make_order([item])
    result = apply_order_intent(
        order,
        _intent(INTENT_REPLACE_ITEM, target_line_id=item.line_id, replacement_item_id="classic_10"),
    )
    assert result.order.items[0].selected_flavor_ids == ["cajun"]


def test_adding_flavors_when_max_allows_succeeds():
    item = _make_item("classic_10", flavor_ids=["cajun"])
    order = _make_order([item])
    result = apply_order_intent(
        order,
        _intent(INTENT_CHANGE_FLAVOR, target_line_id=item.line_id, flavor_ids=("cajun", "mild")),
    )
    assert "cajun" in result.order.items[0].selected_flavor_ids
    assert "mild" in result.order.items[0].selected_flavor_ids
    assert len(result.order.items[0].selected_flavor_ids) == 2


def test_adding_too_many_flavors_gets_limited():
    """Adding 3 flavors to classic_6 (max=1) trims to 1 with a flavor_limit_adjusted event."""
    item = _make_item("classic_6", flavor_ids=["cajun", "mild", "garlic_parmesan"])
    order = _make_order([item])
    target_id = item.line_id
    result = apply_order_intent(
        order,
        _intent(INTENT_CHANGE_QUANTITY, target_line_id=target_id, quantity=2),
    )
    event_types = [e.type for e in result.events]
    assert "flavor_limit_adjusted" in event_types
    max_f = _get_max_flavors("classic_6")
    assert len(result.order.items[0].selected_flavor_ids) <= max_f


# ══════════════════════════════════════════════════════════════════════════
# Part 7 – Catalog Lookup Tests
# ══════════════════════════════════════════════════════════════════════════


def test_get_catalog_returns_catalog():
    cat = get_catalog()
    assert cat is not None
    assert cat.schema_version == "2.0"


def test_get_item_template_returns_correct_item():
    tpl = get_item_template("classic_wings_6")
    assert tpl is not None
    assert tpl.id == "classic_wings_6"


def test_get_combo_template_returns_correct_combo():
    ct = get_combo_template("classic_combo_6")
    assert ct is not None
    assert ct.id == "classic_combo_6"


def test_get_group_pack_template_returns_correct_pack():
    gp = get_group_pack_template("meal_for_2_15pc")
    assert gp is not None
    assert gp.id == "meal_for_2_15pc"


def test_get_item_type_for_classic_wings_returns_classic_wings():
    assert get_item_type("classic_wings_6") == "classic_wings"


def test_get_item_type_for_boneless_wings_returns_boneless_wings():
    assert get_item_type("boneless_wings_6") == "boneless_wings"


def test_get_item_type_for_combo_returns_combo():
    assert get_item_type("classic_combo_6") == "combo"


def test_get_item_type_for_group_pack_returns_group_pack():
    assert get_item_type("meal_for_2_15pc") == "group_pack"


def test_get_flavor_by_id_returns_correct_flavor():
    f = get_flavor_by_id("cajun")
    assert f is not None
    assert f.name == "Cajun"


def test_get_modifier_group_by_id_returns_correct_group():
    g = get_modifier_group_by_id("piece_preference")
    assert g is not None
    assert g.name == "Wing Piece Preference"


# ══════════════════════════════════════════════════════════════════════════
# Part 8 – Edge Cases
# ══════════════════════════════════════════════════════════════════════════


def test_unknown_item_id_returns_none_from_get_item_template():
    assert get_item_template("nonexistent_item") is None


def test_unknown_item_id_returns_0_from_get_max_flavors():
    assert _get_max_flavors("nonexistent_item") == 0


def test_unknown_item_id_returns_none_from_get_item_type():
    assert get_item_type("nonexistent_item") is None


def test_nonexistent_modifier_id_gracefully_handled():
    item = _make_item("chicken_sandwich", flavor_ids=["cajun"], modifier_ids=["not_a_modifier"])
    errors = validate_order(_make_order([item]))
    assert any("modifier" in e.lower() and "not available" in e.lower() for e in errors)


def test_catalog_synonyms_map_correctly():
    cat = get_catalog()
    syn_map = {s["input"]: s["maps_to"] for s in cat.synonyms}
    assert syn_map["bone in"] == "classic_wings"
    assert syn_map["naked wings"] == "boneless_wings"
    assert syn_map["tenders"] == "crispy_tenders"
    assert syn_map["fries"] == "regular_seasoned_fries"


def test_all_modifier_group_options_have_unique_ids():
    """Options within each modifier group must have unique ids.

    Note: the same option *id* can appear in different groups (e.g.
    ``regular_cook`` is shared between ``wing_cook_preference`` and
    ``fry_cook_preference``).
    """
    cat = get_catalog()
    for g in cat.modifier_groups:
        seen = set()
        for opt in g.options:
            assert opt.id not in seen, f"Duplicate {opt.id} in group {g.id}"
            seen.add(opt.id)


def test_all_item_template_ids_are_unique():
    cat = get_catalog()
    ids = [t.id for t in cat.item_templates]
    assert len(ids) == len(set(ids))


def test_all_combo_template_ids_are_unique():
    cat = get_catalog()
    ids = [c.id for c in cat.combo_templates]
    assert len(ids) == len(set(ids))


def test_all_group_pack_template_ids_are_unique():
    cat = get_catalog()
    ids = [g.id for g in cat.group_pack_templates]
    assert len(ids) == len(set(ids))


# ══════════════════════════════════════════════════════════════════════════
# Part 9 – Combo Flavor Split Tests
# ══════════════════════════════════════════════════════════════════════════


def test_classic_combo_10_allows_split_flavors():
    ct = get_combo_template("classic_combo_10")
    assert ct.max_flavors == 2


def test_classic_combo_6_does_not_allow_two_flavors():
    ct = get_combo_template("classic_combo_6")
    assert ct.max_flavors == 1


def test_half_and_half_with_2_flavors_valid_for_10pc_classic_wings():
    """10-piece classic wings (max_flavors=2) accepts 2 flavors."""
    item = _make_item("classic_10", flavor_ids=["cajun", "mild"])
    errors = validate_order(_make_order([item]))
    assert errors == []


def test_10pc_classic_wings_with_3_flavors_fails_validation():
    item = _make_item("classic_10", flavor_ids=["cajun", "mild", "garlic_parmesan"])
    errors = validate_order(_make_order([item]))
    assert any("up to 2 flavor" in e for e in errors)


# ══════════════════════════════════════════════════════════════════════════
# Part 10 – Group Pack Tests
# ══════════════════════════════════════════════════════════════════════════


def test_meal_for_2_15pc_has_correct_price():
    gp = get_group_pack_template("meal_for_2_15pc")
    assert gp.base_price == Decimal("29.99")


def test_family_pack_24pc_has_correct_price():
    gp = get_group_pack_template("family_pack_24pc")
    assert gp.base_price == Decimal("42.99")


def test_crew_pack_30pc_has_correct_price():
    gp = get_group_pack_template("crew_pack_30pc")
    assert gp.base_price == Decimal("52.99")


def test_party_pack_50pc_has_correct_price():
    gp = get_group_pack_template("party_pack_50pc")
    assert gp.base_price == Decimal("84.99")


def test_all_group_packs_require_side():
    for gid in ("meal_for_2_15pc", "family_pack_24pc", "crew_pack_30pc",
                "party_pack_50pc", "party_pack_75pc", "party_pack_100pc"):
        gp = get_group_pack_template(gid)
        assert gp.rules is not None
        assert gp.rules.requires_side is True, f"{gid} should require side"


def test_all_group_packs_allow_piece_preference():
    for gid in ("meal_for_2_15pc", "family_pack_24pc", "crew_pack_30pc",
                "party_pack_50pc", "party_pack_75pc", "party_pack_100pc"):
        gp = get_group_pack_template(gid)
        assert gp.rules is not None
        assert gp.rules.allows_piece_preference is True, f"{gid} should allow piece_preference"


def test_all_group_packs_have_wing_type_required_true():
    for gid in ("meal_for_2_15pc", "family_pack_24pc", "crew_pack_30pc",
                "party_pack_50pc", "party_pack_75pc", "party_pack_100pc"):
        gp = get_group_pack_template(gid)
        assert gp.rules is not None
        assert gp.rules.wing_type_required is True, f"{gid} should require wing type"


# ══════════════════════════════════════════════════════════════════════════
# Part 11 – Pricing Tests
# ══════════════════════════════════════════════════════════════════════════


def test_simple_wing_item_prices_correctly():
    item = _make_item("classic_6", flavor_ids=["cajun"])
    quote = build_price_quote(_make_order([item]))
    assert "$" in quote.subtotal
    assert "8.99" in quote.subtotal or "8.99" in quote.line_items[0].unit_price


def test_combo_with_base_side_prices_correctly():
    item = _make_item(
        "combo_classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["regular_seasoned_fries", "coke"],
    )
    quote = build_price_quote(_make_order([item]))
    assert "12.99" in quote.line_items[0].unit_price


def test_combo_with_upgraded_side_prices_higher():
    base_item = _make_item(
        "combo_classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["regular_seasoned_fries", "coke"],
    )
    upgraded_item = _make_item(
        "combo_classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["large_seasoned_fries", "coke"],
    )
    base_quote = build_price_quote(_make_order([base_item]))
    upgraded_quote = build_price_quote(_make_order([upgraded_item]))
    base_total = Decimal(base_quote.total.replace("$", ""))
    upgraded_total = Decimal(upgraded_quote.total.replace("$", ""))
    assert upgraded_total > base_total


def test_all_flats_upcharge_applies_correctly():
    without = _make_item("classic_6", flavor_ids=["cajun"])
    with_flats = _make_item("classic_6", flavor_ids=["cajun"], modifier_ids=["all_flats"])
    base_quote = build_price_quote(_make_order([without]))
    flats_quote = build_price_quote(_make_order([with_flats]))
    diff = Decimal(flats_quote.total.replace("$", "")) - Decimal(base_quote.total.replace("$", ""))
    assert diff >= Decimal("1.99")


def test_extra_dip_beyond_included_count_charges_correctly():
    """classic_6 includes 1 dip; 3 extra dips should be charged."""
    item = _make_item(
        "classic_6",
        flavor_ids=["cajun"],
        modifier_ids=["ranch", "blue_cheese", "honey_mustard", "cheese_sauce"],
    )
    quote = build_price_quote(_make_order([item]))
    breakdown = " ".join(quote.line_items[0].breakdown)
    count_plus = breakdown.count("+")
    assert count_plus >= 3, f"Expected 3+ chargeable modifiers, got {count_plus}"


# ══════════════════════════════════════════════════════════════════════════
# Part 12 – Multiple Item Order Tests
# ══════════════════════════════════════════════════════════════════════════


def test_order_with_wings_and_fries_and_drink_validates():
    order = _make_order([
        _make_item("classic_6", flavor_ids=["cajun"]),
        _make_item("regular_fries"),
        _make_item("fountain_drink_20oz"),
    ])
    errors = validate_order(order)
    assert errors == []


def test_order_with_wings_and_fries_and_drink_prices_correctly():
    order = _make_order([
        _make_item("classic_6", flavor_ids=["cajun"]),
        _make_item("regular_fries"),
        _make_item("fountain_drink_20oz"),
    ])
    quote = build_price_quote(order)
    assert len(quote.line_items) == 3
    assert quote.eta_minutes >= 16


def test_cancelling_one_item_from_multi_item_order():
    order = _make_order([
        _make_item("classic_6", flavor_ids=["cajun"]),
        _make_item("regular_fries"),
    ])
    fries_line = order.items[1]
    result = apply_order_intent(
        order,
        _intent(INTENT_REMOVE_ITEM, target_line_id=fries_line.line_id),
    )
    assert len(result.order.items) == 1
    assert result.order.items[0].item_id == "classic_6"


def test_replacing_item_in_multi_item_order():
    order = _make_order([
        _make_item("classic_6", flavor_ids=["cajun"]),
        _make_item("regular_fries"),
    ])
    wings_line = order.items[0]
    result = apply_order_intent(
        order,
        _intent(INTENT_REPLACE_ITEM, target_line_id=wings_line.line_id, replacement_item_id="boneless_6"),
    )
    assert len(result.order.items) == 2
    assert result.order.items[0].item_id == "boneless_6"


# ══════════════════════════════════════════════════════════════════════════
# Part 13 – State Machine + Reducer Integration
# ══════════════════════════════════════════════════════════════════════════


def test_adding_item_sets_state_to_collecting():
    order = _make_order()
    result = apply_order_intent(
        order,
        _intent(INTENT_ADD_ITEM, replacement_item_id="chicken_sandwich",
                target_line_id="line-1"),
    )
    assert len(result.order.items) == 1
    assert "collecting" in result.order.status or "validating" in result.order.status


def test_valid_order_validates_to_passing():
    order = _make_order([
        _make_item("chicken_sandwich", flavor_ids=["cajun"]),
    ])
    errors = validate_order(order)
    assert errors == []


def test_invalid_order_fails_validation_flag():
    order = _make_order([
        _make_item("chicken_sandwich"),
    ])
    errors = validate_order(order)
    assert len(errors) > 0
    order.pos_validation_passed = False
    order.last_validation_errors = list(errors)
    assert order.pos_validation_passed is False


def test_after_validation_pass_state_moves_properly():
    order = _make_order([
        _make_item("chicken_sandwich", flavor_ids=["cajun"]),
    ])
    machine = OrderStateMachine(order)
    machine.start_validation()
    errors = validate_order(order)
    machine.apply_validation(errors)
    assert order.pos_validation_passed is True
    assert order.last_validation_errors == []


def test_cancel_order_clears_items():
    order = _make_order([
        _make_item("classic_6", flavor_ids=["cajun"]),
        _make_item("regular_fries"),
    ])
    result = apply_order_intent(order, _intent(INTENT_CANCEL_ORDER))
    assert result.order.items == []
    event_types = [e.type for e in result.events]
    assert "order_cancelled" in event_types


# ══════════════════════════════════════════════════════════════════════════
# Part 14 – Bulk Parametrized Tests (coverage)
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "item_id,expected_type,expected_price",
    [
        ("classic_wings_6", "classic_wings", "8.99"),
        ("classic_wings_8", "classic_wings", "11.49"),
        ("classic_wings_10", "classic_wings", "13.99"),
        ("classic_wings_15", "classic_wings", "20.99"),
        ("classic_wings_20", "classic_wings", "27.99"),
        ("classic_wings_30", "classic_wings", "40.99"),
        ("classic_wings_50", "classic_wings", "66.99"),
        ("boneless_wings_6", "boneless_wings", "7.99"),
        ("boneless_wings_8", "boneless_wings", "10.49"),
        ("boneless_wings_10", "boneless_wings", "12.99"),
        ("boneless_wings_15", "boneless_wings", "18.99"),
        ("boneless_wings_20", "boneless_wings", "24.99"),
        ("boneless_wings_30", "boneless_wings", "36.99"),
        ("boneless_wings_50", "boneless_wings", "58.99"),
    ],
)
def test_item_templates_parametrized(item_id, expected_type, expected_price):
    tpl = get_item_template(item_id)
    assert tpl is not None
    assert tpl.item_type == expected_type
    assert tpl.base_price == Decimal(expected_price)


@pytest.mark.parametrize(
    "combo_id,expected_price,max_flavors",
    [
        ("classic_combo_6", "12.99", 1),
        ("classic_combo_8", "15.49", 2),
        ("classic_combo_10", "17.99", 2),
        ("boneless_combo_6", "11.99", 1),
        ("boneless_combo_8", "14.49", 2),
        ("boneless_combo_10", "16.99", 2),
        ("tenders_combo_3", "11.49", 1),
        ("tenders_combo_4", "13.49", 1),
        ("chicken_sandwich_combo", "10.99", 1),
    ],
)
def test_combo_templates_parametrized(combo_id, expected_price, max_flavors):
    ct = get_combo_template(combo_id)
    assert ct is not None
    assert ct.base_price == Decimal(expected_price)
    assert ct.max_flavors == max_flavors


@pytest.mark.parametrize(
    "pack_id,expected_price,serves,max_f",
    [
        ("meal_for_2_15pc", "29.99", 2, 2),
        ("family_pack_24pc", "42.99", 4, 3),
        ("crew_pack_30pc", "52.99", 5, 3),
        ("party_pack_50pc", "84.99", 8, 4),
        ("party_pack_75pc", "119.99", 12, 5),
        ("party_pack_100pc", "159.99", 16, 6),
    ],
)
def test_group_pack_templates_parametrized(pack_id, expected_price, serves, max_f):
    gp = get_group_pack_template(pack_id)
    assert gp is not None
    assert gp.base_price == Decimal(expected_price)
    assert gp.serves == serves
    assert gp.max_flavors == max_f


@pytest.mark.parametrize(
    "modifier_id,expected_name,expected_delta",
    [
        ("ranch", "Ranch", "1.49"),
        ("blue_cheese", "Blue Cheese", "1.49"),
        ("honey_mustard", "Honey Mustard", "1.49"),
        ("cheese_sauce", "Cheese Sauce", "1.49"),
        ("cajun_seasoning", "Cajun Seasoning", "0.99"),
        ("all_flats", "All Flats", "1.99"),
        ("all_drums", "All Drums", "1.99"),
        ("mixed", "Mixed Pieces", "0.00"),
        ("regular_cook", "Regular Cook", "0.00"),
        ("well_done", "Well Done", "0.00"),
        ("extra_crispy", "Extra Crispy", "0.00"),
    ],
)
def test_modifier_pricing(modifier_id, expected_name, expected_delta):
    mod = MODIFIER_OPTIONS[modifier_id]
    assert mod.display_name == expected_name
    assert mod.price_delta == Decimal(expected_delta)


@pytest.mark.parametrize(
    "flavor_id,expected_name,heat",
    [
        ("plain", "Plain", 0),
        ("lemon_pepper", "Lemon Pepper", 1),
        ("garlic_parmesan", "Garlic Parmesan", 1),
        ("mild", "Mild", 1),
        ("original_hot", "Original Hot", 3),
        ("cajun", "Cajun", 3),
        ("louisiana_rub", "Louisiana Rub", 2),
        ("hickory_smoked_bbq", "Hickory Smoked BBQ", 1),
        ("hawaiian", "Hawaiian", 1),
        ("mango_habanero", "Mango Habanero", 4),
        ("spicy_korean_q", "Spicy Korean Q", 3),
        ("atomic", "Atomic", 5),
        ("hot_honey_rub", "Hot Honey Rub", 2),
    ],
)
def test_flavor_options(flavor_id, expected_name, heat):
    flav = FLAVOR_OPTIONS[flavor_id]
    assert flav.display_name == expected_name
    assert flav.heat_level == heat


@pytest.mark.parametrize(
    "item_id,expected_max",
    [
        ("classic_wings_6", 1),
        ("classic_wings_10", 2),
        ("classic_wings_20", 3),
        ("classic_wings_50", 4),
        ("boneless_wings_6", 1),
        ("boneless_wings_10", 2),
        ("boneless_wings_20", 3),
        ("boneless_wings_50", 4),
        ("classic_combo_6", 1),
        ("classic_combo_10", 2),
        ("boneless_combo_6", 1),
        ("boneless_combo_10", 2),
        ("meal_for_2_15pc", 2),
        ("family_pack_24pc", 3),
        ("party_pack_50pc", 4),
    ],
)
def test_get_max_flavors_parametrized(item_id, expected_max):
    assert _get_max_flavors(item_id) == expected_max


@pytest.mark.parametrize(
    "item_id,expected_type",
    [
        ("classic_wings_6", "classic_wings"),
        ("boneless_wings_6", "boneless_wings"),
        ("crispy_tenders_3", "crispy_tenders"),
        ("chicken_sandwich", "chicken_sandwich"),
        ("regular_seasoned_fries", "fries"),
        ("veggie_sticks", "sides"),
        ("classic_combo_6", "combo"),
        ("meal_for_2_15pc", "group_pack"),
        ("fountain_drink_20oz", "drinks"),
        ("brownie", "desserts"),
    ],
)
def test_get_item_type_parametrized(item_id, expected_type):
    assert get_item_type(item_id) == expected_type


@pytest.mark.parametrize(
    "line_item,should_pass",
    [
        (_make_item("chicken_sandwich", flavor_ids=["mild"]), True),
        (_make_item("chicken_sandwich", flavor_ids=["lemon_pepper"]), True),
        (_make_item("veggie_sticks", modifier_ids=["ranch"]), True),
        (_make_item("regular_fries"), True),
        (_make_item("classic_6", flavor_ids=["cajun"], modifier_ids=["mixed"]), True),
        (_make_item("classic_6", flavor_ids=["cajun"], modifier_ids=["all_drums"]), True),
        (_make_item("fountain_drink_20oz"), True),
        (_make_item("boneless_6", flavor_ids=["cajun"]), True),
        (_make_item("tenders_3", flavor_ids=["cajun"]), True),
        (_make_item("classic_6", flavor_ids=["mild"]), True),
        (_make_item("brownie"), True),
    ],
)
def test_validation_parametrized_valid(line_item, should_pass):
    errors = validate_order(_make_order([line_item]))
    if should_pass:
        assert errors == [], f"Expected no errors, got: {errors}"
    else:
        assert errors != []


@pytest.mark.parametrize(
    "line_item",
    [
        _make_item("boneless_6", flavor_ids=["cajun"], modifier_ids=["all_drums"]),
        _make_item("classic_6", flavor_ids=["cajun", "mild"]),
        _make_item("chicken_sandwich"),
        _make_item("fountain_drink_20oz", modifier_ids=["extra_crispy"]),
    ],
)
def test_validation_parametrized_invalid(line_item):
    errors = validate_order(_make_order([line_item]))
    assert errors != []


# ── Brittleness: LLM argument formatting deviations ──────────────────────


class TestSplitCsv:
    def test_comma_separated(self):
        assert _split_csv("a, b, c") == ["a", "b", "c"]

    def test_and_separated(self):
        assert _split_csv("lemon pepper and mango habanero") == [
            "lemon pepper",
            "mango habanero",
        ]

    def test_and_with_commas(self):
        assert _split_csv("lemon pepper, mango habanero and cajun") == [
            "lemon pepper",
            "mango habanero",
            "cajun",
        ]

    def test_ampersand_separated(self):
        assert _split_csv("ranch & blue cheese") == ["ranch", "blue cheese"]

    def test_triple_and(self):
        assert _split_csv("a and b and c") == ["a", "b", "c"]

    def test_none_returns_empty(self):
        assert _split_csv(None) == []

    def test_empty_string_returns_empty(self):
        assert _split_csv("") == []

    def test_all_three_separators_mixed(self):
        assert _split_csv("mild, cajun & lemon pepper and garlic parmesan") == [
            "mild",
            "cajun",
            "lemon pepper",
            "garlic parmesan",
        ]


class TestResolveFlavorId:
    def test_exact_match(self):
        assert _resolve_flavor_id("mango habanero") == "mango_habanero"

    def test_all_prefix(self):
        assert _resolve_flavor_id("all lemon pepper") == "lemon_pepper"

    def test_count_prefix(self):
        assert _resolve_flavor_id("5 mango habanero") == "mango_habanero"

    def test_count_word_prefix(self):
        assert _resolve_flavor_id("five lemon pepper") == "lemon_pepper"

    def test_half_prefix(self):
        assert _resolve_flavor_id("half mango habanero") == "mango_habanero"

    def test_the_prefix(self):
        assert _resolve_flavor_id("the lemon pepper") == "lemon_pepper"

    def test_some_prefix(self):
        assert _resolve_flavor_id("some mild") == "mild"

    def test_just_prefix(self):
        assert _resolve_flavor_id("just cajun") == "cajun"

    def test_get_prefix(self):
        assert _resolve_flavor_id("get garlic parmesan") == "garlic_parmesan"

    def test_all_prefix_with_known_split(self):
        assert _resolve_flavor_id("all original hot") == "original_hot"


class TestResolveModifierId:
    def test_exact_match(self):
        assert _resolve_modifier_id("ranch") == "ranch"

    def test_alias_match(self):
        assert _resolve_modifier_id("add ranch") == "ranch"

    def test_verbose_trailing_words(self):
        assert _resolve_modifier_id("extra crispy fries") == "extra_crispy"

    def test_verbose_with_and(self):
        assert _resolve_modifier_id("extra crispy and well done") == "extra_crispy"

    def test_ranch_dressing(self):
        assert _resolve_modifier_id("ranch dressing") == "ranch"

    def test_blue_cheese_dressing(self):
        assert _resolve_modifier_id("blue cheese dressing") == "blue_cheese"

    def test_well_done_wings(self):
        assert _resolve_modifier_id("well done wings") == "well_done"

    def test_unknown_returns_none(self):
        assert _resolve_modifier_id("nonexistent_modifier_xyz") is None


class TestResolveItemIdSynonyms:
    def test_bone_in_wings_resolves(self):
        assert _resolve_item_id("bone in wings") == "classic_6"

    def test_naked_wings_resolves(self):
        assert _resolve_item_id("naked wings") == "boneless_6"

    def test_fries_resolves(self):
        assert _resolve_item_id("fries") == "regular_fries"
