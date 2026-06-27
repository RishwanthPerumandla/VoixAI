from __future__ import annotations

from dataclasses import dataclass, field
import re
from types import SimpleNamespace
from typing import Any

from agent import SessionState
from channels import get_channel_definition
from scenarios.wingstop import (
    FLAVOR_OPTIONS,
    MENU_ITEMS,
    MODIFIER_OPTIONS,
    OrderIntent,
    OrderLineItem,
    OrderStateMachine,
    WingstopAssistant,
    _normalize_lookup_key,
    _resolve_flavor_id,
    _resolve_item_id,
    _resolve_modifier_id,
    apply_order_intent,
    build_price_quote,
    customer_expressed_frustration,
    customer_requested_handoff,
    summarize_order_state,
)


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "eight": 8,
    "ten": 10,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "fifty": 50,
}

AMBIGUOUS_PHRASES = {
    "make it spicy": "Which flavor did you want for that item?",
    "make that two": "Which item did you mean? I have more than one item on the order.",
    "the chicken thing": "I want to make sure I got that right. Which chicken item did you mean?",
    "the hot one": "I want to make sure I got that right. Which item did you mean by the hot one?",
    "the regular one": "I want to make sure I got that right. Which regular item did you mean?",
    "add sauce": "I want to make sure I got that right. Which sauce or flavor would you like?",
    "remove that": "Which item did you mean? I have more than one item on the order.",
    "change it": "Which item did you mean? I have more than one item on the order.",
    "same as before": "I want to make sure I got that right. Which item should match the previous one?",
    "give me the other one": "I want to make sure I got that right. Which item did you want instead?",
}

SYNTHETIC_EVENT_BY_REASON = {
    "price_quote_updated": "price_quoted",
    "pricing_blocked": "pricing_blocked",
    "confirmation_review_ready": "confirmation_review_ready",
    "confirmation_review_blocked": "confirmation_review_blocked",
    "mock_order_created": "mock_order_created",
    "mock_order_blocked": "mock_order_blocked",
    "mock_order_duplicate_prevented": "mock_order_duplicate_prevented",
    "handoff_required": "handoff_required",
}


@dataclass
class TurnResult:
    user: str
    response: str
    order_status: str
    line_item_ids: list[str]
    validation_errors: list[str]
    telemetry_events: list[str]
    snapshot_reasons: list[str]
    subtotal: str | None
    total: str | None
    order_id_created: bool


@dataclass
class ScenarioResult:
    name: str
    turns: list[TurnResult] = field(default_factory=list)
    order_status: str = "idle"
    line_item_ids: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    mock_order_id: str | None = None
    archived_order_count: int = 0
    correction_count: int = 0
    cancellation_count: int = 0
    clarification_count: int = 0
    unknown_item_count: int = 0
    validation_failure_count: int = 0
    duplicate_confirmation_prevented: int = 0
    handoff_required_count: int = 0
    last_clarification_question: str | None = None


