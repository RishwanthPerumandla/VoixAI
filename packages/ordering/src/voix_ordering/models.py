"""Pure data models for the VoixAI ordering domain.

These dataclasses carry no behavior and no third-party dependencies so they can
be imported by both ``apps/api`` and ``apps/agent-runtime`` without pulling in
LiveKit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


# ── Catalog-level models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class RestaurantProfile:
    name: str
    scenario: str
    disclaimer: str
    currency: str
    tax_rate: Decimal
    default_ready_minutes: int
    supports_pickup: bool
    supports_delivery: bool


@dataclass(frozen=True)
class CatalogFlavor:
    id: str
    name: str
    flavor_type: str
    heat_level: int
    available: bool = True
    aliases: tuple[str, ...] = ()
    allowed_for_item_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class CatalogModifierOption:
    id: str
    name: str
    price_delta: Decimal = Decimal("0.00")
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class CatalogModifierGroup:
    id: str
    name: str
    applies_to_item_types: tuple[str, ...] = ()
    required: bool = False
    max_select: int = 1
    options: tuple[CatalogModifierOption, ...] = ()


@dataclass(frozen=True)
class MainComponent:
    component_type: str
    piece_count: int = 0
    required: bool = True
    allow_classic: bool = True
    allow_boneless: bool = True


@dataclass(frozen=True)
class IncludedComponents:
    side_count: int = 0
    drink_count: int = 0
    dip_count: int = 0


@dataclass(frozen=True)
class ComboRules:
    allows_piece_preference: bool = False
    allows_all_flats: bool = False
    allows_all_drums: bool = False
    requires_side: bool = True
    requires_drink: bool = True


@dataclass(frozen=True)
class GroupPackRules:
    allows_piece_preference: bool = False
    requires_side: bool = False
    requires_drink: bool = False
    wing_type_required: bool = True


@dataclass(frozen=True)
class ItemTemplate:
    id: str
    name: str
    category_id: str
    item_type: str
    base_price: Decimal
    available: bool = True
    piece_count: int | None = None
    included_flavor_count: int = 0
    included_dip_count: int = 0
    max_flavors: int = 0
    required_slots: tuple[str, ...] = ()
    optional_slots: tuple[str, ...] = ()
    modifier_group_ids: tuple[str, ...] = ()
    prep_time_minutes: int = 15
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComboTemplate:
    id: str
    name: str
    category_id: str
    item_type: str
    base_price: Decimal
    available: bool = True
    main_component: MainComponent | None = None
    included_components: IncludedComponents | None = None
    max_flavors: int = 1
    required_slots: tuple[str, ...] = ()
    optional_slots: tuple[str, ...] = ()
    modifier_group_ids: tuple[str, ...] = ()
    rules: ComboRules | None = None
    prep_time_minutes: int = 18
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroupPackTemplate:
    id: str
    name: str
    category_id: str
    item_type: str
    base_price: Decimal
    available: bool = True
    main_component: MainComponent | None = None
    included_components: IncludedComponents | None = None
    max_flavors: int = 2
    serves: int = 2
    required_slots: tuple[str, ...] = ()
    optional_slots: tuple[str, ...] = ()
    modifier_group_ids: tuple[str, ...] = ()
    rules: GroupPackRules | None = None
    prep_time_minutes: int = 22
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Catalog:
    schema_version: str
    restaurant_profile: RestaurantProfile
    categories: tuple[dict[str, str], ...]  # id -> name
    flavors: tuple[CatalogFlavor, ...]
    modifier_groups: tuple[CatalogModifierGroup, ...]
    item_templates: tuple[ItemTemplate, ...]
    combo_templates: tuple[ComboTemplate, ...]
    group_pack_templates: tuple[GroupPackTemplate, ...]
    synonyms: tuple[dict[str, str], ...]


# ── Legacy models (kept for backward compatibility) ──────────────────────


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
class ReliabilityMetrics:
    correction_count: int = 0
    cancellation_count: int = 0
    validation_failure_count: int = 0
    clarification_count: int = 0
    unknown_item_count: int = 0
    handoff_required_count: int = 0
    duplicate_confirmation_prevented: int = 0
    final_status: str = "idle"


@dataclass(frozen=True)
class OrderIntent:
    name: str
    target_item: str | None = None
    target_item_id: str | None = None
    target_line_id: str | None = None
    target_modifier: str | None = None
    target_modifier_id: str | None = None
    replacement_value: str | None = None
    replacement_item_id: str | None = None
    quantity: int | None = None
    flavor_ids: tuple[str, ...] = ()
    add_modifier_ids: tuple[str, ...] = ()
    remove_modifier_ids: tuple[str, ...] = ()
    notes: str | None = None
    confidence: float = 1.0
    requires_clarification: bool = False
    clarification_question: str | None = None


@dataclass
class OrderEvent:
    type: str
    detail: str
    data: dict[str, object] = field(default_factory=dict)


@dataclass
class OrderState:
    items: list[OrderLineItem] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    quantity: int = 1
    order_type: str = "pickup"
    customer_name: str = ""
    phone: str = ""
    notes: str = ""
    status: str = "idle"
    confirmed: bool = False
    pickup_time: str | None = None
    language: str = "english"
    total_shown: bool = False
    recap_readback: bool = False
    pos_validation_passed: bool = False
    last_validation_errors: list[str] = field(default_factory=list)
    last_clarification_question: str | None = None
    recent_events: list[OrderEvent] = field(default_factory=list)
    archived_orders: list[dict[str, object]] = field(default_factory=list)
    metrics: ReliabilityMetrics = field(default_factory=ReliabilityMetrics)
