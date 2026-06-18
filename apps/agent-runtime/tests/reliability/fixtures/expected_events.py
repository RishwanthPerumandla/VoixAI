EXPECTED_REDUCER_EVENTS = {
    "intent_detected",
    "item_added",
    "item_removed",
    "item_replaced",
    "modifier_added",
    "modifier_removed",
    "invalid_modifier_removed",
    "validation_passed",
    "validation_failed",
    "clarification_required",
    "order_cancelled",
    "order_restarted",
    "handoff_required",
}

EXPECTED_SNAPSHOT_REASONS = {
    "order_state_updated",
    "order_item_removed",
    "order_cancelled",
    "order_restarted",
    "handoff_required",
    "price_quote_updated",
    "pricing_blocked",
    "confirmation_review_ready",
    "confirmation_review_blocked",
    "mock_order_created",
    "mock_order_blocked",
    "mock_order_duplicate_prevented",
}

PRIMARY_CATEGORIES = [
    "happy_paths",
    "corrections",
    "cancellations",
    "invalid_modifiers",
    "flavor_limits",
    "unknown_items",
    "ambiguous_phrasing",
    "bilingual",
    "confirmation_gate",
    "pricing_repricing",
    "session_lifecycle",
]

