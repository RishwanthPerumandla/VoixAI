"""The order-placement safety net.

Realtime models sometimes announce that an order is placed without ever calling
``create_mock_order``. ``maybe_autoplace_order`` must then place the order — but
ONLY through the same hard submit gate, so an unconfirmed/invalid order is never
persisted just because the model said the wrong thing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import scenarios.wingstop as ws  # noqa: E402
from voix_ordering import OrderLineItem, OrderState  # noqa: E402


def _submittable_order() -> OrderState:
    return OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=1,
                selected_flavor_ids=["lemon_pepper", "mango_habanero"],
            )
        ],
        order_type="pickup",
        customer_name="Cherry",
        confirmed=True,
        total_shown=True,
        recap_readback=True,
        pos_validation_passed=True,
        status="confirmed_pending_submit",
    )


def _fake_state(order: OrderState) -> SimpleNamespace:
    async def publish_snapshot(*, reason: str) -> None:  # noqa: ARG001
        return None

    return SimpleNamespace(
        order=order,
        mock_order=None,
        price_quote=None,
        room=SimpleNamespace(name="room-1"),
        publish_snapshot=publish_snapshot,
    )


def test_claim_phrases_match_realtime_paraphrases() -> None:
    assert ws.assistant_claimed_placement("I'm placing the order now. Ready for pickup in about 15 minutes.")
    assert ws.assistant_claimed_placement("Got it, your order was placed.")
    assert ws.assistant_claimed_placement("You're all set, Cherry!")
    assert ws.assistant_claimed_placement("I've placed your order.")
    assert not ws.assistant_claimed_placement("What flavor would you like on those wings?")
    assert not ws.assistant_claimed_placement("Would you like the total?")


def test_handoff_phrase_detectors_match_human_and_frustration_requests() -> None:
    assert ws.customer_requested_handoff("Can I talk to a real person?")
    assert ws.customer_requested_handoff("Get me a manager.")
    assert ws.customer_expressed_frustration("This is not working and I'm frustrated.")
    assert not ws.customer_requested_handoff("Can I get ranch with that?")
    assert not ws.customer_expressed_frustration("That sounds good.")


@pytest.mark.asyncio
async def test_autoplaces_valid_confirmed_order_when_model_skips_tool(monkeypatch) -> None:
    submitted = {"order_number": "MOCK-77777", "total": "$18.92", "kitchen_ticket": "TICKET"}

    async def fake_submit(room_name: str, order: OrderState) -> dict:
        return submitted

    monkeypatch.setattr(ws, "_submit_order_via_backend", fake_submit)

    state = _fake_state(_submittable_order())
    await ws.maybe_autoplace_order(state, "Got it, I'm placing the order now. Ready for pickup in about 15 minutes.")

    assert state.mock_order is not None
    assert state.mock_order.order_number == "MOCK-77777"
    assert state.mock_order.total == "$18.92"


@pytest.mark.asyncio
async def test_never_autoplaces_an_unconfirmed_order(monkeypatch) -> None:
    calls: list[int] = []

    async def fake_submit(room_name: str, order: OrderState) -> dict:
        calls.append(1)
        return {}

    monkeypatch.setattr(ws, "_submit_order_via_backend", fake_submit)

    order = _submittable_order()
    order.confirmed = False  # customer never confirmed -> gate must block
    state = _fake_state(order)
    await ws.maybe_autoplace_order(state, "Your order was placed.")

    assert state.mock_order is None
    assert calls == []


@pytest.mark.asyncio
async def test_no_placement_claim_does_nothing(monkeypatch) -> None:
    calls: list[int] = []

    async def fake_submit(room_name: str, order: OrderState) -> dict:
        calls.append(1)
        return {}

    monkeypatch.setattr(ws, "_submit_order_via_backend", fake_submit)

    state = _fake_state(_submittable_order())
    await ws.maybe_autoplace_order(state, "What else can I get for you?")

    assert state.mock_order is None
    assert calls == []


@pytest.mark.asyncio
async def test_autoplace_recovers_missing_order_state_from_transcript(monkeypatch) -> None:
    submitted = {"order_number": "MOCK-88888", "total": "$63.86", "kitchen_ticket": "TICKET"}

    async def fake_submit(room_name: str, order: OrderState) -> dict:
        assert room_name == "room-1"
        assert order.order_type == "pickup"
        assert order.customer_name == "Cherry"
        assert [line.item_id for line in order.items] == ["boneless_50"]
        assert order.items[0].selected_flavor_ids == ["lemon_pepper", "original_hot"]
        return submitted

    monkeypatch.setattr(ws, "_submit_order_via_backend", fake_submit)

    state = _fake_state(OrderState())
    state.transcript = [
        {
            "role": "assistant",
            "text": (
                "Got it. So, that's 50 boneless wings, half Lemon Pepper, half Original Hot, "
                "for pickup for Cherry. Your total is $63.86. Should I place that order for you?"
            ),
            "ts": 1.0,
        },
        {
            "role": "user",
            "text": "Yes, please place that.",
            "ts": 2.0,
        },
    ]

    await ws.maybe_autoplace_order(
        state,
        "Got it, placing it. Your order was placed. Ready for pickup in about 15 minutes.",
    )

    assert state.mock_order is not None
    assert state.mock_order.order_number == "MOCK-88888"
