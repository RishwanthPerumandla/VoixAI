from __future__ import annotations

from unittest.mock import MagicMock

from conversation_core.order_fsm import OrderSubFSM, OrderSubNode
from conversation_core.state_machine import ConversationContext, NodeName


def _make_context() -> ConversationContext:
    return ConversationContext(call_id="test-call", room_name="test-room")


def _make_order(items: list | None = None) -> MagicMock:
    order = MagicMock()
    order.items = items or []
    return order


def _make_line_item(item_id: str, **kwargs) -> MagicMock:
    line = MagicMock()
    line.item_id = item_id
    for k, v in kwargs.items():
        setattr(line, k, v)
    return line


def test_select_item_empty_order_asks_what_to_order() -> None:
    order = _make_order()
    fsm = OrderSubFSM(_make_context())

    action = fsm.handle_turn(_make_context(), order, "I want wings")

    assert action.message == "What would you like to order today?"
    assert action.node == NodeName.ORDER
    assert fsm.state.value == "SELECT_ITEM"


def test_select_item_with_items_transitions_to_configure() -> None:
    order = _make_order([
        _make_line_item("classic_10", selected_flavor_ids=[], selected_modifier_ids=[])
    ])
    fsm = OrderSubFSM(_make_context())

    action = fsm.handle_turn(_make_context(), order, "I want wings")

    assert fsm.state.value == "CONFIGURE_ITEM"


def test_configure_item_asks_for_missing_flavor() -> None:
    line = _make_line_item("classic_10", selected_flavor_ids=[], selected_modifier_ids=[])
    order = _make_order([line])
    fsm = OrderSubFSM(_make_context())

    # Start with SELECT_ITEM
    fsm.handle_turn(_make_context(), order, "I want wings")

    # Now in CONFIGURE_ITEM
    action = fsm.handle_turn(_make_context(), order, "lemon pepper")

    assert fsm.state.value == "CONFIGURE_ITEM"


def test_configure_item_with_flavor_proceeds_to_review() -> None:
    line = _make_line_item(
        "classic_10",
        selected_flavor_ids=["lemon_pepper"],
        selected_modifier_ids=["ranch"],
    )
    order = _make_order([line])
    fsm = OrderSubFSM(_make_context())
    fsm._state = OrderSubNode.CONFIGURE_ITEM

    # All slots filled → "anything else?"
    action = fsm.handle_turn(_make_context(), order, "lemon pepper")

    assert fsm.state.value == "CONFIGURE_ITEM"
    assert "anything else" in action.message.lower()

    # Say no → transitions to REVIEW/CONFIRM
    action = fsm.handle_turn(_make_context(), order, "no that's it")

    assert fsm.state.value in ("CONFIRM",)


def test_cancel_mid_order_returns_to_route() -> None:
    order = _make_order([
        _make_line_item("classic_10", selected_flavor_ids=[], selected_modifier_ids=[])
    ])
    fsm = OrderSubFSM(_make_context())

    action = fsm.handle_turn(_make_context(), order, "cancel everything")

    assert fsm._ctx.cancelled is True
    assert action.node == NodeName.ORDER
    assert "no problem" in action.message.lower()


def test_affirmative_in_confirm_triggers_place() -> None:
    fsm = OrderSubFSM(_make_context())
    fsm._state = OrderSubNode.CONFIRM

    action = fsm.handle_turn(_make_context(), _make_order(), "yes")

    assert fsm.state.value == "PLACE"


def test_negative_in_confirm_goes_back_to_configure() -> None:
    fsm = OrderSubFSM(_make_context())
    fsm._state = OrderSubNode.CONFIRM

    action = fsm.handle_turn(_make_context(), _make_order(), "no")

    assert fsm.state.value == "CONFIGURE_ITEM"


def test_duplicate_place_is_idempotent() -> None:
    fsm = OrderSubFSM(_make_context())
    fsm._state = OrderSubNode.PLACE
    fsm._ctx.placed = True

    action = fsm.handle_turn(_make_context(), _make_order(), "yes")

    assert "already placed" in action.message


def test_reset_clears_state() -> None:
    fsm = OrderSubFSM(_make_context())
    fsm._state = OrderSubNode.PLACE
    fsm._ctx.placed = True

    fsm.reset()

    assert fsm.state.value == "SELECT_ITEM"
    assert fsm._ctx.placed is False
    assert fsm._ctx.cancelled is False
