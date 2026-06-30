"""Top-level call state machine for Phase 2 conversation routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Protocol

from .router import Intent, IntentRouter, RouterResult


class NodeName(str, Enum):
    GREETING = "GREETING"
    IDENTIFY = "IDENTIFY"
    ROUTE = "ROUTE"
    ORDER = "ORDER"
    TRACK = "TRACK"
    STORE_INFO = "STORE_INFO"
    CANCEL = "CANCEL"
    ESCALATE = "ESCALATE"
    WRAPUP = "WRAPUP"


@dataclass
class OrderRecord:
    order_number: str
    status: str
    subtotal: str
    tax: str
    total: str
    eta_minutes: int
    created_at: float | None = None


@dataclass
class StoreInfoRecord:
    name: str
    address: str
    phone: str
    timezone: str
    hours: dict[str, dict[str, str]]
    is_open_now: bool


@dataclass
class ConversationContext:
    call_id: str
    room_name: str
    caller_id: str | None = None
    caller_phone: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    is_returning_customer: bool = False
    last_order_code: str | None = None
    last_order_summary: str | None = None
    current_node: NodeName = NodeName.GREETING
    clarification_count: int = 0
    pending_name: str | None = None
    name_confirmed: bool = False
    order_sub_fsm: Any | None = field(default=None, repr=False, compare=False)
    order_sub_node: str | None = None
    # Multi-turn flow flags
    track_pending: bool = False
    cancel_pending_order: str | None = None
    cancel_pending_text: str = ""
    # Escalation
    frustration_decision: Any | None = field(default=None, repr=False, compare=False)
    outcome: str | None = None
    telemetry: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class StateAction:
    node: NodeName
    message: str
    telemetry_events: tuple[dict[str, object], ...] = ()
    router_result: RouterResult | None = None
    requires_response: bool = True


@dataclass(frozen=True)
class StateNode:
    name: NodeName
    allowed_intents: frozenset[Intent]
    transitions: dict[Intent, NodeName]
    telemetry: tuple[str, ...]
    on_enter: Callable[[ConversationContext, RouterResult | None], StateAction]


class ConversationRepository(Protocol):
    def get_current_node(self, call_id: str) -> NodeName | None: ...

    def persist_node(self, context: ConversationContext, node: NodeName) -> None: ...

    def identify_customer(self, context: ConversationContext) -> ConversationContext: ...

    def persist_customer_name(self, context: ConversationContext, name: str) -> ConversationContext: ...

    def get_order_by_code(self, code: str) -> OrderRecord | None: ...

    def get_latest_active_order_by_phone(self, phone: str) -> OrderRecord | None: ...

    def cancel_order(self, order_number: str) -> bool: ...

    def get_store_info(self) -> StoreInfoRecord: ...

    def get_item_available(self, item_name_or_id: str) -> bool: ...

    def record_escalation(
        self, call_id: str, reason_code: str, frustration_score: float, triggered_at: float
    ) -> None: ...

    def set_call_outcome(self, call_id: str, outcome: str) -> None: ...


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.nodes: dict[str, NodeName] = {}
        self.customers: dict[str, dict[str, object]] = {}
        self.persisted_names: dict[str, str] = {}
        self._orders: dict[str, OrderRecord] = {}
        self._store: StoreInfoRecord | None = None
        self._unavailable_items: set[str] = set()
        self._outcomes: dict[str, str] = {}
        self._escalations: list[dict[str, object]] = []

    def seed_order(self, record: OrderRecord) -> None:
        self._orders[record.order_number] = record

    def seed_store(self, record: StoreInfoRecord) -> None:
        self._store = record

    def mark_item_unavailable(self, item_name_or_id: str) -> None:
        self._unavailable_items.add(item_name_or_id.lower())

    # --- protocol methods for ordering data ---

    def record_escalation(self, call_id: str, reason_code: str, frustration_score: float, triggered_at: float) -> None:
        self._escalations.append({
            "call_id": call_id,
            "reason_code": reason_code,
            "frustration_score": frustration_score,
            "triggered_at": triggered_at,
        })

    def set_call_outcome(self, call_id: str, outcome: str) -> None:
        self._outcomes[call_id] = outcome

    def get_order_by_code(self, code: str) -> OrderRecord | None:
        return self._orders.get(code)

    def get_latest_active_order_by_phone(self, phone: str) -> OrderRecord | None:
        active = [o for o in self._orders.values() if o.status in ("confirmed", "in_kitchen", "ready")]
        if not active:
            return None
        return max(active, key=lambda o: o.created_at or 0)

    def cancel_order(self, order_number: str) -> bool:
        record = self._orders.get(order_number)
        if record is None or record.status in ("completed", "cancelled"):
            return False
        record.status = "cancelled"
        return True

    def get_store_info(self) -> StoreInfoRecord:
        if self._store is not None:
            return self._store
        return StoreInfoRecord(
            name="Wingstop Dallas",
            address="Demo Store - Dallas, TX",
            phone="2145550100",
            timezone="America/Chicago",
            hours={
                day: {"open": "10:30", "close": "23:00"}
                for day in ("mon", "tue", "wed", "thu", "sun")
            } | {
                day: {"open": "10:30", "close": "00:00"}
                for day in ("fri", "sat")
            },
            is_open_now=True,
        )

    def get_item_available(self, item_name_or_id: str) -> bool:
        return item_name_or_id.lower() not in self._unavailable_items

    def seed_customer(
        self,
        *,
        phone: str,
        customer_id: str,
        name: str | None = None,
        last_order_code: str | None = None,
        last_order_summary: str | None = None,
    ) -> None:
        self.customers[phone] = {
            "customer_id": customer_id,
            "name": name,
            "last_order_code": last_order_code,
            "last_order_summary": last_order_summary,
        }

    def get_current_node(self, call_id: str) -> NodeName | None:
        return self.nodes.get(call_id)

    def persist_node(self, context: ConversationContext, node: NodeName) -> None:
        self.nodes[context.call_id] = node

    def identify_customer(self, context: ConversationContext) -> ConversationContext:
        phone = context.caller_phone or _phone_from_caller_id(context.caller_id)
        context.caller_phone = phone
        if not phone:
            return context
        seeded = self.customers.get(phone)
        if seeded:
            context.customer_id = str(seeded["customer_id"])
            context.customer_name = str(seeded["name"]) if seeded.get("name") else None
            context.is_returning_customer = True
            context.last_order_code = str(seeded["last_order_code"]) if seeded.get("last_order_code") else None
            context.last_order_summary = (
                str(seeded["last_order_summary"]) if seeded.get("last_order_summary") else None
            )
            context.name_confirmed = bool(context.customer_name)
        else:
            context.customer_id = f"cust-{phone}"
            context.is_returning_customer = False
            self.customers[phone] = {"customer_id": context.customer_id, "name": None}
        return context

    def persist_customer_name(self, context: ConversationContext, name: str) -> ConversationContext:
        if context.caller_phone:
            self.persisted_names[context.caller_phone] = name
            self.customers.setdefault(context.caller_phone, {"customer_id": context.customer_id or f"cust-{context.caller_phone}"})
            self.customers[context.caller_phone]["name"] = name
        context.customer_name = name
        context.name_confirmed = True
        return context


class NameCaptureManager:
    def capture(self, context: ConversationContext, name: str, *, spelled_name: str | None = None) -> StateAction:
        if context.name_confirmed and context.customer_name:
            return StateAction(
                context.current_node,
                f"I already have the name as {context.customer_name}.",
                ({"type": "slot_already_filled", "slot": "customer_name"},),
            )
        candidate = _name_from_spelling(spelled_name) if spelled_name else _clean_name(name)
        context.pending_name = candidate
        return StateAction(
            context.current_node,
            f"Just to confirm, is the name {candidate}?",
            ({"type": "slot_confirmation_requested", "slot": "customer_name"},),
        )

    def confirm(
        self,
        context: ConversationContext,
        repository: ConversationRepository,
        *,
        accepted: bool,
        corrected_name: str | None = None,
        spelled_name: str | None = None,
    ) -> StateAction:
        if accepted and (context.pending_name or context.customer_name):
            name = context.pending_name or context.customer_name or ""
            repository.persist_customer_name(context, name)
            return StateAction(
                context.current_node,
                f"Thanks, I have the name as {name}.",
                ({"type": "slot_filled", "slot": "customer_name"},),
            )
        if corrected_name or spelled_name:
            return self.capture(context, corrected_name or "", spelled_name=spelled_name)
        return StateAction(
            context.current_node,
            "No problem. Please spell the name for me.",
            ({"type": "spelling_fallback_requested", "slot": "customer_name"},),
        )


class ConversationStateMachine:
    def __init__(
        self,
        *,
        router: IntentRouter | None = None,
        repository: ConversationRepository | None = None,
    ) -> None:
        self.router = router or IntentRouter()
        self.repository = repository or InMemoryConversationRepository()
        self.nodes = self._build_nodes()
        self.name_capture = NameCaptureManager()

    def start(self, context: ConversationContext) -> StateAction:
        resumed = self.repository.get_current_node(context.call_id)
        if resumed is not None:
            context.current_node = resumed
            return StateAction(
                resumed,
                f"Resuming from {resumed.value}.",
                ({"type": "state_resume", "node": resumed.value},),
                requires_response=False,
            )

        greeting = self._enter(NodeName.GREETING, context, None)
        identified = self._enter(NodeName.IDENTIFY, context, None)
        self._persist(context, NodeName.ROUTE)
        context.current_node = NodeName.ROUTE
        message = f"{greeting.message} {identified.message}".strip()
        return StateAction(
            NodeName.ROUTE,
            message,
            (*greeting.telemetry_events, *identified.telemetry_events, {"type": "state_enter", "node": NodeName.ROUTE.value}),
        )

    def resume(self, context: ConversationContext) -> StateAction:
        node = self.repository.get_current_node(context.call_id) or NodeName.GREETING
        context.current_node = node
        return StateAction(
            node,
            f"Resuming from {node.value}.",
            ({"type": "state_resume", "node": node.value},),
            requires_response=False,
        )

    def handle_turn(self, context: ConversationContext, text: str) -> StateAction:
        current = self.repository.get_current_node(context.call_id) or context.current_node or NodeName.ROUTE
        context.current_node = current

        # When in ORDER sub-FSM, delegate directly without re-routing.
        if current == NodeName.ORDER and context.order_sub_fsm is not None:
            action = context.order_sub_fsm.handle_turn(context, getattr(context, "_order_state", None), text)
            telemetry_events = list(action.telemetry_events)
            context.telemetry.extend(telemetry_events)
            if action.node == NodeName.ROUTE:
                self._persist(context, NodeName.ROUTE)
            return action

        # Multi-turn flows: stay in node without re-routing when pending flags set
        if current == NodeName.TRACK and context.track_pending:
            context.track_pending = False
            result = self.router.route(text)
            return self._enter(NodeName.TRACK, context, result)
        if current == NodeName.CANCEL and context.cancel_pending_order:
            context.cancel_pending_text = text
            return self._enter(NodeName.CANCEL, context, None)

        if current != NodeName.ROUTE:
            self._persist(context, NodeName.ROUTE)
            context.current_node = NodeName.ROUTE

        result = self.router.route(text)
        if result.requires_disambiguation and context.clarification_count == 0:
            context.clarification_count += 1
            self._persist(context, NodeName.ROUTE)
            return StateAction(
                NodeName.ROUTE,
                "Are you trying to place an order, track an order, get store info, cancel, or talk to a team member?",
                ({"type": "clarification_requested", "intent": result.intent.value},),
                router_result=result,
            )

        context.clarification_count = 0
        target = self.nodes[NodeName.ROUTE].transitions.get(result.intent, NodeName.WRAPUP)
        return self._enter(target, context, result)

    def capture_name(self, context: ConversationContext, name: str, *, spelled_name: str | None = None) -> StateAction:
        return self.name_capture.capture(context, name, spelled_name=spelled_name)

    def confirm_name(
        self,
        context: ConversationContext,
        *,
        accepted: bool,
        corrected_name: str | None = None,
        spelled_name: str | None = None,
    ) -> StateAction:
        return self.name_capture.confirm(
            context,
            self.repository,
            accepted=accepted,
            corrected_name=corrected_name,
            spelled_name=spelled_name,
        )

    def force_escalate(self, context: ConversationContext, decision: Any) -> StateAction:
        """Bypass routing and force the FSM into the ESCALATE node."""
        context.frustration_decision = decision
        context.outcome = "escalated"
        return self._enter(NodeName.ESCALATE, context, None)

    def record_escalation(self, context: ConversationContext, decision: Any) -> None:
        import time
        reason_code = decision.reason_code if decision else "explicit_handoff_request"
        score = decision.frustration_score if decision else 100.0
        self.repository.record_escalation(
            context.call_id, reason_code, score, time.time()
        )
        self.repository.set_call_outcome(context.call_id, "escalated")

    def _enter(
        self,
        node_name: NodeName,
        context: ConversationContext,
        router_result: RouterResult | None,
    ) -> StateAction:
        self._persist(context, node_name)
        action = self.nodes[node_name].on_enter(context, router_result)
        context.telemetry.extend(action.telemetry_events)
        return action

    def _persist(self, context: ConversationContext, node: NodeName) -> None:
        context.current_node = node
        self.repository.persist_node(context, node)

    def _build_nodes(self) -> dict[NodeName, StateNode]:
        return {
            NodeName.GREETING: StateNode(
                NodeName.GREETING,
                frozenset(),
                {},
                ("state_enter", "greeting_started"),
                self._on_greeting,
            ),
            NodeName.IDENTIFY: StateNode(
                NodeName.IDENTIFY,
                frozenset(),
                {},
                ("state_enter", "caller_identified"),
                self._on_identify,
            ),
            NodeName.ROUTE: StateNode(
                NodeName.ROUTE,
                frozenset(Intent),
                {
                    Intent.PLACE_ORDER: NodeName.ORDER,
                    Intent.MODIFY_ORDER: NodeName.ORDER,
                    Intent.TRACK_ORDER: NodeName.TRACK,
                    Intent.CANCEL_ORDER: NodeName.CANCEL,
                    Intent.STORE_INFO: NodeName.STORE_INFO,
                    Intent.SPEAK_TO_HUMAN: NodeName.ESCALATE,
                    Intent.SMALLTALK_OR_UNKNOWN: NodeName.WRAPUP,
                },
                ("state_enter", "intent_routed"),
                lambda ctx, result: StateAction(NodeName.ROUTE, "", (), result, False),
            ),
            NodeName.ORDER: self._order_node(),
            NodeName.TRACK: self._track_node(),
            NodeName.STORE_INFO: self._store_info_node(),
            NodeName.CANCEL: self._cancel_node(),
            NodeName.ESCALATE: self._escalate_node(),
            NodeName.WRAPUP: StateNode(
                NodeName.WRAPUP,
                frozenset(),
                {},
                ("state_enter", "wrapup"),
                lambda ctx, result: StateAction(
                    NodeName.WRAPUP,
                    "I can help with ordering, tracking, store information, cancellations, or a team member.",
                    ({"type": "state_enter", "node": NodeName.WRAPUP.value},),
                    result,
                ),
            ),
        }

    def _order_node(self) -> StateNode:
        return StateNode(
            NodeName.ORDER,
            frozenset(Intent),
            {
                Intent.CANCEL_ORDER: NodeName.CANCEL,
                Intent.SPEAK_TO_HUMAN: NodeName.ESCALATE,
                Intent.SMALLTALK_OR_UNKNOWN: NodeName.ROUTE,
            },
            ("state_enter", "order_started"),
            self._on_order_enter,
        )

    def _on_order_enter(self, context: ConversationContext, result: RouterResult | None) -> StateAction:
        from .order_fsm import OrderSubFSM

        context.order_sub_fsm = OrderSubFSM(context)
        context.order_sub_node = "SELECT_ITEM"
        message = "Let me help you place an order. What would you like today?"
        return StateAction(
            NodeName.ORDER,
            message,
            (
                {"type": "state_enter", "node": NodeName.ORDER.value},
                {"type": "order_sub_fsm_started", "sub_node": "SELECT_ITEM"},
            ),
            result,
        )

    # ── TRACK node ──────────────────────────────────────────────────────────

    @staticmethod
    def _status_text(status: str) -> str:
        return {
            "draft": "is still being prepared",
            "confirmed": "has been confirmed",
            "in_kitchen": "is being prepared in the kitchen",
            "ready": "is ready for pickup",
            "completed": "has been completed",
            "cancelled": "was cancelled",
        }.get(status, f"is {status}")

    def _track_node(self) -> StateNode:
        return StateNode(
            NodeName.TRACK,
            frozenset({Intent.TRACK_ORDER}),
            {},
            ("state_enter", "track_started"),
            self._on_track_enter,
        )

    def _on_track_enter(self, context: ConversationContext, result: RouterResult | None) -> StateAction:
        slots = result.slots if result else {}
        code = slots.get("order_code", "")

        # If pending was cleared, code was extracted by router in the re-route pass
        if code:
            record = self.repository.get_order_by_code(str(code))
            if record is not None:
                status = self._status_text(record.status)
                eta = f" It should be ready in about {record.eta_minutes} minutes." if record.eta_minutes else ""
                self._persist(context, NodeName.ROUTE)
                return StateAction(
                    NodeName.ROUTE,
                    f"Order {record.order_number} {status}.{eta} The total was {record.total}.",
                    ({"type": "track_result", "order_number": record.order_number, "status": record.status},),
                    router_result=result,
                    requires_response=False,
                )
            self._persist(context, NodeName.ROUTE)
            return StateAction(
                NodeName.ROUTE,
                f"I couldn't find an order with code {code}. Would you like to try again or can I help with something else?",
                ({"type": "track_not_found", "code": code},),
                router_result=result,
                requires_response=False,
            )

        # No code — try phone fallback
        phone = context.caller_phone or ""
        if phone:
            record = self.repository.get_latest_active_order_by_phone(phone)
            if record is not None:
                status = self._status_text(record.status)
                eta = f" It should be ready in about {record.eta_minutes} minutes." if record.eta_minutes else ""
                self._persist(context, NodeName.ROUTE)
                return StateAction(
                    NodeName.ROUTE,
                    f"Order {record.order_number} {status}.{eta} The total was {record.total}.",
                    ({"type": "track_result", "order_number": record.order_number, "status": record.status},),
                    router_result=result,
                    requires_response=False,
                )
            self._persist(context, NodeName.ROUTE)
            return StateAction(
                NodeName.ROUTE,
                "I couldn't find any active orders under your phone number. Would you like to place a new order?",
                ({"type": "track_no_active_order"},),
                router_result=result,
                requires_response=False,
            )

        # No code and no phone — ask for the code
        context.track_pending = True
        self._persist(context, NodeName.TRACK)
        return StateAction(
            NodeName.TRACK,
            "I can look up your order. Do you have an order number you can share?",
            ({"type": "track_ask_code"},),
            router_result=result,
        )

    # ── ESCALATE node ──────────────────────────────────────────────────────

    def _escalate_node(self) -> StateNode:
        return StateNode(
            NodeName.ESCALATE,
            frozenset({Intent.SPEAK_TO_HUMAN}),
            {Intent.SPEAK_TO_HUMAN: NodeName.WRAPUP},
            ("state_enter", "escalation_trigger"),
            self._on_escalate_enter,
        )

    @staticmethod
    def _on_escalate_enter(context: ConversationContext, result: RouterResult | None) -> StateAction:
        import time
        from .handoff import HANDOFF_MESSAGE

        decision = context.frustration_decision
        reason_code = decision.reason_code if decision else "explicit_handoff_request"
        frustration_score = decision.frustration_score if decision else 100.0

        context.outcome = "escalated"
        now = time.time()

        telemetry_events: list[dict[str, object]] = [
            {"type": "state_enter", "node": NodeName.ESCALATE.value},
            {
                "type": "escalation_trigger",
                "reason_code": reason_code,
                "frustration_score": frustration_score,
            },
        ]

        return StateAction(
            NodeName.WRAPUP,
            HANDOFF_MESSAGE,
            tuple(telemetry_events),
            router_result=result,
            requires_response=False,
        )

    # ── CANCEL node ─────────────────────────────────────────────────────────

    def _cancel_node(self) -> StateNode:
        return StateNode(
            NodeName.CANCEL,
            frozenset({Intent.CANCEL_ORDER}),
            {},
            ("state_enter", "cancel_started"),
            self._on_cancel_enter,
        )

    def _on_cancel_enter(self, context: ConversationContext, result: RouterResult | None) -> StateAction:
        # If we have a pending cancellation, this is the confirmation turn
        pending_code = context.cancel_pending_order
        if pending_code:
            text = context.cancel_pending_text
            context.cancel_pending_order = None
            context.cancel_pending_text = ""
            if self._is_affirmative(text):
                ok = self.repository.cancel_order(pending_code)
                if ok:
                    self._persist(context, NodeName.ROUTE)
                    return StateAction(
                        NodeName.ROUTE,
                        f"OK, order {pending_code} has been cancelled.",
                        ({"type": "cancel_completed", "order_number": pending_code},),
                        router_result=result,
                        requires_response=False,
                    )
                self._persist(context, NodeName.ROUTE)
                return StateAction(
                    NodeName.ROUTE,
                    f"I wasn't able to cancel order {pending_code}. It may already be completed or cancelled.",
                    ({"type": "cancel_failed", "order_number": pending_code},),
                    router_result=result,
                    requires_response=False,
                )
            self._persist(context, NodeName.ROUTE)
            return StateAction(
                NodeName.ROUTE,
                f"OK, I won't cancel order {pending_code}. Is there anything else I can help with?",
                ({"type": "cancel_aborted", "order_number": pending_code},),
                router_result=result,
                requires_response=False,
            )

        slots = result.slots if result else {}
        code = slots.get("order_code", "")
        phone = context.caller_phone or ""

        if code:
            record = self.repository.get_order_by_code(str(code))
        elif phone:
            record = self.repository.get_latest_active_order_by_phone(phone)
        else:
            record = None

        if record is None:
            self._persist(context, NodeName.ROUTE)
            return StateAction(
                NodeName.ROUTE,
                "I couldn't find an order to cancel. Do you have an order number?",
                ({"type": "cancel_not_found"},),
                router_result=result,
                requires_response=False,
            )

        # Found the order — ask for confirmation (gate)
        context.cancel_pending_order = record.order_number
        self._persist(context, NodeName.CANCEL)
        return StateAction(
            NodeName.CANCEL,
            f"Should I cancel order {record.order_number} for {record.total}?",
            ({"type": "cancel_ask_confirm", "order_number": record.order_number},),
            router_result=result,
        )

    # ── STORE_INFO node ─────────────────────────────────────────────────────

    def _store_info_node(self) -> StateNode:
        return StateNode(
            NodeName.STORE_INFO,
            frozenset({Intent.STORE_INFO}),
            {},
            ("state_enter", "store_info_started"),
            self._on_store_info_enter,
        )

    def _on_store_info_enter(self, context: ConversationContext, result: RouterResult | None) -> StateAction:
        store = self.repository.get_store_info()
        is_open = store.is_open_now
        open_status = "open now" if is_open else "closed right now"

        parts = [f"{store.name} is {open_status}."]
        parts.append("We're located at " + store.address + ".")
        parts.append("Our phone number is " + store.phone + ".")
        parts.append("Hours vary by day — most days 10:30 AM to 11:00 PM, Friday and Saturday until midnight.")

        self._persist(context, NodeName.ROUTE)
        return StateAction(
            NodeName.ROUTE,
            " ".join(parts),
            ({"type": "store_info_result", "is_open": is_open},),
            router_result=result,
            requires_response=False,
        )

    @staticmethod
    def _is_affirmative(text: str) -> bool:
        lowered = text.lower().strip()
        return any(
            lowered.startswith(p) or p in lowered
            for p in ("yes", "yeah", "sure", "correct", "that's right", "place it", "confirm", "go ahead", "si")
        )

    def _stub(self, node_name: NodeName, message: str, intents: tuple[Intent, ...]) -> StateNode:
        return StateNode(
            node_name,
            frozenset(intents),
            {intent: NodeName.WRAPUP for intent in intents},
            ("state_enter",),
            lambda ctx, result: StateAction(
                node_name,
                message,
                (
                    {"type": "state_enter", "node": node_name.value},
                    {"type": "intent_routed", "intent": result.intent.value if result else None},
                ),
                result,
            ),
        )

    @staticmethod
    def _on_greeting(context: ConversationContext, _result: RouterResult | None) -> StateAction:
        return StateAction(
            NodeName.GREETING,
            "Hey, thanks for calling Wingstop Dallas, this is Mia.",
            ({"type": "state_enter", "node": NodeName.GREETING.value}, {"type": "greeting_started"}),
        )

    def _on_identify(self, context: ConversationContext, _result: RouterResult | None) -> StateAction:
        self.repository.identify_customer(context)
        if context.is_returning_customer and context.customer_name:
            last = f" Your last order was {context.last_order_summary}." if context.last_order_summary else ""
            message = f"Welcome back, {context.customer_name}.{last} How can I help you."
        else:
            message = "How can I help you."
        return StateAction(
            NodeName.IDENTIFY,
            message,
            (
                {"type": "state_enter", "node": NodeName.IDENTIFY.value},
                {
                    "type": "caller_identified",
                    "returning": context.is_returning_customer,
                    "customer_id": context.customer_id,
                    "phone": context.caller_phone,
                },
            ),
        )


def _clean_name(name: str) -> str:
    cleaned = " ".join(part for part in name.strip().replace(".", " ").split() if part)
    return cleaned.title() if cleaned else ""


def _name_from_spelling(spelled_name: str | None) -> str:
    if not spelled_name:
        return ""
    letters = re_split_letters(spelled_name)
    return "".join(letters).title() if letters else _clean_name(spelled_name)


def re_split_letters(spelled_name: str) -> list[str]:
    separators = (" ", "-", ",", ".")
    normalized = spelled_name.strip()
    for sep in separators:
        normalized = normalized.replace(sep, " ")
    return [part for part in normalized.split() if len(part) == 1 and part.isalpha()]


def _phone_from_caller_id(caller_id: str | None) -> str | None:
    if not caller_id:
        return None
    digits = "".join(ch for ch in caller_id if ch.isdigit())
    if len(digits) >= 10:
        return digits[-10:]
    return None
