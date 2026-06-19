"""Menu data and lookups for the VoixAI ordering domain.

This module is the single source of truth for the ``Voix Wings Demo`` menu.
The menu is loaded from the POS-grade JSON catalog at
``apps/api/data/wingstop_demo_catalog.json``, and the legacy Python dicts
(``MENU_ITEMS``, ``FLAVOR_OPTIONS``, etc.) are built from it automatically for
backward compatibility.
"""

from __future__ import annotations

import json
import os
import difflib
import re
from decimal import Decimal
from pathlib import Path

from .models import (
    Catalog,
    CatalogFlavor,
    CatalogModifierGroup,
    CatalogModifierOption,
    ComboRules,
    ComboTemplate,
    FlavorOption,
    GroupPackRules,
    GroupPackTemplate,
    IncludedComponents,
    ItemTemplate,
    MainComponent,
    MenuItem,
    ModifierGroup,
    ModifierOption,
    OrderLineItem,
    RestaurantProfile,
)


# ── POS-grade catalog loading -------------------------------------------------

_DEFAULT_CATALOG_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "apps"
    / "api"
    / "data"
    / "wingstop_demo_catalog.json"
)

_catalog: Catalog | None = None


def _parse_catalog_modifier_options(raw_options: list[dict]) -> tuple[CatalogModifierOption, ...]:
    return tuple(
        CatalogModifierOption(
            id=o["id"],
            name=o["name"],
            price_delta=Decimal(str(o.get("price_delta", "0"))),
            aliases=tuple(o.get("aliases", [])),
        )
        for o in raw_options
    )


def load_catalog(path: str | None = None) -> Catalog:
    """Load the POS-grade menu catalog from a JSON file.

    If *path* is ``None`` the file is looked up relative to this package
    (``apps/api/data/wingstop_demo_catalog.json`` under the repo root).
    Subsequent calls return the cached instance.
    """
    global _catalog
    if _catalog is not None:
        return _catalog

    catalog_path = path or os.environ.get("VOIXAI_CATALOG_PATH") or _DEFAULT_CATALOG_PATH
    with open(catalog_path, encoding="utf-8") as f:
        raw = json.load(f)

    rp = raw["restaurant_profile"]
    profile = RestaurantProfile(
        name=rp["name"],
        scenario=rp["scenario"],
        disclaimer=rp["disclaimer"],
        currency=rp["currency"],
        tax_rate=Decimal(str(rp["tax_rate"])),
        default_ready_minutes=rp["default_ready_minutes"],
        supports_pickup=rp["supports_pickup"],
        supports_delivery=rp["supports_delivery"],
    )

    flavors = tuple(
        CatalogFlavor(
            id=f["id"],
            name=f["name"],
            flavor_type=f["flavor_type"],
            heat_level=f["heat_level"],
            available=f.get("available", True),
            aliases=tuple(f.get("aliases", [])),
            allowed_for_item_types=tuple(f.get("allowed_for_item_types", [])),
        )
        for f in raw["flavors"]
    )

    modifier_groups = tuple(
        CatalogModifierGroup(
            id=g["id"],
            name=g["name"],
            applies_to_item_types=tuple(g.get("applies_to_item_types", [])),
            required=g.get("required", False),
            max_select=g.get("max_select", 1),
            options=_parse_catalog_modifier_options(g.get("options", [])),
        )
        for g in raw["modifier_groups"]
    )

    item_templates = tuple(
        ItemTemplate(
            id=t["id"],
            name=t["name"],
            category_id=t["category_id"],
            item_type=t["item_type"],
            base_price=Decimal(str(t["base_price"])),
            available=t.get("available", True),
            piece_count=t.get("piece_count"),
            included_flavor_count=t.get("included_flavor_count", 0),
            included_dip_count=t.get("included_dip_count", 0),
            max_flavors=t.get("max_flavors", 0),
            required_slots=tuple(t.get("required_slots", [])),
            optional_slots=tuple(t.get("optional_slots", [])),
            modifier_group_ids=tuple(t.get("modifier_group_ids", [])),
            prep_time_minutes=t.get("prep_time_minutes", 15),
            aliases=tuple(t.get("aliases", [])),
        )
        for t in raw["item_templates"]
    )

    combo_templates = tuple(
        ComboTemplate(
            id=ct["id"],
            name=ct["name"],
            category_id=ct["category_id"],
            item_type=ct["item_type"],
            base_price=Decimal(str(ct["base_price"])),
            available=ct.get("available", True),
            main_component=_parse_main_component(ct["main_component"]) if "main_component" in ct else None,
            included_components=_parse_included_components(ct["included_components"]) if "included_components" in ct else None,
            max_flavors=ct.get("max_flavors", 1),
            required_slots=tuple(ct.get("required_slots", [])),
            optional_slots=tuple(ct.get("optional_slots", [])),
            modifier_group_ids=tuple(ct.get("modifier_group_ids", [])),
            rules=_parse_combo_rules(ct.get("rules", {})),
            prep_time_minutes=ct.get("prep_time_minutes", 18),
            aliases=tuple(ct.get("aliases", [])),
        )
        for ct in raw.get("combo_templates", [])
    )

    group_pack_templates = tuple(
        GroupPackTemplate(
            id=gp["id"],
            name=gp["name"],
            category_id=gp["category_id"],
            item_type=gp["item_type"],
            base_price=Decimal(str(gp["base_price"])),
            available=gp.get("available", True),
            main_component=_parse_main_component(gp["main_component"]) if "main_component" in gp else None,
            included_components=_parse_included_components(gp["included_components"]) if "included_components" in gp else None,
            max_flavors=gp.get("max_flavors", 2),
            serves=gp.get("serves", 2),
            required_slots=tuple(gp.get("required_slots", [])),
            optional_slots=tuple(gp.get("optional_slots", [])),
            modifier_group_ids=tuple(gp.get("modifier_group_ids", [])),
            rules=_parse_group_pack_rules(gp.get("rules", {})),
            prep_time_minutes=gp.get("prep_time_minutes", 22),
            aliases=tuple(gp.get("aliases", [])),
        )
        for gp in raw.get("group_pack_templates", [])
    )

    categories = tuple(
        {"id": c["id"], "name": c["name"]} for c in raw.get("categories", [])
    )

    synonyms = tuple(
        {"input": s["input"], "maps_to": s["maps_to"]} for s in raw.get("synonyms", [])
    )

    _catalog = Catalog(
        schema_version=raw["schema_version"],
        restaurant_profile=profile,
        categories=categories,
        flavors=flavors,
        modifier_groups=modifier_groups,
        item_templates=item_templates,
        combo_templates=combo_templates,
        group_pack_templates=group_pack_templates,
        synonyms=synonyms,
    )
    return _catalog


