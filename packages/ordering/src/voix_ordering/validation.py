"""Order validation for the VoixAI ordering domain (pure, deterministic).

Enforces the POS-grade validation rules defined in the catalog:
  - item/template exists and is available
  - required slots must be filled
  - flavors are valid, available, and allowed for the item type
  - modifiers are valid, available, and allowed for the item type
  - piece preference (all_flats/all_drums) only for classic_wings
  - cook preference only for applicable item types
  - combo requires side and drink
  - group pack requires wing type
  - flavor count within max
"""

from __future__ import annotations

from .menu import (
    FLAVOR_OPTIONS,
    MENU_ITEMS,
    MODIFIER_GROUPS,
    MODIFIER_OPTIONS,
    OPTION_TO_GROUP_IDS,
    _get_max_flavors,
    _selected_by_group,
    get_catalog,
    get_combo_template,
    get_group_pack_template,
    get_item_template,
    get_item_type,
    get_flavor_by_id,
    get_modifier_group_by_id,
)
from .models import OrderLineItem, OrderState


def _flavor_validation_item_type(item_id: str) -> str | None:
    item_type = get_item_type(item_id)
    if item_type == "combo":
        combo_tpl = get_combo_template(item_id)
        if combo_tpl and combo_tpl.main_component:
            return combo_tpl.main_component.component_type
    if item_type == "group_pack":
        pack_tpl = get_group_pack_template(item_id)
        if pack_tpl and pack_tpl.main_component:
            component_type = pack_tpl.main_component.component_type
            if component_type == "classic_or_boneless_choice":
                return "classic_wings"
            return component_type
    return item_type


def _get_required_slots(item_id: str) -> list[str]:
    """Resolve required slots from catalog templates."""
    cat_tpl = get_item_template(item_id)
    if cat_tpl:
        return list(cat_tpl.required_slots)
    combo_tpl = get_combo_template(item_id)
    if combo_tpl:
        return list(combo_tpl.required_slots)
    pack_tpl = get_group_pack_template(item_id)
    if pack_tpl:
        return [
            slot
            for slot in pack_tpl.required_slots
            if slot != "combo_side_selection"
        ]
    return []


def _item_type_allows_flavor(item_type: str | None) -> bool:
    if item_type is None:
        return False
    return item_type in {"classic_wings", "boneless_wings", "crispy_tenders", "chicken_sandwich"}


def _item_type_allows_piece_preference(item_type: str | None) -> bool:
    return item_type == "classic_wings"


def _item_type_allows_cook_preference(item_type: str | None) -> bool:
    if item_type is None:
        return False
    return item_type in {"classic_wings", "boneless_wings", "crispy_tenders", "fries"}


def _item_type_allows_dip_selection(item_type: str | None) -> bool:
    if item_type is None:
        return False
    return item_type in {
        "classic_wings", "boneless_wings", "crispy_tenders",
        "chicken_sandwich", "combo", "group_pack", "sides",
    }


def _slot_group_id(slot_name: str) -> str | None:
    mapping = {
        "flavor_selection": None,
        "piece_preference": "wing_piece_preference",
        "wing_cook_preference": "wing_cook_preference",
        "dip_selection": "dip_selection",
        "combo_side_selection": "combo_side_choice",
        "combo_drink_selection": "combo_drink_choice",
        "fry_cook_preference": "fry_cook_preference",
        "fry_seasoning_level": "fry_seasoning_level",
        "fry_add_ons": "fry_add_ons",
    }
    return mapping.get(slot_name)


def _modifiers_for_slot(line: OrderLineItem, slot_name: str) -> list[str]:
    """Return the modifier ids that belong to a named slot."""
    group_id = _slot_group_id(slot_name)
    if group_id is None:
        # flavor_selection has no modifier group
        return []
    return _selected_by_group(line, group_id)


