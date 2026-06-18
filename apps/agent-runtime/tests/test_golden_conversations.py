import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import scenarios.wingstop as wingstop_module

from channels import get_channel_definition
from scenarios.wingstop import (
    MENU_ITEMS,
    MockOrder,
    OrderState,
    OrderStateMachine,
    PriceQuote,
    WingstopAssistant,
    _resolve_flavor_id,
    _resolve_item_id,
    _resolve_modifier_id,
)
from voix_ordering import OrderLineItem, build_confirmation_summary, build_price_quote, validate_order
from voix_ordering.validation import _validation_errors_for_line


EVALS_PATH = Path(__file__).resolve().parents[1] / "evals" / "wingstop_regressions.json"


def _load_eval_cases() -> list[dict[str, Any]]:
    return json.loads(EVALS_PATH.read_text(encoding="utf-8"))


async def _resolve_selection_locally(
    *,
    item_name: str,
    quantity: int = 1,
    flavors: list[str] | None = None,
    modifiers: list[str] | None = None,
    special_instructions: str | None = None,
    validate_line: bool = True,
) -> dict[str, object]:
    item_id = _resolve_item_id(item_name)
    if item_id is None:
        return {
            "line_errors": ["That item is not available in this demo menu."],
            "suggestions": [],
        }

    flavor_ids: list[str] = []
    flavor_names: list[str] = []
    line_errors: list[str] = []
    for flavor_name in flavors or []:
        flavor_id = _resolve_flavor_id(flavor_name)
        if flavor_id is None:
            line_errors.append(f"{flavor_name} is not available in this demo menu.")
            continue
        if flavor_id not in flavor_ids:
            flavor_ids.append(flavor_id)
            flavor_names.append(flavor_id)

    modifier_ids: list[str] = []
    modifier_names: list[str] = []
    for modifier_name in modifiers or []:
        modifier_id = _resolve_modifier_id(modifier_name)
        if modifier_id is None:
            line_errors.append(f"{modifier_name} is not a valid option for this demo menu.")
            continue
        if modifier_id not in modifier_ids:
            modifier_ids.append(modifier_id)
            modifier_names.append(modifier_id)

    if not line_errors and validate_line:
        preview_line = OrderLineItem(
            line_id="line-preview",
            item_id=item_id,
            quantity=quantity,
            selected_flavor_ids=flavor_ids,
            selected_modifier_ids=modifier_ids,
            notes=(special_instructions or "").strip(),
        )
        line_errors = _validation_errors_for_line(preview_line)

    return {
        "item_id": item_id,
        "item_name": MENU_ITEMS[item_id].display_name,
        "flavor_ids": flavor_ids,
        "flavor_names": flavor_names,
        "modifier_ids": modifier_ids,
        "modifier_names": modifier_names,
        "line_errors": line_errors,
        "suggestions": [],
    }


async def _validate_order_locally(order: OrderState) -> list[str]:
    return validate_order(order)


async def _price_order_locally(order: OrderState) -> tuple[list[str], PriceQuote | None]:
    errors = validate_order(order)
    return errors, (None if errors else build_price_quote(order))


async def _submit_order_locally(room_name: str, order: OrderState) -> dict[str, object]:
    quote = build_price_quote(order)
    ticket = build_confirmation_summary(order, quote)
    return {
        "order_number": f"EVAL-{room_name.upper()}",
        "status": "submitted",
        "subtotal": quote.subtotal,
        "tax": quote.tax,
        "total": quote.total,
        "eta_minutes": quote.eta_minutes,
        "kitchen_ticket": ticket,
    }


def _build_session_state() -> Any:
    session_state = SimpleNamespace(
        order=OrderState(),
        price_quote=None,
        mock_order=None,
        waiting_for_customer=False,
        room=SimpleNamespace(name="eval-room"),
    )

    async def publish_snapshot(*, reason: str) -> None:
        _ = reason

    session_state.publish_snapshot = publish_snapshot
    return session_state


async def _run_eval_case(
    case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, list[str]]:
    monkeypatch.setattr(wingstop_module, "_resolve_selection_via_backend", _resolve_selection_locally)
    monkeypatch.setattr(wingstop_module, "_validate_order_via_backend", _validate_order_locally)
    monkeypatch.setattr(wingstop_module, "_price_order_via_backend", _price_order_locally)
    monkeypatch.setattr(wingstop_module, "_submit_order_via_backend", _submit_order_locally)

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    session_state = _build_session_state()
    context = SimpleNamespace(userdata=session_state)
    responses: list[str] = []

    for step in case["steps"]:
        tool = getattr(assistant, step["tool"])
        response = await tool(context, **step["kwargs"])
        responses.append(response)
        for text in step.get("response_contains", []):
            assert text in response, f"{case['name']}: expected '{text}' in '{response}'"
        for text in step.get("response_not_contains", []):
            assert text not in response, f"{case['name']}: did not expect '{text}' in '{response}'"

    return session_state, responses


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_eval_cases(), ids=lambda case: case["name"])
async def test_wingstop_golden_conversations(
    case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state, _responses = await _run_eval_case(case, monkeypatch)
    expected = case["expected"]

    order = session_state.order
    assert order.order_type == expected["order_type"]
    assert order.customer_name == expected["customer_name"]
    assert len(order.items) == expected["line_count"]
    assert [line.item_id for line in order.items] == expected["line_item_ids"]
    assert [line.selected_flavor_ids for line in order.items] == expected["line_flavor_ids"]
    assert [line.selected_modifier_ids for line in order.items] == expected["line_modifier_ids"]
    assert order.status == expected["status"]
    assert order.confirmed is expected["confirmed"]
    assert validate_order(order) == expected["validation_errors"]

    if "total" in expected:
        assert session_state.price_quote is not None
        assert session_state.price_quote.total == expected["total"]

    if expected["status"] == "submitted":
        assert session_state.mock_order is not None
        assert isinstance(session_state.mock_order, MockOrder)
        assert OrderStateMachine(order).phase.value == "submitted"