def _parse_main_component(raw: dict) -> MainComponent:
    return MainComponent(
        component_type=raw["component_type"],
        piece_count=raw.get("piece_count", 0),
        required=raw.get("required", True),
        allow_classic=raw.get("allow_classic", True),
        allow_boneless=raw.get("allow_boneless", True),
    )


def _parse_included_components(raw: dict) -> IncludedComponents:
    return IncludedComponents(
        side_count=raw.get("side_count", 0),
        drink_count=raw.get("drink_count", 0),
        dip_count=raw.get("dip_count", 0),
    )


def _parse_combo_rules(raw: dict) -> ComboRules:
    return ComboRules(
        allows_piece_preference=raw.get("allows_piece_preference", False),
        allows_all_flats=raw.get("allows_all_flats", False),
        allows_all_drums=raw.get("allows_all_drums", False),
        requires_side=raw.get("requires_side", True),
        requires_drink=raw.get("requires_drink", True),
    )


def _parse_group_pack_rules(raw: dict) -> GroupPackRules:
    return GroupPackRules(
        allows_piece_preference=raw.get("allows_piece_preference", False),
        requires_side=raw.get("requires_side", False),
        requires_drink=raw.get("requires_drink", False),
        wing_type_required=raw.get("wing_type_required", True),
    )


def get_catalog() -> Catalog:
    """Return the loaded catalog, loading it on first access if needed."""
    if _catalog is None:
        return load_catalog()
    return _catalog


# ── Legacy Python dicts (built from catalog for backward compatibility) ────


FLAVOR_OPTIONS: dict[str, FlavorOption] = {
    "plain": FlavorOption("plain", "Plain", "none", 0, aliases=("no sauce",)),
    "lemon_pepper": FlavorOption(
        "lemon_pepper",
        "Lemon Pepper",
        "dry_rub",
        1,
        aliases=("lemon pepper",),
    ),
    "garlic_parmesan": FlavorOption(
        "garlic_parmesan",
        "Garlic Parmesan",
        "dry_rub",
        1,
        aliases=("garlic parm", "garlic parmesan"),
    ),
    "mild": FlavorOption("mild", "Mild", "sauce", 1),
    "original_hot": FlavorOption(
        "original_hot",
        "Original Hot",
        "sauce",
        3,
        aliases=("hot", "original hot"),
    ),
    "cajun": FlavorOption(
        "cajun",
        "Cajun",
        "sauce",
        3,
        aliases=("original cajun", "cajun rub"),
    ),
    "louisiana_rub": FlavorOption(
        "louisiana_rub",
        "Louisiana Rub",
        "dry_rub",
        2,
        aliases=("voodoo rub",),
    ),
    "hickory_smoked_bbq": FlavorOption(
        "hickory_smoked_bbq",
        "Hickory Smoked BBQ",
        "sauce",
        1,
        aliases=("bbq", "barbecue"),
    ),
    "hawaiian": FlavorOption("hawaiian", "Hawaiian", "sauce", 1),
    "mango_habanero": FlavorOption(
        "mango_habanero",
        "Mango Habanero",
        "sauce",
        4,
        aliases=("mango hab", "mango habanero"),
    ),
    "spicy_korean_q": FlavorOption(
        "spicy_korean_q",
        "Spicy Korean Q",
        "sauce",
        3,
        aliases=("korean", "korean q"),
    ),
    "atomic": FlavorOption("atomic", "Atomic", "sauce", 5),
    "hot_honey_rub": FlavorOption(
        "hot_honey_rub",
        "Hot Honey Rub",
        "dry_rub",
        2,
        aliases=("hot honey", "hot honey rub"),
    ),
}

