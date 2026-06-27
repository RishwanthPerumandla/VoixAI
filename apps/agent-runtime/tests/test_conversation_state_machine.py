from __future__ import annotations

from conversation_core.router import Intent
from conversation_core.state_machine import (
    ConversationContext,
    ConversationStateMachine,
    InMemoryConversationRepository,
    NodeName,
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
    assert "Hello, Wingstop Dallas." in action.message
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

    assert action.message == "Hello, Wingstop Dallas. How can I help you."
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
    assert second.node == NodeName.TRACK
    assert second.router_result is not None
    assert second.router_result.intent == Intent.TRACK_ORDER


def test_route_dispatches_to_order_stub_for_phase3_entrypoint() -> None:
    fsm = ConversationStateMachine(repository=InMemoryConversationRepository())
    context = ConversationContext(call_id="call-4", room_name="room-4")
    fsm.start(context)

    action = fsm.handle_turn(context, "I'd like ten boneless wings")

    assert action.node == NodeName.ORDER
    assert action.message == "I can help start that order."
    assert fsm.nodes[NodeName.ORDER].transitions[Intent.PLACE_ORDER] == NodeName.WRAPUP


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
