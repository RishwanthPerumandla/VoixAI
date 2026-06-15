"""Menu data and lookups for the VoixAI ordering domain.

This module is the single source of truth for the ``Voix Wings Demo`` menu.
Today the menu is declared as Python literals; the seam to replace is the data
in this module (a future ``MenuRepository`` can load it from a DB/seed without
changing any consumer that imports the lookups below).
"""

from __future__ import annotations

import re
from decimal import Decimal

from .models import (
    FlavorOption,
    MenuItem,
    ModifierGroup,
    ModifierOption,
    OrderLineItem,
)

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
        aliases=("ranch", "add ranch"),
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
        aliases=("6 bone in wings", "six bone in wings", "6 regular wings", "six classic wings"),
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
        aliases=("6 boneless wings", "six boneless wings", "boneless"),
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
        aliases=("seasoned fries", "regular fries"),
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

for modifier in MODIFIER_OPTIONS.values():
    MODIFIER_ALIAS_TO_ID[_normalize_lookup_key(modifier.display_name)] = modifier.id
    for alias in modifier.aliases:
        MODIFIER_ALIAS_TO_ID[_normalize_lookup_key(alias)] = modifier.id

for group in MODIFIER_GROUPS.values():
    for option_id in group.option_ids:
        OPTION_TO_GROUP_IDS.setdefault(option_id, set()).add(group.id)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _normalize_note(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()


def _resolve_item_id(name: str) -> str | None:
    return ITEM_ALIAS_TO_ID.get(_normalize_lookup_key(name))


def _resolve_flavor_id(name: str) -> str | None:
    return FLAVOR_ALIAS_TO_ID.get(_normalize_lookup_key(name))


def _resolve_modifier_id(name: str) -> str | None:
    return MODIFIER_ALIAS_TO_ID.get(_normalize_lookup_key(name))


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
