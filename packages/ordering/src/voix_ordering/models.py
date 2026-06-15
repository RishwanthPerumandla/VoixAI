"""Pure data models for the VoixAI ordering domain.

These dataclasses carry no behavior and no third-party dependencies so they can
be imported by both ``apps/api`` and ``apps/agent-runtime`` without pulling in
LiveKit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class FlavorOption:
    id: str
    display_name: str
    flavor_type: str
    heat_level: int
    available: bool = True
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModifierOption:
    id: str
    display_name: str
    price_delta: Decimal = Decimal("0.00")
    available: bool = True
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModifierGroup:
    id: str
    display_name: str
    required: bool
    min_selections: int
    max_selections: int
    option_ids: tuple[str, ...]


@dataclass(frozen=True)
class MenuItem:
    id: str
    display_name: str
    category: str
    base_price: Decimal
    available: bool = True
    aliases: tuple[str, ...] = ()
    required_modifier_group_ids: tuple[str, ...] = ()
    optional_modifier_group_ids: tuple[str, ...] = ()
    requires_flavors: bool = False
    max_flavors: int = 0
    included_dip_count: int = 0
    supports_piece_preference: bool = False
    allowed_piece_preference_ids: tuple[str, ...] = ()
    prep_time_minutes: int = 15
    order_style: str | None = None
    item_kind: str = "entree"


@dataclass
class OrderLineItem:
    line_id: str
    item_id: str
    quantity: int
    selected_flavor_ids: list[str] = field(default_factory=list)
    selected_modifier_ids: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class PriceLineItem:
    line_id: str
    name: str
    quantity: int
    unit_price: str
    line_subtotal: str
    breakdown: list[str] = field(default_factory=list)


@dataclass
class PriceQuote:
    subtotal: str
    tax: str
    total: str
    line_items: list[PriceLineItem]
    eta_minutes: int
    pricing_source: str = "demo_menu"


@dataclass
class MockOrder:
    order_number: str
    total: str
    summary: str
    kitchen_ticket: str


@dataclass
class OrderState:
    items: list[OrderLineItem] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    quantity: int = 1
    order_type: str | None = None
    customer_name: str = ""
    phone: str = ""
    notes: str = ""
    status: str = "collecting"
    confirmed: bool = False
    pickup_time: str | None = None
    language: str = "english"
    total_shown: bool = False
    recap_readback: bool = False
    pos_validation_passed: bool = False
    last_validation_errors: list[str] = field(default_factory=list)
