"""Deterministic intent router for call-level conversation routing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Sequence


class Intent(str, Enum):
    PLACE_ORDER = "place_order"
    MODIFY_ORDER = "modify_order"
    TRACK_ORDER = "track_order"
    CANCEL_ORDER = "cancel_order"
    STORE_INFO = "store_info"
    SPEAK_TO_HUMAN = "speak_to_human"
    SMALLTALK_OR_UNKNOWN = "smalltalk_or_unknown"


@dataclass(frozen=True)
class RouterResult:
    intent: Intent
    confidence: float
    slots: dict[str, object] = field(default_factory=dict)
    requires_disambiguation: bool = False


Classifier = Callable[[str, Sequence[Intent]], RouterResult | Mapping[str, object] | str | Intent | None]


_ORDER_CODE_RE = re.compile(r"\b(?:WS|MOCK|EVAL)[-\s]?\d{3,8}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_slots(text: str) -> dict[str, object]:
    slots: dict[str, object] = {}
    if code_match := _ORDER_CODE_RE.search(text):
        slots["order_code"] = code_match.group(0).upper().replace(" ", "-")
    if phone_match := _PHONE_RE.search(text):
        slots["phone"] = re.sub(r"\D+", "", phone_match.group(0))[-10:]
    return slots


class IntentRouter:
    """Closed-enum router with deterministic rules and optional constrained LLM fallback."""

    def __init__(self, classifier: Classifier | None = None, *, low_confidence: float = 0.55) -> None:
        self._classifier = classifier
        self._low_confidence = low_confidence

    def route(self, text: str) -> RouterResult:
        normalized = _normalize(text)
        slots = _extract_slots(text)
        if not normalized:
            return RouterResult(Intent.SMALLTALK_OR_UNKNOWN, 0.0, slots, True)

        rule_result = self._route_by_rules(normalized, slots)
        if rule_result is not None:
            return rule_result

        if self._classifier is not None:
            classified = self._coerce_classifier_result(self._classifier(text, tuple(Intent)), slots)
            if classified is not None:
                return classified

        return RouterResult(
            Intent.SMALLTALK_OR_UNKNOWN,
            0.35,
            slots,
            requires_disambiguation=True,
        )

    def _route_by_rules(self, normalized: str, slots: dict[str, object]) -> RouterResult | None:
        if self._has_any(normalized, ("manager", "human", "representative", "real person", "real human", "supervisor")):
            return RouterResult(Intent.SPEAK_TO_HUMAN, 0.98, {**slots, "handoff_requested": True}, False)

        if "order_code" in slots or re.search(r"\b(track|status|where(?:'s| is)?|check).{0,24}\border\b", normalized):
            return RouterResult(Intent.TRACK_ORDER, 0.96, slots, False)

        if re.search(r"\b(cancel|void).{0,24}\border\b", normalized) or normalized in {"cancel", "never mind cancel it"}:
            return RouterResult(Intent.CANCEL_ORDER, 0.95, slots, False)

        if self._has_any(normalized, ("hours", "open", "close", "location", "address", "directions", "store phone")):
            return RouterResult(Intent.STORE_INFO, 0.92, slots, False)

        if re.search(r"\b(actually|change|switch|make that|instead|update|remove|add another)\b", normalized):
            return RouterResult(Intent.MODIFY_ORDER, 0.86, {"utterance": normalized, **slots}, False)

        if re.search(r"\b(i want|i'd like|i would like|let me get|can i get|can i have|place an order|order)\b", normalized):
            return RouterResult(Intent.PLACE_ORDER, 0.84, {"utterance": normalized, **slots}, False)

        if self._has_any(
            normalized,
            (
                "wings",
                "boneless",
                "bone in",
                "combo",
                "fries",
                "ranch",
                "lemon pepper",
                "cajun",
                "coke",
                "sprite",
            ),
        ):
            return RouterResult(Intent.PLACE_ORDER, 0.72, {"utterance": normalized, **slots}, False)

        if re.search(r"\b(hello|hi|hey|thanks|thank you)\b", normalized):
            return RouterResult(Intent.SMALLTALK_OR_UNKNOWN, 0.62, slots, False)

        return None

    def _coerce_classifier_result(
        self,
        raw: RouterResult | Mapping[str, object] | str | Intent | None,
        deterministic_slots: dict[str, object],
    ) -> RouterResult | None:
        if raw is None:
            return None
        if isinstance(raw, RouterResult):
            slots = {**deterministic_slots, **raw.slots}
            return RouterResult(raw.intent, self._bounded(raw.confidence), slots, raw.requires_disambiguation)
        if isinstance(raw, Intent):
            return RouterResult(raw, 0.6, deterministic_slots, False)
        if isinstance(raw, str):
            try:
                return RouterResult(Intent(raw), 0.6, deterministic_slots, False)
            except ValueError:
                return None
        intent_value = raw.get("intent")
        try:
            intent = intent_value if isinstance(intent_value, Intent) else Intent(str(intent_value))
        except ValueError:
            return None
        confidence = self._bounded(float(raw.get("confidence", 0.6)))
        slots = {**deterministic_slots, **dict(raw.get("slots", {}) or {})}
        return RouterResult(
            intent,
            confidence,
            slots,
            bool(raw.get("requires_disambiguation", confidence < self._low_confidence)),
        )

    @staticmethod
    def _has_any(text: str, phrases: Sequence[str]) -> bool:
        return any(phrase in text for phrase in phrases)

    @staticmethod
    def _bounded(confidence: float) -> float:
        return max(0.0, min(1.0, confidence))