def _find_customer_name(text: str) -> str | None:
    patterns = (
        r"\bfor (?P<name>[A-Za-z][A-Za-z'-]*)\b",
        r"\bname is (?P<name>[A-Za-z][A-Za-z'-]*)\b",
        r"\bit(?:'s| is) for (?P<name>[A-Za-z][A-Za-z'-]*)\b",
        r"\bpara (?P<name>[A-Za-z][A-Za-z'-]*)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.groupdict().get("name")
            if name and name.lower() not in {"pickup", "delivery"}:
                return name.title()
    return None


def _collect_catalog_matches(text: str, source: dict[str, Any]) -> list[str]:
    lowered = text.lower()
    candidates: list[tuple[int, str, str]] = []
    for value_id, value in source.items():
        aliases = (value.display_name, *value.aliases)
        for alias in aliases:
            normalized = alias.strip().lower()
            if normalized:
                candidates.append((len(normalized), normalized, value_id))

    matches: list[str] = []
    occupied_spans: list[tuple[int, int]] = []
    for _, candidate, value_id in sorted(candidates, reverse=True):
        for match in re.finditer(rf"\b{re.escape(candidate)}\b", lowered):
            span = match.span()
            if any(max(span[0], used[0]) < min(span[1], used[1]) for used in occupied_spans):
                continue
            if value_id not in matches:
                matches.append(value_id)
            occupied_spans.append(span)
            break
    return matches


def _collect_flavors(text: str) -> list[str]:
    return _collect_catalog_matches(text, FLAVOR_OPTIONS)


def _collect_modifiers(text: str) -> list[str]:
    return _collect_catalog_matches(text, MODIFIER_OPTIONS)


def _resolve_item_phrase(text: str) -> str | None:
    lowered = text.lower()
    ranked: list[tuple[int, str]] = []
    for item in MENU_ITEMS.values():
        candidates = (item.display_name, *item.aliases)
        for candidate in candidates:
            if candidate.lower() in lowered:
                ranked.append((len(candidate), candidate))
    if ranked:
        return max(ranked, key=lambda entry: entry[0])[1]
    return None


def _find_quantity_value(text: str) -> int | None:
    match = re.search(r"\b(\d+)\b", text)
    if match:
        return int(match.group(1))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text, re.IGNORECASE):
            return value
    return None


def _contains_phrase(normalized_text: str, *phrases: str) -> bool:
    for phrase in phrases:
        normalized_phrase = _normalize_lookup_key(phrase)
        if re.search(rf"\b{re.escape(normalized_phrase)}\b", normalized_text):
            return True
    return False


def _is_total_request(normalized_text: str) -> bool:
    return _contains_phrase(
        normalized_text,
        "cuanto es el total",
        "what is my total",
        "whats my total",
        "what's my total",
        "total",
        "price",
    )


def _is_review_request(normalized_text: str) -> bool:
    return _contains_phrase(
        normalized_text,
        "review",
        "read it back",
        "recap",
    )


def _is_place_request(normalized_text: str) -> bool:
    return _contains_phrase(
        normalized_text,
        "yes",
        "yes please",
        "si",
        "si por favor",
        "place it",
        "place the order",
        "pon la orden",
        "confirm",
    )


def _find_removal_target(user_text: str, normalized_text: str) -> str:
    target = _resolve_item_phrase(user_text)
    if target is not None:
        return target
    if _contains_phrase(normalized_text, "fries", "fry"):
        return "fries"
    if _contains_phrase(normalized_text, "drink", "coke", "sprite", "dr pepper", "water"):
        return "drink"
    if _contains_phrase(normalized_text, "ranch", "blue cheese", "honey mustard", "cheese sauce", "dip"):
        return "dip"
    if _contains_phrase(normalized_text, "sandwich"):
        return "sandwich"
    if _contains_phrase(normalized_text, "wing", "wings", "boneless", "classic"):
        return "wings"
    return "item"


def _display_names(ids: list[str], source: dict[str, Any]) -> str | None:
    values: list[str] = []
    for value_id in ids:
        if value_id in source:
            values.append(str(source[value_id].display_name))
    if not values:
        return None
    return ", ".join(values)


