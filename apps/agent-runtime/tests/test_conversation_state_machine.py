from __future__ import annotations

from conversation_core.router import Intent
from conversation_core.state_machine import (
    ConversationContext,
    ConversationStateMachine,
    InMemoryConversationRepository,
    NodeName,
    OrderRecord,
    StoreInfoRecord,
)


def test_start_identifies_returning_caller_and_surfaces_last_order() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_customer(
        phone="2145550101",
        customer_id="cust-1",
        name="Sam",
        last_order_code="WS-4821",
        last_order_summary="WS-4821 (confirmed, total $18.92, ETA 20 minutes)",
    )
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="call-1", room_name="room-1", caller_id="+1 214-555-0101")

    action = fsm.start(context)

    assert action.node == NodeName.ROUTE
    assert "Wingstop Dallas" in action.message
    assert "Mia" in action.message
    assert "Welcome back, Sam." in action.message
    assert "WS-4821" in action.message
    assert context.customer_id == "cust-1"
    assert context.name_confirmed is True
    assert repo.get_current_node("call-1") == NodeName.ROUTE


def test_start_marks_new_caller_without_reasking_known_slot() -> None:
    repo = InMemoryConversationRepository()
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="call-2", room_name="room-2", caller_phone="2145550199")

    action = fsm.start(context)

    assert "Mia" in action.message
    assert "Wingstop Dallas" in action.message
    assert context.is_returning_customer is False
    assert context.customer_id == "cust-2145550199"


def test_low_confidence_gets_exactly_one_clarification_then_reroutes() -> None:
    fsm = ConversationStateMachine(repository=InMemoryConversationRepository())
    context = ConversationContext(call_id="call-3", room_name="room-3")
    fsm.start(context)

    first = fsm.handle_turn(context, "I need some help maybe")
    second = fsm.handle_turn(context, "I want to track my order WS-1111")

    assert first.node == NodeName.ROUTE
    assert "Are you trying to place an order" in first.message
    assert context.clarification_count == 0
    assert second.node == NodeName.ROUTE
    assert second.router_result is not None
    assert second.router_result.intent == Intent.TRACK_ORDER


def test_route_dispatches_to_order_node_which_creates_subfsm() -> None:
    fsm = ConversationStateMachine(repository=InMemoryConversationRepository())
    context = ConversationContext(call_id="call-4", room_name="room-4")
    fsm.start(context)

    action = fsm.handle_turn(context, "I'd like ten boneless wings")

    assert action.node == NodeName.ORDER
    assert "What would you like today?" in action.message
    assert context.order_sub_fsm is not None
    assert context.order_sub_node == "SELECT_ITEM"


def test_current_node_survives_simulated_reconnect() -> None:
    repo = InMemoryConversationRepository()
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="call-5", room_name="room-5")
    fsm.start(context)
    fsm.handle_turn(context, "Let me talk to a human")

    resumed_context = ConversationContext(call_id="call-5", room_name="room-5")
    resumed = ConversationStateMachine(repository=repo).resume(resumed_context)

    assert resumed.node == NodeName.ESCALATE
    assert resumed_context.current_node == NodeName.ESCALATE


def test_name_capture_confirms_spelling_and_persists_once() -> None:
    repo = InMemoryConversationRepository()
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="call-6", room_name="room-6", caller_phone="2145550133")
    fsm.start(context)

    prompt = fsm.capture_name(context, "max", spelled_name="M A X")
    confirmed = fsm.confirm_name(context, accepted=True)
    repeated = fsm.capture_name(context, "Macks")

    assert prompt.message == "Just to confirm, is the name Max?"
    assert confirmed.message == "Thanks, I have the name as Max."
    assert repo.persisted_names["2145550133"] == "Max"
    assert repeated.message == "I already have the name as Max."


# ── TRACK node ──────────────────────────────────────────────────────────


def test_track_by_code_found() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-1001", "confirmed", "$15.99", "$1.50", "$17.49", 20, 1000.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="track-1", room_name="room-1")
    fsm.start(context)

    action = fsm.handle_turn(context, "I want to track my order WS-1001")

    assert action.node == NodeName.ROUTE
    assert "WS-1001" in action.message
    assert "confirmed" in action.message or "in the kitchen" in action.message
    assert "17.49" in action.message
    assert action.router_result is not None
    assert action.router_result.intent == Intent.TRACK_ORDER


def test_track_by_code_not_found() -> None:
    repo = InMemoryConversationRepository()
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="track-2", room_name="room-2")
    fsm.start(context)

    action = fsm.handle_turn(context, "track order WS-9999")

    assert action.node == NodeName.ROUTE
    assert "couldn't find" in action.message or "WS-9999" in action.message


