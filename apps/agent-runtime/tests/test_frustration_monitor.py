from __future__ import annotations

import time

import pytest

from conversation_core.frustration_monitor import (
    FrustrationConfig,
    FrustrationMonitor,
    FrustrationState,
)
from conversation_core.handoff import MockHandoffHandler

HANDLER = MockHandoffHandler()


def _make_monitor(**overrides: object) -> FrustrationMonitor:
    defaults = dict(
        slot_correction_threshold=2,
        node_loop_threshold=3,
        low_confidence_stt_threshold=0.4,
        low_confidence_streak_limit=3,
        negative_sentiment_window=5,
        negative_sentiment_limit=3,
            duration_no_progress_seconds=120.0,
            hard_trigger_min_score=0.85,
            escalation_threshold=0.60,
        max_turns_before_escalation=8,
        monitor_min_turns=3,
        suspicious_cooldown_seconds=300,
    )
    defaults.update(overrides)
    return FrustrationMonitor(
        handoff_handler=HANDLER,
        config=FrustrationConfig(**defaults),
    )


class TestFrustrationState:
    def test_initial_state(self) -> None:
        s = FrustrationState()
        assert s.escalation_called is False
        assert s.negative_sentiment_streak == 0
        assert s.low_confidence_streak == 0
        assert s.cancel_refund_attempts == 0
        assert s.repeated_slot_corrections == {}
        assert s.node_reentry_count == {}
        assert s.last_hard_trigger_ts == 0.0

    def test_reset_conversation(self) -> None:
        s = FrustrationState(negative_sentiment_streak=3, low_confidence_streak=2)
        s.reset_conversation()
        assert s.negative_sentiment_streak == 0
        assert s.low_confidence_streak == 0
        assert s.cancel_refund_attempts == 0
        assert s.repeated_slot_corrections == {}
        assert s.node_reentry_count == {}


class TestHardTriggers:
    def test_explicit_handoff_request(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0)
        d = m.evaluate("I want to talk to a manager", call_duration=30.0)
        assert d is not None
        assert d.reason_code == "explicit_handoff_request"
        assert d.is_hard_trigger

    def test_profanity_hard_trigger(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0)
        d = m.evaluate("This is fucking ridiculous", call_duration=10.0)
        assert d is not None
        assert d.is_hard_trigger
        assert d.frustration_score >= 85.0

    @pytest.mark.parametrize(
        "text,expected_code",
        [
            ("talk to a human", "explicit_handoff_request"),
            ("I need a real person", "explicit_handoff_request"),
            ("get me a supervisor", "explicit_handoff_request"),
            ("I want someone real", "explicit_handoff_request"),
        ],
    )
    def test_handoff_phrases(self, text: str, expected_code: str) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0)
        d = m.evaluate(text, call_duration=5.0)
        assert d is not None
        assert d.reason_code == expected_code
        assert d.is_hard_trigger

    def test_hard_trigger_cooldown(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0, suspicious_cooldown_seconds=300)
        d1 = m.evaluate("I want to talk to a manager", call_duration=10.0)
        assert d1 is not None
        d2 = m.evaluate("I want to talk to a manager", call_duration=15.0)
        assert d2 is None  # within cooldown

    def test_hard_trigger_re_arms_after_cooldown(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.5, suspicious_cooldown_seconds=0.001)
        d1 = m.evaluate("I want a human", call_duration=10.0)
        assert d1 is not None
        time.sleep(0.002)
        m.state.escalation_called = False
        d2 = m.evaluate("I want a human", call_duration=20.0)
        assert d2 is not None


class TestSoftSignals:
    def test_node_loop_escalation(self) -> None:
        m = _make_monitor(node_loop_threshold=2, monitor_min_turns=1, escalation_threshold=0.0)
        m.update_turn(text="what", state_node="menu", call_duration=5.0)
        m.update_turn(text="what", state_node="menu", call_duration=10.0)
        d = m.evaluate("what", call_duration=15.0)
        assert d is not None
        assert "node_" in d.reason_code
        assert not d.is_hard_trigger

    def test_repeated_slot_correction(self) -> None:
        m = _make_monitor(slot_correction_threshold=2, monitor_min_turns=1, escalation_threshold=0.0)
        m.update_turn(text="no, I said large", state_node="order_modify", order_has_items=True, call_duration=5.0)
        m.state.repeated_slot_corrections["size"] = 1
        m.update_turn(text="NOT large, medium!", state_node="order_modify", order_has_items=True, call_duration=10.0)
        m.state.repeated_slot_corrections["size"] = 2
        d = m.evaluate("NO!", call_duration=15.0)
        assert d is not None
        assert "slot_" in d.reason_code

    def test_cancel_refund_accumulation(self) -> None:
        m = _make_monitor(max_turns_before_escalation=1, monitor_min_turns=1, escalation_threshold=0.0)
        m.update_turn(text="hello", call_duration=5.0)
        m.state.cancel_refund_attempts = 3
        d = m.evaluate("I want to cancel", call_duration=60.0)
        assert d is not None
        assert "cancel_refund" in d.reason_code

    def test_duration_no_progress(self) -> None:
        m = _make_monitor(duration_no_progress_seconds=0.0, monitor_min_turns=1, escalation_threshold=0.0)
        m.update_turn(text="uh", state_node="greeting", call_duration=180.0)
        d = m.evaluate("uh", call_duration=180.0)
        assert d is not None
        assert "no_progress" in d.reason_code

    def test_low_confidence_streak(self) -> None:
        m = _make_monitor(
            low_confidence_stt_threshold=0.5,
            low_confidence_streak_limit=3,
            monitor_min_turns=1,
            escalation_threshold=0.0,
        )
        for i in range(3):
            m.update_turn("huh?", stt_confidence=0.3, call_duration=float(i) * 5.0)
        d = m.evaluate("what?", call_duration=15.0)
        assert d is not None
        assert "low_confidence" in d.reason_code

    def test_too_few_turns_no_escalation(self) -> None:
        m = _make_monitor(monitor_min_turns=5, escalation_min_score=0.0)
        m.update_turn("hello", state_node="greeting", call_duration=0.0)
        d = m.evaluate("hello", call_duration=0.0)
        assert d is None


class TestOverrideFlags:
    def test_force_override_true(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0)
        d = m.evaluate("anything", call_duration=5.0, override_force_escalation=True)
        assert d is not None
        assert d.reason_code == "force_override"

    def test_no_override_false(self) -> None:
        m = _make_monitor(hard_trigger_min_score=1.5, escalation_threshold=1.5)
        d = m.evaluate("casual chat", call_duration=5.0, override_force_escalation=False)
        assert d is None

    def test_suppress_override(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0)
        d = m.evaluate("I want a manager", call_duration=5.0)
        assert d is not None
        d2 = m.evaluate("I want a manager", call_duration=10.0, override_suppress_escalation=True)
        assert d2 is None


class TestEscalationGuard:
    def test_no_double_escalation(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0)
        d1 = m.evaluate("talk to a human", call_duration=5.0)
        assert d1 is not None
        m.state.escalation_called = True
        d2 = m.evaluate("talk to a human again", call_duration=10.0)
        assert d2 is None

    def test_reset_after_time(self) -> None:
        m = _make_monitor(hard_trigger_min_score=0.0, suspicious_cooldown_seconds=0.001)
        d1 = m.evaluate("talk to a human", call_duration=5.0)
        assert d1 is not None
        m.state.escalation_called = False
        time.sleep(0.002)
        d2 = m.evaluate("still want a human", call_duration=15.0)
        assert d2 is not None
