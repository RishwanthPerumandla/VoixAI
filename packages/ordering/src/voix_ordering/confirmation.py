"""Confirmation checklist, recap building, and mock order creation (pure)."""

from __future__ import annotations

import random

from .menu import MENU_ITEMS, _flavor_names, _modifier_names
from .models import MockOrder, OrderState, PriceQuote
from .pricing import build_price_quote
from .serialization import summarize_order_state
from .validation import validate_order


def _missing_confirmation_reasons(order: OrderState) -> list[str]:
    reasons: list[str] = []
    if not order.confirmed:
        reasons.append("customer confirmation is missing")
    if not order.total_shown:
        reasons.append("the total has not been shown")
    if not order.recap_readback:
        reasons.append("the final recap has not been read back")
    if not order.pos_validation_passed:
        reasons.append("POS validation has not passed")
    if not order.order_type:
        reasons.append("the order type is missing")
    if order.order_type == "pickup" and not order.customer_name.strip():
        reasons.append("the pickup name is missing")
    return reasons


def build_confirmation_summary(order: OrderState, price_quote: PriceQuote | None = None) -> str:
    validation_errors = validate_order(order)
    if validation_errors:
        return "I still need to fix this order before I can place it: " + " ".join(validation_errors)

    quote = price_quote or build_price_quote(order)
    item_parts: list[str] = []
    for line in order.items:
        menu_item = MENU_ITEMS[line.item_id]
        description = f"{line.quantity} {menu_item.display_name}"
        flavors = _flavor_names(line.selected_flavor_ids)
        modifiers = _modifier_names(line.selected_modifier_ids)
        if flavors:
            description += f" with {', '.join(flavors)}"
        if modifiers:
            description += f", {', '.join(modifiers)}"
        item_parts.append(description)

    customer_bits: list[str] = []
    if order.customer_name:
        customer_bits.append(f"name {order.customer_name}")
    if order.phone:
        customer_bits.append(f"phone {order.phone}")

    customer_text = ""
    if customer_bits:
        customer_text = " " + ", ".join(customer_bits) + "."

    return (
        f"Your order is {', '.join(item_parts)}. "
        f"Total is {quote.total}. "
        f"This is for {order.order_type}.{customer_text} "
        f"Should I place it?"
    )


def _build_kitchen_ticket(order: OrderState, price_quote: PriceQuote, order_number: str) -> str:
    lines = ["VOIX WINGS DEMO", f"Order {order_number}", (order.order_type or "pickup").title(), ""]
    for line in order.items:
        menu_item = MENU_ITEMS[line.item_id]
        lines.append(f"{line.quantity}x {menu_item.display_name}")
        flavors = _flavor_names(line.selected_flavor_ids)
        if flavors:
            lines.append(f"Flavors: {', '.join(flavors)}")
        modifiers = _modifier_names(line.selected_modifier_ids)
        if modifiers:
            lines.append(f"Modifiers: {', '.join(modifiers)}")
        if line.notes:
            lines.append(f"Notes: {line.notes}")
        lines.append("")

    lines.append(f"Subtotal: {price_quote.subtotal}")
    lines.append(f"Tax: {price_quote.tax}")
    lines.append(f"Total: {price_quote.total}")
    lines.append(f"ETA: {price_quote.eta_minutes} minutes")
    return "\n".join(lines)


def create_mock_order(order: OrderState, price_quote: PriceQuote | None = None) -> MockOrder:
    quote = price_quote or build_price_quote(order)
    order_number = f"MOCK-{random.randint(10001, 99999)}"
    summary = summarize_order_state(order)
    return MockOrder(
        order_number=order_number,
        total=quote.total,
        summary=summary,
        kitchen_ticket=_build_kitchen_ticket(order, quote, order_number),
    )
