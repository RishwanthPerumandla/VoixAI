"""Pricing engine for the VoixAI ordering domain (pure, deterministic)."""

from __future__ import annotations

from decimal import Decimal

from .menu import MENU_ITEMS, MODIFIER_OPTIONS, _selected_by_group
from .models import OrderLineItem, OrderState, PriceLineItem, PriceQuote

TAX_RATE = Decimal("0.0825")


def _format_currency(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.01'))}"


def _chargeable_modifier_ids(line: OrderLineItem) -> list[str]:
    menu_item = MENU_ITEMS[line.item_id]
    included_dip_count = menu_item.included_dip_count
    chargeable_modifier_ids: list[str] = []
    dip_modifier_ids = _selected_by_group(line, "dip_selection")

    for modifier_id in line.selected_modifier_ids:
        if modifier_id in dip_modifier_ids and included_dip_count > 0:
            included_dip_count -= 1
            continue
        chargeable_modifier_ids.append(modifier_id)

    return chargeable_modifier_ids


def _price_line_item(line: OrderLineItem) -> PriceLineItem:
    menu_item = MENU_ITEMS[line.item_id]
    unit_total = menu_item.base_price
    breakdown = [f"base {menu_item.display_name}: {_format_currency(menu_item.base_price)}"]

    for modifier_id in _chargeable_modifier_ids(line):
        modifier = MODIFIER_OPTIONS[modifier_id]
        if modifier.price_delta:
            unit_total += modifier.price_delta
            breakdown.append(
                f"{modifier.display_name}: +{_format_currency(modifier.price_delta)}"
            )

    line_subtotal = unit_total * line.quantity
    return PriceLineItem(
        line_id=line.line_id,
        name=menu_item.display_name,
        quantity=line.quantity,
        unit_price=_format_currency(unit_total),
        line_subtotal=_format_currency(line_subtotal),
        breakdown=breakdown,
    )


def calculate_order_total(order: OrderState) -> Decimal:
    subtotal = Decimal("0.00")
    for line in order.items:
        line_item = _price_line_item(line)
        subtotal += Decimal(line_item.line_subtotal.replace("$", ""))
    tax = subtotal * TAX_RATE
    return subtotal + tax


def build_price_quote(order: OrderState) -> PriceQuote:
    line_items = [_price_line_item(line) for line in order.items]
    subtotal = sum(
        Decimal(line_item.line_subtotal.replace("$", "")) for line_item in line_items
    )
    tax = subtotal * TAX_RATE
    eta_minutes = max((MENU_ITEMS[line.item_id].prep_time_minutes for line in order.items), default=12)
    return PriceQuote(
        subtotal=_format_currency(subtotal),
        tax=_format_currency(tax),
        total=_format_currency(subtotal + tax),
        line_items=line_items,
        eta_minutes=eta_minutes,
    )