def test_track_with_phone_fallback() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-2001", "in_kitchen", "$22.99", "$2.10", "$25.09", 10, 1001.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="track-3", room_name="room-3", caller_phone="2145550101")
    fsm.start(context)

    action = fsm.handle_turn(context, "track my order")

    assert action.node == NodeName.ROUTE
    assert "WS-2001" in action.message
    assert "25.09" in action.message


def test_track_no_code_no_phone_asks_for_code() -> None:
    repo = InMemoryConversationRepository()
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="track-4", room_name="room-4")
    fsm.start(context)

    action = fsm.handle_turn(context, "track my order")

    assert action.node == NodeName.TRACK
    assert "order number" in action.message.lower()


def test_track_pending_follow_up_with_code() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-3001", "ready", "$8.99", "$0.80", "$9.79", 5, 1002.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="track-5", room_name="room-5")
    fsm.start(context)

    first = fsm.handle_turn(context, "track my order")
    assert first.node == NodeName.TRACK
    assert context.track_pending is True

    second = fsm.handle_turn(context, "WS-3001")
    assert second.node == NodeName.ROUTE
    assert "WS-3001" in second.message
    assert "ready" in second.message
    assert context.track_pending is False


# ── CANCEL node ─────────────────────────────────────────────────────────


def test_cancel_by_code_asks_confirmation() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-4001", "confirmed", "$12.99", "$1.20", "$14.19", 20, 1003.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="cancel-1", room_name="room-1")
    fsm.start(context)

    action = fsm.handle_turn(context, "cancel order WS-4001")

    assert action.node == NodeName.CANCEL
    assert "WS-4001" in action.message
    assert context.cancel_pending_order == "WS-4001"


def test_cancel_confirm_yes() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-4002", "confirmed", "$12.99", "$1.20", "$14.19", 20, 1004.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="cancel-2", room_name="room-2")
    fsm.start(context)

    fsm.handle_turn(context, "cancel WS-4002")

    action = fsm.handle_turn(context, "yes")

    assert action.node == NodeName.ROUTE
    assert "cancelled" in action.message
    assert repo.get_order_by_code("WS-4002").status == "cancelled"


def test_cancel_confirm_no() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-4003", "confirmed", "$12.99", "$1.20", "$14.19", 20, 1005.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="cancel-3", room_name="room-3")
    fsm.start(context)

    fsm.handle_turn(context, "cancel order WS-4003")

    action = fsm.handle_turn(context, "no")

    assert action.node == NodeName.ROUTE
    assert "won't cancel" in action.message
    assert repo.get_order_by_code("WS-4003").status == "confirmed"


def test_cancel_completed_order_is_noop() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_order(OrderRecord("WS-4004", "completed", "$0", "$0", "$0", 0, 1006.0))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="cancel-4", room_name="room-4")
    fsm.start(context)

    action = fsm.handle_turn(context, "cancel WS-4004")

    assert action.node == NodeName.CANCEL
    assert context.cancel_pending_order == "WS-4004"

    action = fsm.handle_turn(context, "yes")

    assert action.node == NodeName.ROUTE
    assert "wasn't able to cancel" in action.message or "may already be completed" in action.message


# ── STORE_INFO node ─────────────────────────────────────────────────────


def test_store_info_returns_hours_and_location() -> None:
    repo = InMemoryConversationRepository()
    repo.seed_store(StoreInfoRecord(
        name="Wingstop Dallas",
        address="123 Main St, Dallas, TX",
        phone="2145550100",
        timezone="America/Chicago",
        hours={"mon": {"open": "10:30", "close": "23:00"}},
        is_open_now=True,
    ))
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="store-1", room_name="room-1")
    fsm.start(context)

    action = fsm.handle_turn(context, "are you open today?")

    assert action.node == NodeName.ROUTE
    assert "open now" in action.message or "closed" in action.message
    assert "123 Main St" in action.message
    assert "2145550100" in action.message


def test_store_info_fallback_to_default_store() -> None:
    repo = InMemoryConversationRepository()
    fsm = ConversationStateMachine(repository=repo)
    context = ConversationContext(call_id="store-2", room_name="room-2")
    fsm.start(context)

    action = fsm.handle_turn(context, "what are your hours?")

    assert action.node == NodeName.ROUTE
    assert "Wingstop Dallas" in action.message
    assert "10:30" in action.message or "11:00" in action.message or "midnight" in action.message