def _validation_errors_for_line(line: OrderLineItem) -> list[str]:
    errors: list[str] = []
    menu_item = MENU_ITEMS.get(line.item_id)
    if menu_item is None or not menu_item.available:
        return ["That item is not available in this demo menu."]

    if line.quantity < 1:
        errors.append("Quantity must be at least one.")

    item_type = get_item_type(line.item_id)
    flavor_item_type = _flavor_validation_item_type(line.item_id)

    # --- Flavor validation ---
    flavors = []
    required_slots = _get_required_slots(line.item_id)
    for flavor_id in line.selected_flavor_ids:
        flavor = FLAVOR_OPTIONS.get(flavor_id)
        cat_flavor = get_flavor_by_id(flavor_id)
        if flavor is None or not flavor.available:
            errors.append("That flavor is not available in this demo menu.")
            continue
        flavors.append(flavor)
        # Catalog-level: flavor must be allowed for item type
        if cat_flavor and flavor_item_type and cat_flavor.allowed_for_item_types:
            if flavor_item_type not in cat_flavor.allowed_for_item_types:
                errors.append(
                    f"{flavor.display_name} is not available for {menu_item.display_name}."
                )

    if (
        menu_item.requires_flavors
        and "flavor_selection" not in required_slots
        and not flavors
    ):
        errors.append("Please choose a flavor for your wings.")

    max_flavors = _get_max_flavors(line.item_id)
    if max_flavors and len(flavors) > max_flavors:
        errors.append(
            f"{menu_item.display_name} can include up to {max_flavors} flavor"
            f"{'' if max_flavors == 1 else 's'}."
        )

    # --- Required slots validation ---
    for slot_name in required_slots:
        if slot_name == "flavor_selection":
            if not flavors:
                errors.append("Please choose a flavor for your wings.")
            continue
        group_id = _slot_group_id(slot_name)
        if group_id is None:
            continue
        selected = _selected_by_group(line, group_id)
        if not selected:
            if group_id == "combo_side_choice":
                errors.append("This combo requires a side selection.")
            elif group_id == "combo_drink_choice":
                errors.append("This combo requires a drink selection.")
            else:
                errors.append(f"{slot_name} is required for {menu_item.display_name}.")

    # --- Modifier validation ---
    for modifier_id in line.selected_modifier_ids:
        modifier = MODIFIER_OPTIONS.get(modifier_id)
        if modifier is None or not modifier.available:
            errors.append("That modifier is not available in this demo menu.")
            continue

        modifier_group_ids = OPTION_TO_GROUP_IDS.get(modifier_id, set())
        allowed_groups = set(menu_item.required_modifier_group_ids) | set(
            menu_item.optional_modifier_group_ids
        )
        if modifier_group_ids.isdisjoint(allowed_groups):
            # Check item-type-level rules for precise messages
            if modifier_id in ("all_flats", "all_drums"):
                if item_type and not _item_type_allows_piece_preference(item_type):
                    if modifier_id == "all_flats":
                        errors.append("All flats is only available for classic bone-in wings.")
                    else:
                        errors.append("All drums is only available for classic bone-in wings.")
                else:
                    errors.append(f"{modifier.display_name} is not valid for {menu_item.display_name}.")
            elif modifier_id in ("well_done", "extra_crispy", "regular_cook"):
                if item_type and item_type in {"drinks", "desserts", "sides"}:
                    if modifier_id == "well_done":
                        errors.append(f"Drinks and desserts cannot be well done.")
                    elif modifier_id == "extra_crispy":
                        errors.append(f"Drinks and desserts cannot be extra crispy.")
                else:
                    errors.append(f"{modifier.display_name} is not valid for {menu_item.display_name}.")
            else:
                errors.append(f"{modifier.display_name} is not valid for {menu_item.display_name}.")

    # --- Group max selections ---
    for group_id in menu_item.required_modifier_group_ids + menu_item.optional_modifier_group_ids:
        group = MODIFIER_GROUPS.get(group_id)
        if group is None:
            continue
        selected = _selected_by_group(line, group_id)
        if len(selected) > group.max_selections:
            if group.max_selections == 1:
                errors.append(f"Please choose no more than one option for {group.display_name}.")
            else:
                errors.append(f"Please choose no more than {group.max_selections} options for {group.display_name}.")

    return errors


def validate_order(order: OrderState) -> list[str]:
    errors: list[str] = []
    if not order.items:
        errors.append("Add at least one valid item before placing the order.")

    for line in order.items:
        errors.extend(_validation_errors_for_line(line))

    return errors
