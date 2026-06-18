"""Deterministic lifecycle controller for VoixAI orders."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import OrderState


class OrderPhase(str, Enum):
    IDLE = "idle"
    GREETING = "greeting"
    COLLECTING_ORDER = "collecting_order"
    VALIDATING_ORDER = "validating_order"
    PRICING_ORDER = "pricing_order"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUBMITTING_ORDER = "submitting_order"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    HANDOFF_REQUIRED = "handoff_required"
    FAILED = "failed"


_LEGACY_STATUS_MAP = {
    "collecting": OrderPhase.COLLECTING_ORDER,
    "priced": OrderPhase.PRICING_ORDER,
    "ready_for_confirmation": OrderPhase.AWAITING_CONFIRMATION,
    "confirmed_pending_submit": OrderPhase.AWAITING_CONFIRMATION,
    "submitted": OrderPhase.COMPLETED,
}


def derive_phase(order: OrderState) -> OrderPhase:
    if order.status in {phase.value for phase in OrderPhase}:
        return OrderPhase(order.status)
    if order.status in _LEGACY_STATUS_MAP:
        return _LEGACY_STATUS_MAP[order.status]
    if order.confirmed and order.total_shown and order.recap_readback:
        return OrderPhase.AWAITING_CONFIRMATION
    if order.items:
        return OrderPhase.COLLECTING_ORDER
    return OrderPhase.IDLE


@dataclass
class SubmitDecision:
    validation_errors: list[str] = field(default_factory=list)
    confirmation_reasons: list[str] = field(default_factory=list)

    @property
    def authorized(self) -> bool:
        return not self.validation_errors and not self.confirmation_reasons


class OrderStateMachine:
    def __init__(self, order: OrderState) -> None:
        self.order = order

    @property
    def phase(self) -> OrderPhase:
        return derive_phase(self.order)

    def _set_status(self, phase: OrderPhase) -> None:
        self.order.status = phase.value
        self.order.metrics.final_status = phase.value

    def start_greeting(self) -> None:
        self._set_status(OrderPhase.GREETING)

    def reset_to_collecting(self) -> None:
        order = self.order
        order.confirmed = False
        order.total_shown = False
        order.recap_readback = False
        order.pos_validation_passed = False
        self._set_status(OrderPhase.COLLECTING_ORDER if order.items or order.order_type else OrderPhase.IDLE)

    def start_validation(self) -> None:
        self._set_status(OrderPhase.VALIDATING_ORDER)

    def apply_validation(self, errors: list[str]) -> None:
        order = self.order
        order.last_validation_errors = list(errors)
        order.pos_validation_passed = not errors
        if errors:
            self._set_status(OrderPhase.COLLECTING_ORDER if order.items or order.order_type else OrderPhase.IDLE)
        elif order.confirmed and order.recap_readback and order.total_shown:
            self._set_status(OrderPhase.AWAITING_CONFIRMATION)
        elif order.recap_readback:
            self._set_status(OrderPhase.AWAITING_CONFIRMATION)
        elif order.total_shown:
            self._set_status(OrderPhase.PRICING_ORDER)
        else:
            self._set_status(OrderPhase.COLLECTING_ORDER if order.items or order.order_type else OrderPhase.IDLE)

    def start_pricing(self) -> None:
        self._set_status(OrderPhase.PRICING_ORDER)

    def mark_priced(self) -> None:
        order = self.order
        order.total_shown = True
        order.last_validation_errors = []
        order.pos_validation_passed = True
        self._set_status(OrderPhase.PRICING_ORDER)

    def mark_reviewed(self) -> None:
        order = self.order
        order.total_shown = True
        order.recap_readback = True
        order.pos_validation_passed = True
        order.last_validation_errors = []
        self._set_status(OrderPhase.AWAITING_CONFIRMATION)

    def set_confirmed(self, confirmed: bool) -> None:
        self.order.confirmed = confirmed
        if confirmed:
            self._set_status(OrderPhase.AWAITING_CONFIRMATION)
        else:
            self._set_status(
                OrderPhase.COLLECTING_ORDER if self.order.items or self.order.order_type else OrderPhase.IDLE
            )

    def mark_submitting(self) -> None:
        self._set_status(OrderPhase.SUBMITTING_ORDER)

    def mark_submitted(self) -> None:
        self._set_status(OrderPhase.COMPLETED)

    def mark_cancelled(self) -> None:
        self._set_status(OrderPhase.CANCELLED)

    def mark_handoff_required(self) -> None:
        self._set_status(OrderPhase.HANDOFF_REQUIRED)

    def mark_failed(self) -> None:
        self._set_status(OrderPhase.FAILED)

    def authorize_submit(self) -> SubmitDecision:
        from .confirmation import _missing_confirmation_reasons
        from .validation import validate_order

        self.start_validation()
        validation_errors = validate_order(self.order)
        self.apply_validation(validation_errors)
        confirmation_reasons = (
            [] if validation_errors else _missing_confirmation_reasons(self.order)
        )
        return SubmitDecision(
            validation_errors=validation_errors,
            confirmation_reasons=confirmation_reasons,
        )