class ReliabilityScenarioRunner:
    def __init__(self) -> None:
        self.assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
        self.session_state = SessionState()
        self.context = SimpleNamespace(userdata=self.session_state)
        self._snapshot_reasons: list[str] = []

        async def publish_snapshot(*, reason: str) -> None:
            self._snapshot_reasons.append(reason)

        self.session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    def reset(self, initial_state: dict[str, Any] | None = None) -> None:
        self.session_state = SessionState()
        self.context = SimpleNamespace(userdata=self.session_state)
        self._snapshot_reasons = []

        async def publish_snapshot(*, reason: str) -> None:
            self._snapshot_reasons.append(reason)

        self.session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]
        setattr(self.session_state, "_last_priced_subtotal", None)
        initial_state = initial_state or {}
        order = self.session_state.order
        if "order_type" in initial_state:
            order.order_type = initial_state["order_type"]
        order.customer_name = initial_state.get("customer_name", "")
        order.phone = initial_state.get("phone", "")
        order.language = initial_state.get("language", "english")
        for item_payload in initial_state.get("items", []):
            order.items.append(
                OrderLineItem(
                    line_id=item_payload["line_id"],
                    item_id=item_payload["item_id"],
                    quantity=int(item_payload.get("quantity", 1)),
                    selected_flavor_ids=list(item_payload.get("selected_flavor_ids", [])),
                    selected_modifier_ids=list(item_payload.get("selected_modifier_ids", [])),
                    notes=str(item_payload.get("notes", "")),
                )
            )
        if order.items:
            OrderStateMachine(order).reset_to_collecting()

    async def run_scenario(self, scenario: dict[str, Any]) -> ScenarioResult:
        self.reset(scenario.get("initial_state"))
        result = ScenarioResult(name=str(scenario["name"]))
        for turn in scenario.get("turns", []):
            turn_result = await self.run_turn(str(turn["user"]))
            result.turns.append(turn_result)
        order = self.session_state.order
        result.order_status = order.status
        result.line_item_ids = [line.item_id for line in order.items]
        result.validation_errors = list(order.last_validation_errors)
        result.mock_order_id = (
            self.session_state.mock_order.order_number if self.session_state.mock_order else None
        )
        result.archived_order_count = len(order.archived_orders)
        result.correction_count = order.metrics.correction_count
        result.cancellation_count = order.metrics.cancellation_count
        result.clarification_count = order.metrics.clarification_count
        result.unknown_item_count = order.metrics.unknown_item_count
        result.validation_failure_count = order.metrics.validation_failure_count
        result.duplicate_confirmation_prevented = (
            order.metrics.duplicate_confirmation_prevented
        )
        result.handoff_required_count = order.metrics.handoff_required_count
        result.last_clarification_question = order.last_clarification_question
        return result

    async def run_turn(self, user_text: str) -> TurnResult:
        before_events = len(self.session_state.order.recent_events)
        before_reasons = len(self._snapshot_reasons)
        previous_subtotal = (
            self.session_state.price_quote.subtotal
            if self.session_state.price_quote
            else getattr(self.session_state, "_last_priced_subtotal", None)
        )
        response = await self._dispatch_turn(user_text)
        new_events = [event.type for event in self.session_state.order.recent_events[before_events:]]
        new_reasons = self._snapshot_reasons[before_reasons:]
        telemetry_events = list(new_events)
        telemetry_events.extend(
            SYNTHETIC_EVENT_BY_REASON[reason]
            for reason in new_reasons
            if reason in SYNTHETIC_EVENT_BY_REASON
        )
        quote = self.session_state.price_quote
        subtotal = quote.subtotal if quote else None
        total = quote.total if quote else None
        if previous_subtotal is not None and subtotal != previous_subtotal:
            telemetry_events.append("subtotal_changed")
        if subtotal is not None:
            setattr(self.session_state, "_last_priced_subtotal", subtotal)
        return TurnResult(
            user=user_text,
            response=response,
            order_status=self.session_state.order.status,
            line_item_ids=[line.item_id for line in self.session_state.order.items],
            validation_errors=list(self.session_state.order.last_validation_errors),
            telemetry_events=telemetry_events,
            snapshot_reasons=new_reasons,
            subtotal=subtotal,
            total=total,
            order_id_created=self.session_state.mock_order is not None,
        )

    async def _dispatch_turn(self, user_text: str) -> str:
        normalized = _normalize_lookup_key(user_text)
        responses: list[str] = []
        item_phrase = _resolve_item_phrase(user_text)

        customer_name = _find_customer_name(user_text)
        if customer_name is not None:
            responses.append(
                await self.assistant.set_customer_details(
                    self.context,
                    customer_name=customer_name,
                )
            )

        if customer_requested_handoff(user_text) or customer_expressed_frustration(user_text):
            responses.append(await self.assistant.request_handoff(self.context, reason=user_text))
            return " ".join(part for part in responses if part)

        if "refund" in normalized or "wrong order" in normalized or "complaint" in normalized:
            responses.append(await self.assistant.request_handoff(self.context, reason=user_text))
            return " ".join(part for part in responses if part)

        if "start over" in normalized or "restart" in normalized or "empezar de nuevo" in normalized:
            responses.append(await self.assistant.restart_order(self.context))
            return " ".join(part for part in responses if part)

        if (
            "cancel everything" in normalized
            or "cancel the order" in normalized
            or "never mind" in normalized
            or "cancela todo" in normalized
        ):
            responses.append(await self.assistant.cancel_order(self.context))
            return " ".join(part for part in responses if part)

        if responses and item_phrase is None:
            return " ".join(part for part in responses if part)

        if normalized in AMBIGUOUS_PHRASES:
            result = apply_order_intent(
                self.session_state.order,
                OrderIntent(
                    name="unknown",
                    clarification_question=AMBIGUOUS_PHRASES[normalized],
                ),
            )
            self.session_state.order = result.order
            if not self.session_state.order.items:
                self.session_state.order.status = "idle"
                self.session_state.order.metrics.final_status = "idle"
            self.session_state.mock_order = None
            self.session_state.price_quote = None
            return result.clarification_question or AMBIGUOUS_PHRASES[normalized]

        if _is_total_request(normalized):
            responses.append(await self.assistant.price_order(self.context))
            return " ".join(part for part in responses if part)

        if _is_review_request(normalized):
            responses.append(await self.assistant.review_order_for_confirmation(self.context))
            return " ".join(part for part in responses if part)

        if _is_place_request(normalized):
            if (
                self.session_state.order.status != "completed"
                and self.session_state.order.recap_readback
                and self.session_state.price_quote is not None
            ):
                await self.assistant.set_confirmation_status(self.context, confirmed=True)
            responses.append(await self.assistant.create_mock_order(self.context))
            return " ".join(part for part in responses if part)

        if "remove" in normalized or normalized.startswith("cancel ") or "quita" in normalized:
            target = _find_removal_target(user_text, normalized)
            responses.append(await self.assistant.remove_order_item(self.context, item_name=target))
            return " ".join(part for part in responses if part)

        if "make it two" in normalized and len(self.session_state.order.items) > 1:
            result = apply_order_intent(
                self.session_state.order,
                OrderIntent(
                    name="change_quantity",
                    target_item="wings",
                    quantity=2,
                ),
            )
            self.session_state.order = result.order
            self.session_state.mock_order = None
            self.session_state.price_quote = None
            return result.clarification_question or "Which item did you mean?"

        is_update = any(
            phrase in normalized
            for phrase in (
                "actually",
                "make that",
                "change",
                "instead",
                "mejor",
                "hazlas",
            )
        )
        flavor_names = _display_names(_collect_flavors(user_text), FLAVOR_OPTIONS)
        modifier_ids = _collect_modifiers(user_text)
        if item_phrase is not None and "fries" in _normalize_lookup_key(item_phrase):
            modifier_ids = [
                modifier_id
                for modifier_id in modifier_ids
                if modifier_id
                not in {"regular_seasoned_fries", "large_seasoned_fries", "cheese_sauce"}
            ]
        modifier_names = _display_names(modifier_ids, MODIFIER_OPTIONS)
        quantity_value = _find_quantity_value(user_text)

        if is_update and self.session_state.order.items:
            kwargs: dict[str, Any] = {}
            if item_phrase is not None and item_phrase.lower() not in user_text.lower():
                kwargs["item_name"] = item_phrase
            elif item_phrase is not None and _resolve_item_id(item_phrase) != self.session_state.order.items[-1].item_id:
                kwargs["item_name"] = item_phrase
            if flavor_names is not None:
                kwargs["flavors"] = flavor_names
            if modifier_names is not None:
                kwargs["add_modifiers"] = modifier_names
            if quantity_value is not None and not any(token in normalized for token in ("10 boneless", "10 classic", "20 boneless", "20 classic", "50 boneless", "50 classic", "6 ", "8 ", "15 ", "30 ")):
                kwargs["quantity"] = quantity_value
            responses.append(await self.assistant.update_last_item(self.context, **kwargs))
            return " ".join(part for part in responses if part)

        if item_phrase is not None:
            responses.append(
                await self.assistant.add_menu_item(
                    self.context,
                    item_name=item_phrase,
                    flavors=flavor_names,
                    modifiers=modifier_names,
                )
            )
            return " ".join(part for part in responses if part)

        result = apply_order_intent(
            self.session_state.order,
            OrderIntent(
                name="unknown",
                clarification_question="I want to make sure I got that right. What would you like to change?",
            ),
        )
        self.session_state.order = result.order
        self.session_state.mock_order = None
        self.session_state.price_quote = None
        return result.clarification_question or "I want to make sure I got that right."