MODIFIER_OPTIONS: dict[str, ModifierOption] = {
    "mixed": ModifierOption(
        "mixed",
        "Mixed Pieces",
        aliases=("mixed pieces", "regular pieces", "mixed"),
    ),
    "all_flats": ModifierOption(
        "all_flats",
        "All Flats",
        Decimal("1.99"),
        aliases=("all flats", "flats only"),
    ),
    "all_drums": ModifierOption(
        "all_drums",
        "All Drums",
        Decimal("1.99"),
        aliases=("all drums", "drums only"),
    ),
    "regular_cook": ModifierOption(
        "regular_cook",
        "Regular Cook",
        aliases=("regular", "regular cook"),
    ),
    "well_done": ModifierOption(
        "well_done",
        "Well Done",
        aliases=("well done",),
    ),
    "extra_crispy": ModifierOption(
        "extra_crispy",
        "Extra Crispy",
        aliases=("extra crispy",),
    ),
    "regular_seasoning": ModifierOption(
        "regular_seasoning",
        "Regular Seasoning",
        aliases=("regular seasoning",),
    ),
    "light_seasoning": ModifierOption(
        "light_seasoning",
        "Light Seasoning",
        aliases=("light seasoning",),
    ),
    "extra_seasoning": ModifierOption(
        "extra_seasoning",
        "Extra Seasoning",
        aliases=("extra seasoning",),
    ),
    "no_seasoning": ModifierOption(
        "no_seasoning",
        "No Seasoning",
        aliases=("no seasoning",),
    ),
    "cheese_sauce": ModifierOption(
        "cheese_sauce",
        "Cheese Sauce",
        Decimal("1.49"),
        aliases=("cheese", "cheese sauce", "add cheese sauce"),
    ),
    "ranch": ModifierOption(
        "ranch",
        "Ranch",
        Decimal("1.49"),
        aliases=("ranch", "add ranch", "regular ranch"),
    ),
    "buffalo_ranch": ModifierOption(
        "buffalo_ranch",
        "Buffalo Ranch",
        Decimal("1.49"),
        aliases=("buffalo ranch", "add buffalo ranch"),
    ),
    "cajun_seasoning": ModifierOption(
        "cajun_seasoning",
        "Cajun Seasoning",
        Decimal("0.99"),
        aliases=("add cajun seasoning", "cajun seasoning"),
    ),
    "blue_cheese": ModifierOption(
        "blue_cheese",
        "Blue Cheese",
        Decimal("1.49"),
        aliases=("blue cheese", "bleu cheese"),
    ),
    "honey_mustard": ModifierOption(
        "honey_mustard",
        "Honey Mustard",
        Decimal("1.49"),
        aliases=("honey mustard",),
    ),
    "regular_seasoned_fries": ModifierOption(
        "regular_seasoned_fries",
        "Regular Seasoned Fries",
        aliases=("fries", "regular fries", "seasoned fries"),
    ),
    "veggie_sticks": ModifierOption(
        "veggie_sticks",
        "Veggie Sticks",
        aliases=("veggie sticks", "carrot sticks"),
    ),
    "large_seasoned_fries": ModifierOption(
        "large_seasoned_fries",
        "Large Seasoned Fries",
        Decimal("1.99"),
        aliases=("large fries", "large seasoned fries"),
    ),
    "cajun_fried_corn": ModifierOption(
        "cajun_fried_corn",
        "Cajun Fried Corn",
        Decimal("1.49"),
        aliases=("corn", "fried corn", "cajun fried corn"),
    ),
    "coke": ModifierOption("coke", "Coke", aliases=("coke", "coca cola")),
    "diet_coke": ModifierOption(
        "diet_coke",
        "Diet Coke",
        aliases=("diet coke",),
    ),
    "sprite": ModifierOption("sprite", "Sprite", aliases=("sprite",)),
    "dr_pepper": ModifierOption("dr_pepper", "Dr Pepper", aliases=("dr pepper", "doctor pepper")),
    "lemonade": ModifierOption(
        "lemonade",
        "Lemonade",
        aliases=("lemonade",),
    ),
    "iced_tea": ModifierOption(
        "iced_tea",
        "Iced Tea",
        aliases=("iced tea", "tea"),
    ),
    "bottled_water": ModifierOption(
        "bottled_water",
        "Bottled Water",
        aliases=("water", "bottled water"),
    ),
}

MODIFIER_GROUPS: dict[str, ModifierGroup] = {
    "wing_piece_preference": ModifierGroup(
        "wing_piece_preference",
        "Wing Piece Preference",
        False,
        0,
        1,
        ("mixed", "all_flats", "all_drums"),
    ),
    "cook_preference_wings": ModifierGroup(
        "cook_preference_wings",
        "Cook Preference",
        False,
        0,
        1,
        ("regular_cook", "well_done", "extra_crispy"),
    ),
    "dip_selection": ModifierGroup(
        "dip_selection",
        "Dip Selection",
        False,
        0,
        10,
        ("ranch", "blue_cheese", "honey_mustard", "cheese_sauce"),
    ),
    "combo_side_choice": ModifierGroup(
        "combo_side_choice",
        "Combo Side Choice",
        True,
        1,
        1,
        ("regular_seasoned_fries", "veggie_sticks", "large_seasoned_fries", "cajun_fried_corn"),
    ),
    "combo_drink_choice": ModifierGroup(
        "combo_drink_choice",
        "Combo Drink Choice",
        True,
        1,
        1,
        (
            "coke",
            "diet_coke",
            "sprite",
            "dr_pepper",
            "lemonade",
            "iced_tea",
            "bottled_water",
        ),
    ),
    "fry_cook_preference": ModifierGroup(
        "fry_cook_preference",
        "Fry Cook Preference",
        False,
        0,
        1,
        ("regular_cook", "well_done", "extra_crispy"),
    ),
    "fry_seasoning_level": ModifierGroup(
        "fry_seasoning_level",
        "Fry Seasoning Level",
        False,
        0,
        1,
        ("regular_seasoning", "light_seasoning", "extra_seasoning", "no_seasoning"),
    ),
    "fry_add_ons": ModifierGroup(
        "fry_add_ons",
        "Fry Add-ons",
        False,
        0,
        4,
        ("cheese_sauce", "ranch", "buffalo_ranch", "cajun_seasoning"),
    ),
}

