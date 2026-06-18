"""Replay saved intents/events against the reducer for regression coverage."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import OrderIntent, OrderState
from .reducer import ReducerResult, apply_order_intent


@dataclass
class ReplayResult:
    order: OrderState
    steps: list[ReducerResult] = field(default_factory=list)


def replay_order_intents(intents: list[OrderIntent], *, order: OrderState | None = None) -> ReplayResult:
    active_order = order or OrderState()
    steps: list[ReducerResult] = []
    for intent in intents:
        steps.append(apply_order_intent(active_order, intent))
    return ReplayResult(order=active_order, steps=steps)
