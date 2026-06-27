"""FrustrationMonitor — deterministic per-call frustration scoring & escalation.

All thresholds are configurable and all logic is deterministic so it can be
tested offline with fixed transcripts (no API keys required).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Protocol


_HANDOFF_REQUEST_RE = re.compile(
    r"\b(manager|human|real person|real human|representative|supervisor|team member|someone real|talk to a person)\b",
    re.IGNORECASE,
)

_PROFANITY_RE = re.compile(
    r"\b(fuck|shit|asshole|bastard|damn|stupid|useless|terrible|awful|horrible|ridiculous)\b",
    re.IGNORECASE,
)

_CANCEL_REFUND_RE = re.compile(
    r"\b(cancel|refund|chargeback|dispute|complaint)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FrustrationConfig:
    escalation_threshold: float = 3.0
    slot_correction_threshold: int = 2
    node_loop_threshold: int = 3
    low_confidence_stt_threshold: float = 0.4
    low_confidence_streak_limit: int = 3
    negative_sentiment_window: int = 5
    negative_sentiment_limit: int = 3
    duration_no_progress_seconds: float = 120.0
    hard_trigger_score: float = 100.0
    slot_correction_weight: float = 1.0
    node_loop_weight: float = 1.0
    low_confidence_weight: float = 1.5
    negative_sentiment_weight: float = 1.0
    duration_no_progress_weight: float = 2.0
    # Phase 6 additions
    hard_trigger_min_score: float = 85.0
    escalation_min_score: float = 60.0
    max_turns_before_escalation: int = 8
    monitor_min_turns: int = 3
    suspicious_cooldown_seconds: int = 300


@dataclass(frozen=True)
class EscalationDecision:
    reason_code: str
    frustration_score: float
    message: str = ""

    @property
    def is_hard_trigger(self) -> bool:
        return self.frustration_score >= 85.0


@dataclass
class FrustrationState:
    escalation_called: bool = False
    negative_sentiment_streak: int = 0
    low_confidence_streak: int = 0
    cancel_refund_attempts: int = 0
    repeated_slot_corrections: dict[str, int] = field(default_factory=dict)
    node_reentry_count: dict[str, int] = field(default_factory=dict)
    last_node: str = ""
    last_hard_trigger_ts: float = 0.0
    turn_count: int = 0
    last_progress_at: float = 0.0

    def reset_conversation(self) -> None:
        self.negative_sentiment_streak = 0
        self.low_confidence_streak = 0
        self.cancel_refund_attempts = 0
        self.repeated_slot_corrections.clear()
        self.node_reentry_count.clear()
        self.last_node = ""
        self.turn_count = 0


class HandoffHandlerProtocol(Protocol):
    def handoff(
        self,
        call_id: str,
        reason_code: str,
        *,
        room_name: str = "",
    ) -> str:
        ...


class FrustrationMonitor:
    def __init__(
        self,
        config: FrustrationConfig | None = None,
        handoff_handler: HandoffHandlerProtocol | None = None,
    ) -> None:
        self.config = config or FrustrationConfig()
        self.state = FrustrationState()
        self._handoff_handler = handoff_handler

    def update_turn(
        self,
        text: str,
        *,
        stt_confidence: float | None = None,
        sentiment: float | None = None,
        state_node: str | None = None,
        slot_corrected: str | None = None,
        order_has_items: bool = False,
        call_duration: float = 0.0,
    ) -> None:
        self.state.turn_count += 1

        if self.state.escalation_called:
            return

        if self._is_hard_trigger(text):
            self.state.last_hard_trigger_ts = time.time()
            return

        if slot_corrected:
            current = self.state.repeated_slot_corrections.get(slot_corrected, 0)
            self.state.repeated_slot_corrections[slot_corrected] = current + 1

        if state_node:
            if state_node == self.state.last_node:
                current = self.state.node_reentry_count.get(state_node, 0)
                self.state.node_reentry_count[state_node] = current + 1
            else:
                self.state.node_reentry_count[state_node] = 0
            self.state.last_node = state_node

        if _CANCEL_REFUND_RE.search(text or ""):
            self.state.cancel_refund_attempts += 1

        if stt_confidence is not None and stt_confidence < self.config.low_confidence_stt_threshold:
            self.state.low_confidence_streak += 1
        else:
            self.state.low_confidence_streak = 0

        if sentiment is not None and sentiment < 0.4:
            self.state.negative_sentiment_streak += 1
        elif sentiment is not None:
            self.state.negative_sentiment_streak = 0

        if order_has_items:
            self.state.last_progress_at = call_duration

    def evaluate(
        self,
        text: str,
        *,
        call_duration: float = 0.0,
        now: float | None = None,
        override_force_escalation: bool = False,
        override_suppress_escalation: bool = False,
    ) -> EscalationDecision | None:
        if override_suppress_escalation:
            self.state.escalation_called = False
            return None

        if self.state.escalation_called:
            if self.state.last_hard_trigger_ts > 0:
                elapsed = (now or time.time()) - self.state.last_hard_trigger_ts
                if elapsed < self.config.suspicious_cooldown_seconds:
                    return None
            else:
                return None

        if override_force_escalation:
            self.state.escalation_called = True
            return EscalationDecision(
                "force_override", self.config.hard_trigger_score, "Forced by override flag."
            )

        if self._is_hard_trigger(text):
            self.state.escalation_called = True
            self.state.last_hard_trigger_ts = time.time()
            if _PROFANITY_RE.search(text or ""):
                return EscalationDecision(
                    "profanity", self.config.hard_trigger_score, "Profanity detected."
                )
            return EscalationDecision(
                "explicit_handoff_request",
                self.config.hard_trigger_score,
                "Customer asked for a human.",
            )

        if self.state.turn_count < self.config.monitor_min_turns:
            return None

        score = 0.0
        reasons: list[str] = []

        for slot, count in self.state.repeated_slot_corrections.items():
            if count >= self.config.slot_correction_threshold:
                score += self.config.slot_correction_weight
                reasons.append(f"slot_{slot}_corrected_{count}x")

        for node, count in self.state.node_reentry_count.items():
            if count + 1 >= self.config.node_loop_threshold:
                score += self.config.node_loop_weight
                reasons.append(f"node_{node}_reentered_{count + 1}x")

        if self.state.low_confidence_streak >= self.config.low_confidence_streak_limit:
            score += self.config.low_confidence_weight
            reasons.append(f"low_confidence_streak_{self.state.low_confidence_streak}")

        if self.state.negative_sentiment_streak >= self.config.negative_sentiment_limit:
            score += self.config.negative_sentiment_weight
            reasons.append(f"negative_sentiment_streak_{self.state.negative_sentiment_streak}")

        if self.state.cancel_refund_attempts >= self.config.max_turns_before_escalation:
            score += self.config.slot_correction_weight
            reasons.append(f"cancel_refund_accumulation_{self.state.cancel_refund_attempts}")

        if self.state.last_progress_at == 0.0 and call_duration >= self.config.duration_no_progress_seconds:
            score += self.config.duration_no_progress_weight
            reasons.append(f"no_progress_after_{call_duration:.0f}s")
        elif self.state.last_progress_at > 0.0 and (call_duration - self.state.last_progress_at) >= self.config.duration_no_progress_seconds:
            score += self.config.duration_no_progress_weight
            reasons.append(f"stalled_{call_duration - self.state.last_progress_at:.0f}s_since_progress")

        if score >= self.config.escalation_threshold:
            reason_code = "_".join(reasons) if reasons else "soft_accumulation"
            self.state.escalation_called = True
            return EscalationDecision(reason_code, round(score, 2), f"Frustration threshold crossed ({score}).")

        return None

    @staticmethod
    def _is_hard_trigger(text: str) -> bool:
        if not text:
            return False
        return bool(_HANDOFF_REQUEST_RE.search(text) or _PROFANITY_RE.search(text))

    def reset(self) -> None:
        self.state = FrustrationState()