MENU_ITEMS: dict[str, MenuItem] = {
    "combo_classic_6": MenuItem(
        "combo_classic_6",
        "6 Piece Classic Wing Combo",
        "Wing Combos",
        Decimal("12.99"),
        aliases=(
            "6 wing combo",
            "6 piece classic combo",
            "6 piece wing combo",
            "six wing combo",
            "six piece classic combo",
            "classic wing combo",
        ),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=18,
        order_style="classic bone-in",
    ),
    "combo_classic_8": MenuItem(
        "combo_classic_8",
        "8 Piece Classic Wing Combo",
        "Wing Combos",
        Decimal("15.49"),
        aliases=("8 classic combo", "8 piece classic combo", "eight classic combo", "eight piece classic combo"),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        prep_time_minutes=18,
        order_style="classic bone-in",
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
    ),
    "combo_classic_10": MenuItem(
        "combo_classic_10",
        "10 Piece Classic Wing Combo",
        "Wing Combos",
        Decimal("17.99"),
        aliases=("10 classic combo", "10 piece classic combo", "ten classic combo", "ten piece classic combo"),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        prep_time_minutes=19,
        order_style="classic bone-in",
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
    ),
    "combo_boneless_6": MenuItem(
        "combo_boneless_6",
        "6 Piece Boneless Wing Combo",
        "Wing Combos",
        Decimal("11.99"),
        aliases=(
            "6 boneless combo",
            "6 piece boneless combo",
            "six boneless combo",
            "six piece boneless combo",
            "boneless combo",
        ),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        prep_time_minutes=17,
        order_style="boneless",
    ),
    "combo_boneless_8": MenuItem(
        "combo_boneless_8",
        "8 Piece Boneless Wing Combo",
        "Wing Combos",
        Decimal("14.49"),
        aliases=("8 boneless combo", "8 piece boneless combo", "eight boneless combo", "eight piece boneless combo"),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        prep_time_minutes=18,
        order_style="boneless",
    ),
    "combo_boneless_10": MenuItem(
        "combo_boneless_10",
        "10 Piece Boneless Wing Combo",
        "Wing Combos",
        Decimal("16.99"),
        aliases=("10 boneless combo", "10 piece boneless combo", "ten boneless combo", "ten piece boneless combo"),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        prep_time_minutes=19,
        order_style="boneless",
    ),
    "classic_6": MenuItem(
        "classic_6",
        "6 Classic Wings",
        "Wings By The Piece",
        Decimal("8.99"),
        aliases=("6 bone in wings", "six bone in wings", "6 regular wings", "six classic wings", "bone in wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=16,
        order_style="classic bone-in",
    ),
    "classic_8": MenuItem(
        "classic_8",
        "8 Classic Wings",
        "Wings By The Piece",
        Decimal("11.49"),
        aliases=("8 bone in wings", "eight bone in wings", "8 regular wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=16,
        order_style="classic bone-in",
    ),
    "classic_10": MenuItem(
        "classic_10",
        "10 Classic Wings",
        "Wings By The Piece",
        Decimal("13.99"),
        aliases=("10 bone in wings", "ten bone in wings", "10 regular wings", "10 classic wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=17,
        order_style="classic bone-in",
    ),
    "classic_15": MenuItem(
        "classic_15",
        "15 Classic Wings",
        "Wings By The Piece",
        Decimal("20.99"),
        aliases=("15 bone in wings", "fifteen bone in wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=2,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=18,
        order_style="classic bone-in",
    ),
    "classic_20": MenuItem(
        "classic_20",
        "20 Classic Wings",
        "Wings By The Piece",
        Decimal("27.99"),
        aliases=("20 bone in wings", "twenty bone in wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=3,
        included_dip_count=2,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=20,
        order_style="classic bone-in",
    ),
    "classic_30": MenuItem(
        "classic_30",
        "30 Classic Wings",
        "Wings By The Piece",
        Decimal("40.99"),
        aliases=("30 bone in wings", "thirty bone in wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=3,
        included_dip_count=3,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=24,
        order_style="classic bone-in",
    ),
    "classic_50": MenuItem(
        "classic_50",
        "50 Classic Wings",
        "Wings By The Piece",
        Decimal("66.99"),
        aliases=("50 bone in wings", "fifty bone in wings"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=4,
        included_dip_count=4,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=30,
        order_style="classic bone-in",
    ),
    "boneless_6": MenuItem(
        "boneless_6",
        "6 Boneless Wings",
        "Boneless Wings",
        Decimal("7.99"),
        aliases=("6 boneless wings", "six boneless wings", "boneless", "naked wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        prep_time_minutes=15,
        order_style="boneless",
    ),
    "boneless_8": MenuItem(
        "boneless_8",
        "8 Boneless Wings",
        "Boneless Wings",
        Decimal("10.49"),
        aliases=("8 boneless wings", "eight boneless wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        prep_time_minutes=15,
        order_style="boneless",
    ),
    "boneless_10": MenuItem(
        "boneless_10",
        "10 Boneless Wings",
        "Boneless Wings",
        Decimal("12.99"),
        aliases=("10 boneless wings", "ten boneless wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        prep_time_minutes=16,
        order_style="boneless",
    ),
    "boneless_15": MenuItem(
        "boneless_15",
        "15 Boneless Wings",
        "Boneless Wings",
        Decimal("18.99"),
        aliases=("15 boneless wings", "fifteen boneless wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=2,
        prep_time_minutes=17,
        order_style="boneless",
    ),
    "boneless_20": MenuItem(
        "boneless_20",
        "20 Boneless Wings",
        "Boneless Wings",
        Decimal("24.99"),
        aliases=("20 boneless wings", "twenty boneless wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=3,
        included_dip_count=2,
        prep_time_minutes=19,
        order_style="boneless",
    ),
    "boneless_30": MenuItem(
        "boneless_30",
        "30 Boneless Wings",
        "Boneless Wings",
        Decimal("36.99"),
        aliases=("30 boneless wings", "thirty boneless wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=3,
        included_dip_count=3,
        prep_time_minutes=23,
        order_style="boneless",
    ),
    "boneless_50": MenuItem(
        "boneless_50",
        "50 Boneless Wings",
        "Boneless Wings",
        Decimal("58.99"),
        aliases=("50 boneless wings", "fifty boneless wings"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=4,
        included_dip_count=4,
        prep_time_minutes=28,
        order_style="boneless",
    ),
    "tenders_3": MenuItem(
        "tenders_3",
        "3 Crispy Tenders",
        "Crispy Tenders",
        Decimal("7.49"),
        aliases=("3 tenders", "three tenders", "strips"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        prep_time_minutes=15,
        order_style="tenders",
    ),
    "tenders_4": MenuItem(
        "tenders_4",
        "4 Crispy Tenders",
        "Crispy Tenders",
        Decimal("9.49"),
        aliases=("4 tenders", "four tenders"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=1,
        included_dip_count=1,
        prep_time_minutes=15,
        order_style="tenders",
    ),
    "tenders_6": MenuItem(
        "tenders_6",
        "6 Crispy Tenders",
        "Crispy Tenders",
        Decimal("13.49"),
        aliases=("6 tenders", "six tenders"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=1,
        prep_time_minutes=17,
        order_style="tenders",
    ),
    "tenders_10": MenuItem(
        "tenders_10",
        "10 Crispy Tenders",
        "Crispy Tenders",
        Decimal("21.99"),
        aliases=("10 tenders", "ten tenders"),
        optional_modifier_group_ids=("cook_preference_wings", "dip_selection"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=2,
        prep_time_minutes=22,
        order_style="tenders",
    ),
    "chicken_sandwich": MenuItem(
        "chicken_sandwich",
        "Chicken Sandwich",
        "Chicken Sandwich",
        Decimal("6.99"),
        aliases=("sandwich", "chicken sandwich"),
        requires_flavors=True,
        prep_time_minutes=14,
    ),
    "chicken_sandwich_combo": MenuItem(
        "chicken_sandwich_combo",
        "Chicken Sandwich Combo",
        "Chicken Sandwich",
        Decimal("10.99"),
        aliases=("sandwich combo", "chicken sandwich combo"),
        required_modifier_group_ids=("combo_side_choice", "combo_drink_choice"),
        requires_flavors=True,
        prep_time_minutes=16,
    ),
    "meal_for_2_15pc": MenuItem(
        "meal_for_2_15pc",
        "15 Piece Meal for 2",
        "Group Packs",
        Decimal("29.99"),
        aliases=("meal for 2", "15 piece meal for 2"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection", "combo_side_choice"),
        requires_flavors=True,
        max_flavors=2,
        included_dip_count=2,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=22,
        order_style="classic bone-in",
    ),
    "family_pack_24pc": MenuItem(
        "family_pack_24pc",
        "24 Piece Family Pack",
        "Group Packs",
        Decimal("42.99"),
        aliases=("family pack", "24 piece family pack"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection", "combo_side_choice"),
        requires_flavors=True,
        max_flavors=3,
        included_dip_count=3,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=24,
        order_style="classic bone-in",
    ),
    "crew_pack_30pc": MenuItem(
        "crew_pack_30pc",
        "30 Piece Crew Pack",
        "Group Packs",
        Decimal("52.99"),
        aliases=("crew pack", "30 piece crew pack"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection", "combo_side_choice"),
        requires_flavors=True,
        max_flavors=3,
        included_dip_count=3,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=26,
        order_style="classic bone-in",
    ),
    "party_pack_50pc": MenuItem(
        "party_pack_50pc",
        "50 Piece Party Pack",
        "Group Packs",
        Decimal("84.99"),
        aliases=("party pack", "50 piece party pack"),
        optional_modifier_group_ids=("wing_piece_preference", "cook_preference_wings", "dip_selection", "combo_side_choice"),
        requires_flavors=True,
        max_flavors=4,
        included_dip_count=4,
        supports_piece_preference=True,
        allowed_piece_preference_ids=("mixed", "all_flats", "all_drums"),
        prep_time_minutes=30,
        order_style="classic bone-in",
    ),
    "regular_fries": MenuItem(
        "regular_fries",
        "Regular Seasoned Fries",
        "Fries",
        Decimal("3.49"),
        aliases=("seasoned fries", "regular fries", "fries"),
        optional_modifier_group_ids=("fry_cook_preference", "fry_seasoning_level", "fry_add_ons"),
        prep_time_minutes=10,
    ),
    "large_fries": MenuItem(
        "large_fries",
        "Large Seasoned Fries",
        "Fries",
        Decimal("5.49"),
        aliases=("large fries", "large seasoned fries"),
        optional_modifier_group_ids=("fry_cook_preference", "fry_seasoning_level", "fry_add_ons"),
        prep_time_minutes=11,
    ),
    "cheese_fries": MenuItem(
        "cheese_fries",
        "Cheese Fries",
        "Fries",
        Decimal("5.99"),
        aliases=("cheese fries",),
        optional_modifier_group_ids=("fry_cook_preference", "fry_seasoning_level"),
        prep_time_minutes=11,
    ),
    "voodoo_fries": MenuItem(
        "voodoo_fries",
        "Louisiana Voodoo Fries",
        "Fries",
        Decimal("6.49"),
        aliases=("voodoo fries", "louisiana voodoo fries"),
        optional_modifier_group_ids=("fry_cook_preference", "fry_seasoning_level"),
        prep_time_minutes=12,
    ),
    "buffalo_ranch_fries": MenuItem(
        "buffalo_ranch_fries",
        "Buffalo Ranch Fries",
        "Fries",
        Decimal("6.49"),
        aliases=("buffalo ranch fries",),
        optional_modifier_group_ids=("fry_cook_preference", "fry_seasoning_level"),
        prep_time_minutes=12,
    ),
    "veggie_sticks": MenuItem(
        "veggie_sticks",
        "Veggie Sticks",
        "Sides",
        Decimal("3.49"),
        aliases=("veggie sticks",),
        optional_modifier_group_ids=("dip_selection",),
        prep_time_minutes=5,
    ),
    "fried_corn": MenuItem(
        "fried_corn",
        "Cajun Fried Corn",
        "Sides",
        Decimal("4.49"),
        aliases=("corn", "fried corn", "cajun fried corn"),
        prep_time_minutes=8,
    ),
    "baked_rolls": MenuItem(
        "baked_rolls",
        "Baked Rolls",
        "Sides",
        Decimal("3.99"),
        aliases=("baked rolls", "rolls"),
        prep_time_minutes=6,
    ),
    "side_ranch": MenuItem(
        "side_ranch",
        "Regular Ranch",
        "Dips",
        Decimal("1.49"),
        aliases=("ranch dip", "side ranch", "regular ranch"),
        item_kind="dip",
        prep_time_minutes=2,
    ),
    "large_ranch": MenuItem(
        "large_ranch",
        "Large Ranch",
        "Dips",
        Decimal("4.99"),
        aliases=("large ranch",),
        item_kind="dip",
        prep_time_minutes=2,
    ),
    "side_blue_cheese": MenuItem(
        "side_blue_cheese",
        "Regular Blue Cheese",
        "Dips",
        Decimal("1.49"),
        aliases=("blue cheese dip", "side blue cheese", "regular blue cheese"),
        item_kind="dip",
        prep_time_minutes=2,
    ),
    "large_blue_cheese": MenuItem(
        "large_blue_cheese",
        "Large Blue Cheese",
        "Dips",
        Decimal("4.99"),
        aliases=("large blue cheese",),
        item_kind="dip",
        prep_time_minutes=2,
    ),
    "side_honey_mustard": MenuItem(
        "side_honey_mustard",
        "Regular Honey Mustard",
        "Dips",
        Decimal("1.49"),
        aliases=("honey mustard dip", "side honey mustard", "regular honey mustard"),
        item_kind="dip",
        prep_time_minutes=2,
    ),
    "side_cheese_sauce": MenuItem(
        "side_cheese_sauce",
        "Regular Cheese Sauce",
        "Dips",
        Decimal("1.49"),
        aliases=("side cheese sauce", "regular cheese sauce"),
        item_kind="dip",
        prep_time_minutes=2,
    ),
    "fountain_drink_20oz": MenuItem(
        "fountain_drink_20oz",
        "20 oz Fountain Drink",
        "Drinks",
        Decimal("2.99"),
        aliases=("20 oz drink", "small fountain drink"),
        item_kind="drink",
        optional_modifier_group_ids=("combo_drink_choice",),
        prep_time_minutes=2,
    ),
    "fountain_drink_32oz": MenuItem(
        "fountain_drink_32oz",
        "32 oz Fountain Drink",
        "Drinks",
        Decimal("3.49"),
        aliases=("32 oz drink", "large fountain drink"),
        item_kind="drink",
        optional_modifier_group_ids=("combo_drink_choice",),
        prep_time_minutes=2,
    ),
    "drink_water_item": MenuItem(
        "drink_water_item",
        "Bottled Water",
        "Drinks",
        Decimal("2.49"),
        aliases=("water", "bottled water"),
        item_kind="drink",
        prep_time_minutes=2,
    ),
    "brownie": MenuItem(
        "brownie",
        "Brownie",
        "Desserts",
        Decimal("2.99"),
        aliases=("brownie",),
        prep_time_minutes=3,
    ),
    "triple_chocolate_chunk_brownie": MenuItem(
        "triple_chocolate_chunk_brownie",
        "Triple Chocolate Chunk Brownie",
        "Desserts",
        Decimal("3.49"),
        aliases=("triple chocolate brownie", "chunk brownie"),
        prep_time_minutes=4,
    ),
}

STORE_HOURS = "11:00 AM to 11:00 PM"

ITEM_ALIAS_TO_ID: dict[str, str] = {}
FLAVOR_ALIAS_TO_ID: dict[str, str] = {}
MODIFIER_ALIAS_TO_ID: dict[str, str] = {}
OPTION_TO_GROUP_IDS: dict[str, set[str]] = {}


def _normalize_lookup_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


for menu_item in MENU_ITEMS.values():
    ITEM_ALIAS_TO_ID[_normalize_lookup_key(menu_item.display_name)] = menu_item.id
    for alias in menu_item.aliases:
        ITEM_ALIAS_TO_ID[_normalize_lookup_key(alias)] = menu_item.id

for flavor in FLAVOR_OPTIONS.values():
    FLAVOR_ALIAS_TO_ID[_normalize_lookup_key(flavor.display_name)] = flavor.id
    for alias in flavor.aliases:
        FLAVOR_ALIAS_TO_ID[_normalize_lookup_key(alias)] = flavor.id

FLAVOR_FUZZY_INDEX: list[tuple[frozenset[str], str]] = []
for flavor in FLAVOR_OPTIONS.values():
    for label in (flavor.display_name, *flavor.aliases):
        token_set = frozenset(_normalize_lookup_key(label).split())
        if token_set:
            FLAVOR_FUZZY_INDEX.append((token_set, flavor.id))

for modifier in MODIFIER_OPTIONS.values():
    MODIFIER_ALIAS_TO_ID[_normalize_lookup_key(modifier.display_name)] = modifier.id
    for alias in modifier.aliases:
        MODIFIER_ALIAS_TO_ID[_normalize_lookup_key(alias)] = modifier.id

for group in MODIFIER_GROUPS.values():
    for option_id in group.option_ids:
        OPTION_TO_GROUP_IDS.setdefault(option_id, set()).add(group.id)


# --- Robust item resolution -------------------------------------------------
# Exact alias matching is brittle for voice input: a customer says "6 piece
# classic combo" but the alias list has "6 piece classic combo" only in one
# exact spelling/word order. The token matcher below resolves natural phrasings
# safely: spoken number words become digits, filler words are dropped, any
# number in the request must match the item's size exactly, and a request that
# could mean two different items (e.g. "classic combo" without a size) resolves
# to nothing so the agent asks instead of guessing.

_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "fifteen": "15",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
}

# Words that do not distinguish one menu item from another.
_ITEM_STOPWORDS = {
    "piece",
    "pieces",
    "pc",
    "pcs",
    "wing",
    "wings",
    "order",
    "orders",
    "the",
    "a",
    "an",
    "of",
    "please",
    "some",
    "get",
    "want",
    "like",
    "with",
    "and",
    "plus",
    "just",
    "add",
    "me",
    "my",
    "i",
}


def _item_match_tokens(name: str) -> set[str]:
    tokens: list[str] = []
    for raw in _normalize_lookup_key(name).split():
        token = _NUMBER_WORDS.get(raw, raw)
        if token in _ITEM_STOPWORDS:
            continue
        tokens.append(token)
    return set(tokens)


# (token_set, item_id) for every display name and alias, using the matcher's
# tokenization so query and candidate are compared on equal footing.
ITEM_FUZZY_INDEX: list[tuple[frozenset[str], str]] = []
for menu_item in MENU_ITEMS.values():
    for label in (menu_item.display_name, *menu_item.aliases):
        token_set = frozenset(_item_match_tokens(label))
        if token_set:
            ITEM_FUZZY_INDEX.append((token_set, menu_item.id))


def _fuzzy_item_scores(name: str) -> list[tuple[str, float]]:
    """Rank menu items for a (non-exact) request. Higher score = tighter match.

    Numbers in the request must match the candidate's size exactly, and every
    non-number request word must appear in the candidate, so wrong-size or
    wrong-item matches are filtered out rather than guessed.
    """
    query = _item_match_tokens(name)
    if not query:
        return []

    query_numbers = {token for token in query if token.isdigit()}
    query_words = query - query_numbers

    best_by_item: dict[str, float] = {}
    for token_set, item_id in ITEM_FUZZY_INDEX:
        candidate_numbers = {token for token in token_set if token.isdigit()}

        # A requested size must match exactly; a sized request can't match an
        # unsized item (and vice versa).
        if query_numbers != candidate_numbers and query_numbers:
            continue

        candidate_words = token_set - candidate_numbers
        if query_words and not query_words.issubset(candidate_words):
            continue

        overlap = len(query & token_set)
        precision = overlap / len(token_set)
        recall = overlap / len(query)
        score = precision + 0.001 * recall  # tie-break toward fuller coverage
        if score > best_by_item.get(item_id, 0.0):
            best_by_item[item_id] = score

    return sorted(best_by_item.items(), key=lambda kv: (-kv[1], kv[0]))


def _resolve_item_id(name: str) -> str | None:
    key = _normalize_lookup_key(name)
    if not key:
        return None

    exact = ITEM_ALIAS_TO_ID.get(key)
    if exact is not None:
        return exact

    scores = _fuzzy_item_scores(name)
    if not scores:
        return None
    if len(scores) == 1:
        return scores[0][0]
    # Only resolve when there is a single clear winner; otherwise let the agent
    # clarify rather than silently pick (e.g. a size) for the customer.
    if scores[0][1] > scores[1][1]:
        return scores[0][0]
    return None


def suggest_item_names(name: str, limit: int = 3) -> list[str]:
    """Closest available item display names for a request we could not resolve."""
    ranked = [MENU_ITEMS[item_id].display_name for item_id, _ in _fuzzy_item_scores(name)]
    if ranked:
        return ranked[:limit]

    # Looser fallback: rank all items by string similarity to the raw request so
    # even an off-menu request gets nearby suggestions.
    key = _normalize_lookup_key(name)
    if not key:
        return []
    scored = sorted(
        MENU_ITEMS.values(),
        key=lambda item: difflib.SequenceMatcher(
            None, key, _normalize_lookup_key(item.display_name)
        ).ratio(),
        reverse=True,
    )
    return [item.display_name for item in scored[:limit]]


# --- Category lookup (for menu-discovery questions) -------------------------
# Customers say "combos" but the category is "Wing Combos"; exact matching made
# the agent answer "combos aren't available". Match categories by singularized
# tokens instead, and never fail hard — fall back to the category overview.


def menu_categories() -> list[str]:
    categories: list[str] = []
    for menu_item in MENU_ITEMS.values():
        if menu_item.category not in categories:
            categories.append(menu_item.category)
    return categories


def _singularize(token: str) -> str:
    return token[:-1] if len(token) > 3 and token.endswith("s") else token


def _category_tokens(text: str) -> set[str]:
    return {_singularize(token) for token in _normalize_lookup_key(text).split()}


def find_category(query: str) -> str | None:
    """Resolve a spoken category name (e.g. "combos") to a real category, or
    None when the request is empty or matches more than one category."""
    key = _normalize_lookup_key(query)
    if not key:
        return None

    categories = menu_categories()
    for category in categories:
        if _normalize_lookup_key(category) == key:
            return category

    query_tokens = _category_tokens(query)
    if not query_tokens:
        return None
    matches = [c for c in categories if query_tokens.issubset(_category_tokens(c))]
    return matches[0] if len(matches) == 1 else None


def category_items(category: str) -> list[str]:
    return [item.display_name for item in MENU_ITEMS.values() if item.category == category]


def menu_overview_summary() -> str:
    categories = sorted(set(menu_categories()))
    if len(categories) == 1:
        return f"The available category is {categories[0]}."
    return "Available categories are " + ", ".join(categories[:-1]) + f", and {categories[-1]}."


def category_summary(query: str) -> str:
    """A spoken summary for a category question. Always returns real menu info:
    the matched category's items, or the category overview when not specific."""
    category = find_category(query)
    if category is None:
        return menu_overview_summary()
    return f"{category} options: {', '.join(category_items(category))}."


def build_menu_for_prompt() -> str:
    """The full menu as readable text, generated from the menu data so it stays
    in sync. Injected into the agent so the LLM understands and resolves orders
    itself (the backend remains the source of truth for totals and placement)."""
    by_category: dict[str, list[MenuItem]] = {}
    for menu_item in MENU_ITEMS.values():
        by_category.setdefault(menu_item.category, []).append(menu_item)

    lines: list[str] = ["# Voix Wings Demo menu", ""]
    for category in menu_categories():
        lines.append(f"{category}:")
        for menu_item in by_category[category]:
            price = menu_item.base_price.quantize(Decimal("0.01"))
            lines.append(f"- {menu_item.display_name} (${price})")
        lines.append("")

    flavors = ", ".join(f.display_name for f in FLAVOR_OPTIONS.values() if f.available)
    sides = ", ".join(
        MODIFIER_OPTIONS[o].display_name for o in MODIFIER_GROUPS["combo_side_choice"].option_ids
    )
    drinks = ", ".join(
        MODIFIER_OPTIONS[o].display_name for o in MODIFIER_GROUPS["combo_drink_choice"].option_ids
    )
    dips = ", ".join(
        MODIFIER_OPTIONS[o].display_name for o in MODIFIER_GROUPS["dip_selection"].option_ids
    )

    lines.append(f"Flavors: {flavors}.")
    lines.append(
        f"Combos include one flavor, one side ({sides}), and one drink ({drinks})."
    )
    lines.append(f"Dips: {dips}.")
    lines.append(
        "Classic bone-in wings can be all flats or all drums for a small upcharge; "
        "boneless wings cannot."
    )
    return "\n".join(lines)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    # LLMs often use "and", "&", "plus", or "/" instead of commas between
    # list items.  Split on those connectors first, then sub-split on commas.
    parts: list[str] = []
    for and_part in re.split(r"(?i)\s+(?:and|&|plus)\s+|\s*/\s*", value):
        for part in and_part.split(","):
            stripped = part.strip()
            if stripped:
                parts.append(stripped)
    return parts


def _normalize_note(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()


def _resolve_flavor_id(name: str) -> str | None:
    key = _normalize_lookup_key(name)
    direct = FLAVOR_ALIAS_TO_ID.get(key)
    if direct is not None:
        return direct

    # Voice transcripts often prefix split flavors with "half", "1/2",
    # "split", or a count like "5 mango habanero, 5 lemon pepper".
    # Also strip "all" (e.g. "all lemon pepper") and common filler words
    # that realtime models sprinkle into tool arguments.
    key = re.sub(
        r"^(half|split|one half|1 2|one side|other side|half and half"
        r"|\d+|all|the|some|just|want|add|get|like)\s+",
        "",
        key,
    ).strip()
    key = re.sub(
        r"^(one|two|three|four|five|six|seven|eight|nine|ten)\s+",
        "",
        key,
    ).strip()
    key = re.sub(r"\s+(half|split)$", "", key).strip()
    direct = FLAVOR_ALIAS_TO_ID.get(key)
    if direct is not None:
        return direct

    # Fuzzy fallback for STT homophones ("lemon paper" -> "lemon pepper")
    key_tokens = set(key.split())
    if len(key_tokens) >= 1:
        best: list[tuple[str, float]] = []
        for token_set, flavor_id in FLAVOR_FUZZY_INDEX:
            overlap = len(key_tokens & token_set)
            if overlap == 0:
                continue
            precision = overlap / len(token_set)
            recall = overlap / len(key_tokens)
            best.append((flavor_id, precision + recall))
        if best:
            best.sort(key=lambda kv: (-kv[1], kv[0]))
            if len(best) == 1 or best[0][1] > best[1][1]:
                return best[0][0]

    return None


_MODIFIER_FUZZY_STOPWORDS = frozenset(
    {"the", "a", "an", "some", "add", "get", "want", "like", "with", "and", "my"}
)


def _resolve_modifier_id(name: str) -> str | None:
    key = _normalize_lookup_key(name)
    exact = MODIFIER_ALIAS_TO_ID.get(key)
    if exact is not None:
        return exact

    # Fuzzy fallback: try stopword-cleaned tokens directly, then
    # progressively strip trailing words.  Handles "the ranch" (single
    # remaining token after stopword removal) and LLM verbosity like
    # "extra crispy fries" -> "extra crispy".
    tokens = [t for t in key.split() if t not in _MODIFIER_FUZZY_STOPWORDS]
    while tokens:
        candidate = " ".join(tokens)
        result = MODIFIER_ALIAS_TO_ID.get(candidate)
        if result is not None:
            return result
        tokens.pop()

    return None


def _menu_summary_lines() -> str:
    categories: dict[str, list[str]] = {}
    for menu_item in MENU_ITEMS.values():
        categories.setdefault(menu_item.category, []).append(menu_item.display_name)

    lines: list[str] = []
    for category, names in categories.items():
        lines.append(f"- {category}: {', '.join(names)}")
    return "\n".join(lines)


def _flavor_summary_line() -> str:
    return ", ".join(flavor.display_name for flavor in FLAVOR_OPTIONS.values() if flavor.available)


def _flavor_names(selected_flavor_ids: list[str]) -> list[str]:
    return [FLAVOR_OPTIONS[flavor_id].display_name for flavor_id in selected_flavor_ids]


def _modifier_names(selected_modifier_ids: list[str]) -> list[str]:
    return [MODIFIER_OPTIONS[modifier_id].display_name for modifier_id in selected_modifier_ids]


def _selected_by_group(line: OrderLineItem, group_id: str) -> list[str]:
    return [
        modifier_id
        for modifier_id in line.selected_modifier_ids
        if group_id in OPTION_TO_GROUP_IDS.get(modifier_id, set())
    ]


def _get_max_flavors(item_id: str) -> int:
    """Resolve max flavors from catalog templates, falling back to legacy MenuItem."""
    cat_tpl = get_item_template(item_id)
    if cat_tpl:
        return cat_tpl.max_flavors
    combo_tpl = get_combo_template(item_id)
    if combo_tpl:
        return combo_tpl.max_flavors
    pack_tpl = get_group_pack_template(item_id)
    if pack_tpl:
        return pack_tpl.max_flavors
    menu_item = MENU_ITEMS.get(item_id)
    if menu_item:
        return menu_item.max_flavors
    return 0


# ── Catalog-backed lookups (new code should prefer these) ─────────────────


def get_item_template(item_id: str) -> ItemTemplate | None:
    """Look up an ItemTemplate by id from the catalog."""
    cat = get_catalog()
    for t in cat.item_templates:
        if t.id == item_id:
            return t
    return None


def get_combo_template(combo_id: str) -> ComboTemplate | None:
    """Look up a ComboTemplate by id from the catalog."""
    cat = get_catalog()
    for ct in cat.combo_templates:
        if ct.id == combo_id:
            return ct
    return None


def get_group_pack_template(pack_id: str) -> GroupPackTemplate | None:
    """Look up a GroupPackTemplate by id from the catalog."""
    cat = get_catalog()
    for gp in cat.group_pack_templates:
        if gp.id == pack_id:
            return gp
    return None


def get_item_type(item_id: str) -> str | None:
    """Return the item_type for any catalog item (template, combo, or pack)."""
    cat = get_catalog()
    for t in cat.item_templates:
        if t.id == item_id:
            return t.item_type
    for ct in cat.combo_templates:
        if ct.id == item_id:
            return ct.item_type
    for gp in cat.group_pack_templates:
        if gp.id == item_id:
            return gp.item_type
    return None


def get_flavor_by_id(flavor_id: str) -> CatalogFlavor | None:
    """Look up a CatalogFlavor by id."""
    cat = get_catalog()
    for f in cat.flavors:
        if f.id == flavor_id:
            return f
    return None


def get_modifier_group_by_id(group_id: str) -> CatalogModifierGroup | None:
    """Look up a CatalogModifierGroup by id."""
    cat = get_catalog()
    for g in cat.modifier_groups:
        if g.id == group_id:
            return g
    return None


# ── Attempt to load catalog at import time (graceful fallback to hardcoded) ──

try:
    load_catalog()
except (FileNotFoundError, KeyError, json.JSONDecodeError):
    pass
