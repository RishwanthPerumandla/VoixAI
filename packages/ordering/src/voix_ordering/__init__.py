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
from .intents import (
    INTENT_ADD_ITEM,
    INTENT_ASK_MENU,
    INTENT_ASK_TOTAL,
    INTENT_CANCEL_ORDER,
    INTENT_CHANGE_COOK_PREFERENCE,
    INTENT_CHANGE_FLAVOR,
    INTENT_CHANGE_PIECE_PREFERENCE,
    INTENT_CHANGE_QUANTITY,
    INTENT_COMPLAINT,
    INTENT_CONFIRM_ORDER,
    INTENT_HANDOFF_REQUEST,
    INTENT_MODIFY_ITEM,
    INTENT_REMOVE_ITEM,
    INTENT_REPLACE_ITEM,
    INTENT_RESTART_ORDER,
    INTENT_UNKNOWN,
    SUPPORTED_INTENTS,
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
    get_catalog,
    load_catalog,
)
from .models import (
    Catalog,
    CatalogFlavor,
    CatalogModifierGroup,
    CatalogModifierOption,
    ComboTemplate,
    ComboRules,
    GroupPackTemplate,
    GroupPackRules,
    IncludedComponents,
    ItemTemplate,
    MainComponent,
    RestaurantProfile,
    FlavorOption,
    MenuItem,
    MockOrder,
    ModifierGroup,
    ModifierOption,
    OrderEvent,
    OrderIntent,
    OrderLineItem,
    OrderState,
    PriceLineItem,
    PriceQuote,
    ReliabilityMetrics,
)
from .pricing import (
    TAX_RATE,
    build_price_quote,
    calculate_order_total,
)
from .reducer import (
    ReducerResult,
    apply_order_intent,
)
from .replay import (
    ReplayResult,
    replay_order_intents,
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
    # catalog models
    "Catalog",
    "CatalogFlavor",
    "CatalogModifierGroup",
    "CatalogModifierOption",
    "ComboTemplate",
    "ComboRules",
    "GroupPackTemplate",
    "GroupPackRules",
    "IncludedComponents",
    "ItemTemplate",
    "MainComponent",
    "RestaurantProfile",
    # legacy models
    "FlavorOption",
    "ModifierOption",
    "ModifierGroup",
    "MenuItem",
    "OrderLineItem",
    "PriceLineItem",
    "PriceQuote",
    "MockOrder",
    "OrderState",
    "OrderIntent",
    "OrderEvent",
    "ReliabilityMetrics",
    # menu data + lookups
    "FLAVOR_OPTIONS",
    "MODIFIER_OPTIONS",
    "MODIFIER_GROUPS",
    "MENU_ITEMS",
    "STORE_HOURS",
    "get_catalog",
    "load_catalog",
    # pricing
    "TAX_RATE",
    "build_price_quote",
    "calculate_order_total",
    # intents + reducer
    "INTENT_ADD_ITEM",
    "INTENT_REMOVE_ITEM",
    "INTENT_REPLACE_ITEM",
    "INTENT_MODIFY_ITEM",
    "INTENT_CHANGE_QUANTITY",
    "INTENT_CHANGE_FLAVOR",
    "INTENT_CHANGE_COOK_PREFERENCE",
    "INTENT_CHANGE_PIECE_PREFERENCE",
    "INTENT_ASK_TOTAL",
    "INTENT_ASK_MENU",
    "INTENT_CONFIRM_ORDER",
    "INTENT_CANCEL_ORDER",
    "INTENT_RESTART_ORDER",
    "INTENT_HANDOFF_REQUEST",
    "INTENT_COMPLAINT",
    "INTENT_UNKNOWN",
    "SUPPORTED_INTENTS",
    "ReducerResult",
    "apply_order_intent",
    "ReplayResult",
    "replay_order_intents",
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
