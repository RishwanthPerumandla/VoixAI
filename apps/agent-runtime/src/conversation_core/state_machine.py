"""Top-level call state machine for Phase 2 conversation routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol

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


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.nodes: dict[str, NodeName] = {}
        self.customers: dict[str, dict[str, object]] = {}
        self.persisted_names: dict[str, str] = {}

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
            NodeName.ORDER: self._stub(NodeName.ORDER, "I can help start that order.", (Intent.PLACE_ORDER, Intent.MODIFY_ORDER)),
            NodeName.TRACK: self._stub(NodeName.TRACK, "I can help track that order.", (Intent.TRACK_ORDER,)),
            NodeName.STORE_INFO: self._stub(NodeName.STORE_INFO, "I can help with store information.", (Intent.STORE_INFO,)),
            NodeName.CANCEL: self._stub(NodeName.CANCEL, "I can help cancel an order after confirming the details.", (Intent.CANCEL_ORDER,)),
            NodeName.ESCALATE: self._stub(NodeName.ESCALATE, "I will get a team member to help.", (Intent.SPEAK_TO_HUMAN,)),
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
            "Hello, Wingstop Dallas.",
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
