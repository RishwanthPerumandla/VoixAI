from __future__ import annotations

import pytest

from conversation_core.router import Intent, IntentRouter, RouterResult


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("Can I track my order WS-4821?", Intent.TRACK_ORDER),
        ("Let me talk to a manager", Intent.SPEAK_TO_HUMAN),
        ("Cancel my order please", Intent.CANCEL_ORDER),
        ("What time do you close?", Intent.STORE_INFO),
        ("I'd like ten boneless wings with lemon pepper", Intent.PLACE_ORDER),
        ("Actually make that boneless", Intent.MODIFY_ORDER),
    ],
)
def test_high_signal_transcripts_route_deterministically(text: str, intent: Intent) -> None:
    result = IntentRouter().route(text)

    assert result.intent == intent
    assert result.confidence >= 0.7
    assert result.requires_disambiguation is False


def test_router_extracts_order_code_and_phone_slots() -> None:
    result = IntentRouter().route("Track WS 4821, phone is 214-555-0199")

    assert result.intent == Intent.TRACK_ORDER
    assert result.slots["order_code"] == "WS-4821"
    assert result.slots["phone"] == "2145550199"


def test_low_confidence_unknown_requires_disambiguation() -> None:
    result = IntentRouter().route("uhhh maybe I need help with something")

    assert result.intent == Intent.SMALLTALK_OR_UNKNOWN
    assert result.confidence < 0.55
    assert result.requires_disambiguation is True


def test_constrained_classifier_is_used_only_after_rules() -> None:
    def classifier(_text, _intents):
        return RouterResult(Intent.STORE_INFO, 0.77, {"classifier": True})

    router = IntentRouter(classifier=classifier)

    assert router.route("random ambiguous thing").intent == Intent.STORE_INFO
    assert router.route("talk to a real person").intent == Intent.SPEAK_TO_HUMAN
