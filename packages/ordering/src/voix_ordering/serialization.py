"""Order serialization and human-readable summaries (pure)."""

from __future__ import annotations

from dataclasses import asdict

from .menu import (
    MENU_ITEMS,
    OPTION_TO_GROUP_IDS,
    MODIFIER_OPTIONS,
    _flavor_names,
    _modifier_names,
)
from .models import OrderLineItem, OrderState
from .state_machine import derive_phase


def _get_primary_style(order: OrderState) -> str | None:
    for line in order.items:
        style = MENU_ITEMS[line.item_id].order_style
        if style:
            return style
    return None


def _get_primary_flavor(order: OrderState) -> str | None:
    for line in order.items:
        if line.selected_flavor_ids:
            return ", ".join(_flavor_names(line.selected_flavor_ids))
    return None


def _get_primary_drink(order: OrderState) -> str | None:
    for line in order.items:
        menu_item = MENU_ITEMS[line.item_id]
        if menu_item.item_kind == "drink":
            return menu_item.display_name

        for modifier_id in line.selected_modifier_ids:
            if "combo_drink_choice" in OPTION_TO_GROUP_IDS.get(modifier_id, set()):
                return MODIFIER_OPTIONS[modifier_id].display_name
    return None


def _serialize_line_item(line: OrderLineItem) -> dict[str, object]:
    menu_item = MENU_ITEMS[line.item_id]
    return {
        "line_id": line.line_id,
        "item_id": line.item_id,
        "name": menu_item.display_name,
        "category": menu_item.category,
        "quantity": line.quantity,
        "flavors": _flavor_names(line.selected_flavor_ids),
        "modifiers": _modifier_names(line.selected_modifier_ids),
        "notes": line.notes or None,
        "style": menu_item.order_style,
    }


def serialize_order_state(order: OrderState, *, include_history: bool = True) -> dict[str, object]:
    """Serialize the order for telemetry/inspection.

    ``include_history=False`` omits ``recent_events``. This is essential when the
    result is itself stored *inside* an event (a before/after snapshot) or an
    archived order — otherwise each event embeds the whole event log, which
    embeds prior snapshots, and the payload grows exponentially per mutation.
    """
    payload: dict[str, object] = {
        "items": [MENU_ITEMS[line.item_id].display_name for line in order.items],
        "line_items": [_serialize_line_item(line) for line in order.items],
        "modifiers": order.modifiers,
        "quantity": sum(line.quantity for line in order.items) or order.quantity,
        "order_type": order.order_type,
        "pickup_or_delivery": order.order_type,
        "customer_name": order.customer_name or None,
        "phone": order.phone or None,
        "notes": order.notes or None,
        "status": order.status,
        "phase": derive_phase(order).value,
        "confirmed": order.confirmed,
        "pickup_time": order.pickup_time,
        "language": order.language,
        "total_shown": order.total_shown,
        "recap_readback": order.recap_readback,
        "pos_validation_passed": order.pos_validation_passed,
        "validation_errors": list(order.last_validation_errors),
        "last_clarification_question": order.last_clarification_question,
        "reliability_metrics": asdict(order.metrics),
        "archived_order_count": len(order.archived_orders),
        "flavor": _get_primary_flavor(order),
        "classic_or_boneless": _get_primary_style(order),
        "drink": _get_primary_drink(order),
    }
    if include_history:
        payload["recent_events"] = [asdict(event) for event in order.recent_events[-10:]]
    return payload


def summarize_order_state(order: OrderState) -> str:
    if not order.items:
        return "No order details yet."

    line_summaries: list[str] = []
    for line in order.items:
        menu_item = MENU_ITEMS[line.item_id]
        detail_parts: list[str] = [f"{line.quantity} {menu_item.display_name}"]
        flavors = _flavor_names(line.selected_flavor_ids)
        modifiers = _modifier_names(line.selected_modifier_ids)
        if flavors:
            detail_parts.append(f"flavors: {', '.join(flavors)}")
        if modifiers:
            detail_parts.append(f"modifiers: {', '.join(modifiers)}")
        if line.notes:
            detail_parts.append(f"notes: {line.notes}")
        line_summaries.append(", ".join(detail_parts))

    summary_parts = [f"order type: {order.order_type or 'not set'}", f"items: {'; '.join(line_summaries)}"]
    if order.customer_name:
        summary_parts.append(f"name: {order.customer_name}")
    if order.phone:
        summary_parts.append(f"phone: {order.phone}")
    if order.notes:
        summary_parts.append(f"notes: {order.notes}")
    summary_parts.append(f"status: {order.status}")
    return "Current order: " + ". ".join(summary_parts) + "."
