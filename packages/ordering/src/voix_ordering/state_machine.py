"""Deterministic order state machine (M2).

This module is the single authority for *what phase an order is in* and *whether
it may be submitted*. Before this existed, submission was gated by a handful of
boolean flags on ``OrderState`` that were flipped as side effects of the LLM
calling tools in the order the prompt told it to. That made reliability depend
on model tool-adherence.

Now the rules live here, in code:

- ``derive_phase`` is the single definition of the order lifecycle.
- ``OrderStateMachine`` owns every transition the runtime tools used to perform
  inline (``reset_to_collecting``, ``apply_validation``, ``mark_priced``,
  ``mark_reviewed``, ``set_confirmed``).
- ``authorize_submit`` is the hard gate: it re-runs full validation **and** the
  confirmation checklist every time, so an order can never be "placed" unless it
  is genuinely valid and confirmed — regardless of what the model said or which
  flags happen to be set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import OrderState


class OrderPhase(str, Enum):
    GREETING = "greeting"
    COLLECTING = "collecting"
    PRICED = "priced"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed_pending_submit"
    SUBMITTED = "submitted"


def derive_phase(order: OrderState) -> OrderPhase:
    """Single source of truth for the order's lifecycle phase.

    Derived from the order's persisted flags so it stays correct even if the
    order is rehydrated from storage (no separate phase field to drift).
    """
    if order.status == "submitted":
        return OrderPhase.SUBMITTED
    if order.confirmed and order.recap_readback and order.total_shown and order.pos_validation_passed:
        return OrderPhase.CONFIRMED
    if order.status == "ready_for_confirmation" or (order.recap_readback and order.total_shown):
        return OrderPhase.AWAITING_CONFIRMATION
    if order.total_shown:
        return OrderPhase.PRICED
    if order.items:
        return OrderPhase.COLLECTING
    return OrderPhase.GREETING


@dataclass
class SubmitDecision:
    """Result of asking the machine whether an order may be submitted."""

    validation_errors: list[str] = field(default_factory=list)
    confirmation_reasons: list[str] = field(default_factory=list)

    @property
    def authorized(self) -> bool:
        return not self.validation_errors and not self.confirmation_reasons


class OrderStateMachine:
    """Owns transitions for a single ``OrderState`` instance."""

    def __init__(self, order: OrderState) -> None:
        self.order = order

    @property
    def phase(self) -> OrderPhase:
        return derive_phase(self.order)

    def reset_to_collecting(self) -> None:
        """Any order mutation invalidates pricing/confirmation; go back to collecting.

        This is the order-level half of the old ``_mark_order_dirty``; the
        session-level cleanup (clearing the cached price quote / mock order)
        stays with the caller that owns the session.
        """
        order = self.order
        order.confirmed = False
        order.total_shown = False
        order.recap_readback = False
        order.pos_validation_passed = False
        order.status = "collecting"

    def apply_validation(self, errors: list[str]) -> None:
        """Record validation results and recompute the persisted status string."""
        order = self.order
        order.last_validation_errors = errors
        order.pos_validation_passed = not errors
        if errors:
            order.status = "collecting"
        elif order.confirmed:
            order.status = "confirmed_pending_submit"
        elif order.recap_readback and order.total_shown:
            order.status = "ready_for_confirmation"
        else:
            order.status = "collecting"

    def mark_priced(self) -> None:
        """Transition COLLECTING -> PRICED (a total has been shown to the customer)."""
        order = self.order
        order.total_shown = True
        order.last_validation_errors = []
        order.pos_validation_passed = True
        order.status = "collecting"

    def mark_reviewed(self) -> None:
        """Transition PRICED -> AWAITING_CONFIRMATION (recap read back to the customer)."""
        order = self.order
        order.total_shown = True
        order.recap_readback = True
        order.pos_validation_passed = True
        order.last_validation_errors = []
        order.status = "ready_for_confirmation"

    def set_confirmed(self, confirmed: bool) -> None:
        """Apply the customer's explicit yes/no to the reviewed order."""
        order = self.order
        order.confirmed = confirmed
        if confirmed and order.recap_readback and order.total_shown and order.pos_validation_passed:
            order.status = "confirmed_pending_submit"
        elif not confirmed:
            order.status = "collecting"

    def mark_submitted(self) -> None:
        self.order.status = "submitted"

    def authorize_submit(self) -> SubmitDecision:
        """The hard gate. Re-validate from scratch and re-check the confirmation
        checklist every time. Submission is authorized only if both are clean."""
        from .confirmation import _missing_confirmation_reasons
        from .validation import validate_order

        validation_errors = validate_order(self.order)
        self.apply_validation(validation_errors)
        confirmation_reasons = (
            [] if validation_errors else _missing_confirmation_reasons(self.order)
        )
        return SubmitDecision(
            validation_errors=validation_errors,
            confirmation_reasons=confirmation_reasons,
        )
