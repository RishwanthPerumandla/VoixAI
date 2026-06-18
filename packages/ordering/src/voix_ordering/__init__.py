"""VoixAI ordering domain.

Single source of truth for the menu, pricing, validation, order state, and the
order state machine. Pure Python with no LiveKit dependency, so it can be
imported directly by both ``apps/api`` (HTTP layer) and ``apps/agent-runtime``
(agent tools). This replaces the old arrangement where the API side-loaded the
agent-runtime's scenario module via ``sys.modules`` stubs.
"""

from __future__ import annotations

from .confirmation import (
    _build_kitchen_ticket,
    _missing_confirmation_reasons,
    build_confirmation_summary,
    create_mock_order,
)
from .menu import (
    FLAVOR_OPTIONS,
    MENU_ITEMS,
    MODIFIER_GROUPS,
    MODIFIER_OPTIONS,
    STORE_HOURS,
    _flavor_names,
    _flavor_summary_line,
    _menu_summary_lines,
    _modifier_names,
    _normalize_lookup_key,
    _normalize_note,
    _resolve_flavor_id,
    _resolve_item_id,
    _resolve_modifier_id,
    _selected_by_group,
    _split_csv,
)
from .models import (
    FlavorOption,
    MenuItem,
    MockOrder,
    ModifierGroup,
    ModifierOption,
    OrderLineItem,
    OrderState,
    PriceLineItem,
    PriceQuote,
)
from .pricing import (
    TAX_RATE,
    build_price_quote,
    calculate_order_total,
)
from .serialization import (
    serialize_order_state,
    summarize_order_state,
)
from .state_machine import (
    OrderPhase,
    OrderStateMachine,
    SubmitDecision,
    derive_phase,
)
from .validation import (
    _validation_errors_for_line,
    validate_order,
)

__all__ = [
    # models
    "FlavorOption",
    "ModifierOption",
    "ModifierGroup",
    "MenuItem",
    "OrderLineItem",
    "PriceLineItem",
    "PriceQuote",
    "MockOrder",
    "OrderState",
    # menu data + lookups
    "FLAVOR_OPTIONS",
    "MODIFIER_OPTIONS",
    "MODIFIER_GROUPS",
    "MENU_ITEMS",
    "STORE_HOURS",
    # pricing
    "TAX_RATE",
    "build_price_quote",
    "calculate_order_total",
    # validation
    "validate_order",
    # serialization
    "serialize_order_state",
    "summarize_order_state",
    # confirmation
    "build_confirmation_summary",
    "create_mock_order",
    # state machine
    "OrderPhase",
    "OrderStateMachine",
    "SubmitDecision",
    "derive_phase",
]
