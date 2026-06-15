"""Tests for the deterministic order state machine (M2).

These lock in the core production-reliability guarantee: an order can only be
submitted when it is genuinely valid *and* confirmed, regardless of which flags
happen to be set on the order.
"""

from __future__ import annotations

from voix_ordering import (
    OrderLineItem,
    OrderPhase,
    OrderState,
    OrderStateMachine,
    build_price_quote,
    derive_phase,
)


def _valid_line() -> OrderLineItem:
    return OrderLineItem(
        line_id="line-1",
        item_id="boneless_6",
        quantity=1,
        selected_flavor_ids=["cajun"],
    )


def test_phase_starts_at_greeting_then_collecting() -> None:
    order = OrderState()
    assert derive_phase(order) is OrderPhase.GREETING

    order.items.append(_valid_line())
    order.order_type = "pickup"
    assert derive_phase(order) is OrderPhase.COLLECTING


def test_lifecycle_priced_reviewed_confirmed() -> None:
    order = OrderState(items=[_valid_line()], order_type="pickup", customer_name="Sam")
    machine = OrderStateMachine(order)

    machine.mark_priced()
    assert machine.phase is OrderPhase.PRICED

    machine.mark_reviewed()
    assert machine.phase is OrderPhase.AWAITING_CONFIRMATION

    machine.set_confirmed(True)
    assert machine.phase is OrderPhase.CONFIRMED


def test_any_mutation_resets_to_collecting() -> None:
    order = OrderState(items=[_valid_line()], order_type="pickup", customer_name="Sam")
    machine = OrderStateMachine(order)
    machine.mark_reviewed()
    machine.set_confirmed(True)

    machine.reset_to_collecting()

    assert order.confirmed is False
    assert order.total_shown is False
    assert order.recap_readback is False
    assert order.pos_validation_passed is False
    assert machine.phase is OrderPhase.COLLECTING


def test_authorize_submit_blocks_invalid_order() -> None:
    # Missing flavor on an item that requires one.
    order = OrderState(
        items=[OrderLineItem(line_id="line-1", item_id="boneless_6", quantity=1)],
        order_type="pickup",
        customer_name="Sam",
        confirmed=True,
        total_shown=True,
        recap_readback=True,
    )
    decision = OrderStateMachine(order).authorize_submit()

    assert not decision.authorized
    assert decision.validation_errors
    # When validation fails we don't even compute confirmation reasons.
    assert decision.confirmation_reasons == []


def test_authorize_submit_blocks_unconfirmed_order() -> None:
    order = OrderState(items=[_valid_line()], order_type="pickup", customer_name="Sam")
    # Valid order, but the customer never confirmed and nothing was reviewed.
    decision = OrderStateMachine(order).authorize_submit()

    assert not decision.authorized
    assert decision.validation_errors == []
    assert "customer confirmation is missing" in decision.confirmation_reasons


def test_authorize_submit_authorizes_valid_confirmed_order() -> None:
    order = OrderState(items=[_valid_line()], order_type="pickup", customer_name="Sam")
    machine = OrderStateMachine(order)
    # Walk the real path: price -> review -> confirm.
    machine.mark_priced()
    machine.mark_reviewed()
    machine.set_confirmed(True)

    decision = machine.authorize_submit()

    assert decision.authorized
    assert decision.validation_errors == []
    assert decision.confirmation_reasons == []
    # A quote can be produced for an authorized order.
    assert build_price_quote(order).total.startswith("$")


def test_pickup_requires_name_before_submit() -> None:
    order = OrderState(items=[_valid_line()], order_type="pickup")
    machine = OrderStateMachine(order)
    machine.mark_priced()
    machine.mark_reviewed()
    machine.set_confirmed(True)

    decision = machine.authorize_submit()

    assert not decision.authorized
    assert "the pickup name is missing" in decision.confirmation_reasons
