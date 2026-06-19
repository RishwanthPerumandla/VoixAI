"""Order validation for the VoixAI ordering domain (pure, deterministic)."""

from __future__ import annotations

from .menu import (
    FLAVOR_OPTIONS,
    MENU_ITEMS,
    MODIFIER_GROUPS,
    MODIFIER_OPTIONS,
    OPTION_TO_GROUP_IDS,
    _selected_by_group,
)
from .models import OrderLineItem, OrderState


def _validation_errors_for_line(line: OrderLineItem) -> list[str]:
    errors: list[str] = []
    menu_item = MENU_ITEMS.get(line.item_id)
    if menu_item is None or not menu_item.available:
        return ["That item is not available in this demo menu."]

    if line.quantity < 1:
        errors.append("Quantity must be at least one.")

    flavors = []
    for flavor_id in line.selected_flavor_ids:
        flavor = FLAVOR_OPTIONS.get(flavor_id)
        if flavor is None or not flavor.available:
            errors.append("That flavor is not available in this demo menu.")
        else:
            flavors.append(flavor)

    if menu_item.requires_flavors and not flavors:
        errors.append("Please choose a flavor for your wings.")

    if menu_item.max_flavors and len(flavors) > menu_item.max_flavors:
        errors.append(
            f"{menu_item.display_name} can include up to {menu_item.max_flavors} flavor"
            f"{'' if menu_item.max_flavors == 1 else 's'}."
        )

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
            if modifier_id == "all_flats":
                errors.append("All flats is only available for classic bone-in wings.")
            elif modifier_id == "all_drums":
                errors.append("All drums is only available for classic bone-in wings.")
            else:
                errors.append(f"{modifier.display_name} is not valid for {menu_item.display_name}.")

    for group_id in menu_item.required_modifier_group_ids:
        group = MODIFIER_GROUPS[group_id]
        selected = _selected_by_group(line, group_id)
        if len(selected) < group.min_selections:
            if group_id == "combo_drink_choice":
                errors.append("This combo requires a drink selection.")
            elif group_id == "combo_side_choice":
                errors.append("This combo requires a side selection.")
            else:
                errors.append(f"{group.display_name} is required.")

    for group_id in menu_item.required_modifier_group_ids + menu_item.optional_modifier_group_ids:
        group = MODIFIER_GROUPS[group_id]
        selected = _selected_by_group(line, group_id)
        if len(selected) > group.max_selections:
            errors.append(f"Please choose no more than {group.max_selections} option(s) for {group.display_name}.")

    return errors


def validate_order(order: OrderState) -> list[str]:
    errors: list[str] = []
    if not order.items:
        errors.append("Add at least one valid item before placing the order.")

    for line in order.items:
        errors.extend(_validation_errors_for_line(line))

    return errors
