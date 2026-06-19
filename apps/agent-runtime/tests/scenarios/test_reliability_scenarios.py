import json
from pathlib import Path
from typing import Any

import pytest

from voix_ordering import OrderIntent, OrderState, replay_order_intents


CASES_PATH = Path(__file__).resolve().parent / "wingstop_reliability_cases.json"


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _build_initial_order(payload: dict[str, Any] | None) -> OrderState:
    payload = payload or {}
    order = OrderState()
    if "order_type" in payload:
        order.order_type = payload["order_type"]
    order.customer_name = payload.get("customer_name", "")
    order.phone = payload.get("phone", "")
    order.language = payload.get("language", "english")
    return order


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_reducer_reliability_scenarios(case: dict[str, Any]) -> None:
    order = _build_initial_order(case.get("initial_state"))
    intents = [
        OrderIntent(
            name=intent["name"],
            target_item=intent.get("target_item"),
            target_item_id=intent.get("target_item_id"),
            target_line_id=intent.get("target_line_id"),
            replacement_value=intent.get("replacement_value"),
            replacement_item_id=intent.get("replacement_item_id"),
            quantity=intent.get("quantity"),
            flavor_ids=tuple(intent.get("flavor_ids", [])),
            add_modifier_ids=tuple(intent.get("add_modifier_ids", [])),
            remove_modifier_ids=tuple(intent.get("remove_modifier_ids", [])),
            notes=intent.get("notes"),
            confidence=float(intent.get("confidence", 1.0)),
            requires_clarification=bool(intent.get("requires_clarification", False)),
            clarification_question=intent.get("clarification_question"),
        )
        for intent in case["intents"]
    ]

    result = replay_order_intents(intents, order=order)
    expected = case["expected"]
    final_order = result.order

    assert final_order.status == expected["status"]
    assert [line.item_id for line in final_order.items] == expected["line_item_ids"]
    assert [line.selected_modifier_ids for line in final_order.items] == expected["line_modifier_ids"]
    assert final_order.last_validation_errors == expected["validation_errors"]

    if "correction_count" in expected:
        assert final_order.metrics.correction_count == expected["correction_count"]
    if "cancellation_count" in expected:
        assert final_order.metrics.cancellation_count == expected["cancellation_count"]
    if "validation_failure_count" in expected:
        assert final_order.metrics.validation_failure_count == expected["validation_failure_count"]
    if "clarification_count" in expected:
        assert final_order.metrics.clarification_count == expected["clarification_count"]
    if "unknown_item_count" in expected:
        assert final_order.metrics.unknown_item_count == expected["unknown_item_count"]
    if "handoff_required_count" in expected:
        assert final_order.metrics.handoff_required_count == expected["handoff_required_count"]
    if "archived_order_count" in expected:
        assert len(final_order.archived_orders) == expected["archived_order_count"]

    if "clarification_fragment" in expected:
        assert final_order.last_clarification_question is not None
        assert expected["clarification_fragment"] in final_order.last_clarification_question

    event_types = [event.type for event in final_order.recent_events]
    for event_type in expected.get("event_types", []):
        assert event_type in event_types