def assert_turn_expectation(turn_result: TurnResult, expected: dict[str, Any]) -> None:
    if "status" in expected:
        assert turn_result.order_status == expected["status"]
    if "items" in expected:
        assert turn_result.line_item_ids == expected["items"]
    for item_id in expected.get("contains_items", []):
        assert item_id in turn_result.line_item_ids
    for item_id in expected.get("absent_items", []):
        assert item_id not in turn_result.line_item_ids
    if "validation_errors" in expected:
        assert turn_result.validation_errors == expected["validation_errors"]
    for fragment in expected.get("response_contains", []):
        assert fragment.lower() in turn_result.response.lower()
    for event_name in expected.get("telemetry_events", []):
        assert event_name in turn_result.telemetry_events or event_name in turn_result.snapshot_reasons
    if expected.get("subtotal_changed"):
        assert "subtotal_changed" in turn_result.telemetry_events
    if expected.get("total_present"):
        assert turn_result.total is not None
    if expected.get("order_id_created"):
        assert turn_result.order_id_created is True
    if expected.get("order_id_not_created"):
        assert turn_result.order_id_created is False


def assert_final_expectation(result: ScenarioResult, expected: dict[str, Any]) -> None:
    if "status" in expected:
        assert result.order_status == expected["status"]
    if "item_count" in expected:
        assert len(result.line_item_ids) == expected["item_count"]
    if "line_item_ids" in expected:
        assert result.line_item_ids == expected["line_item_ids"]
    if "completed_order" in expected:
        assert (result.mock_order_id is not None) is bool(expected["completed_order"])
    if "cancelled" in expected:
        assert (result.order_status == "cancelled") is bool(expected["cancelled"])
    if "handoff_required" in expected:
        assert (result.order_status == "handoff_required") is bool(expected["handoff_required"])
    if "validation_failure_count" in expected:
        assert result.validation_failure_count == expected["validation_failure_count"]
    if "correction_count" in expected:
        assert result.correction_count == expected["correction_count"]
    if "cancellation_count" in expected:
        assert result.cancellation_count == expected["cancellation_count"]
    if "clarification_count" in expected:
        assert result.clarification_count == expected["clarification_count"]
    if "unknown_item_count" in expected:
        assert result.unknown_item_count == expected["unknown_item_count"]
    if "duplicate_confirmation_prevented" in expected:
        assert (
            result.duplicate_confirmation_prevented
            == expected["duplicate_confirmation_prevented"]
        )
    if "archived_order_count" in expected:
        assert result.archived_order_count == expected["archived_order_count"]
    if "validation_errors" in expected:
        assert result.validation_errors == expected["validation_errors"]
