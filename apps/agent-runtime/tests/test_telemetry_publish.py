"""Telemetry publishing must self-heal and never stall a turn.

The entire live UI (transcript, order panel, order-placed confirmation) rides on
these snapshots, so a transient publisher blip must NOT take telemetry dark for
the rest of the call, and a slow publisher must never block longer than the cap.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import agent as agent_mod  # noqa: E402
from agent import SessionState, _publish_session_snapshot  # noqa: E402


class _FakeParticipant:
    def __init__(self) -> None:
        self.calls = 0
        self.mode = "ok"  # "ok" | "raise" | "hang"

    async def publish_data(self, data, *, reliable, topic):  # noqa: ANN001, D401
        self.calls += 1
        if self.mode == "raise":
            raise ConnectionError("could not establish publisher connection: timeout")
        if self.mode == "hang":
            await asyncio.sleep(10)
        return None


class _FakeRoom:
    def __init__(self, participant: _FakeParticipant) -> None:
        self.local_participant = participant
        self.name = "test-room"


def _make_state(monkeypatch) -> tuple[SessionState, _FakeParticipant]:
    # Avoid the heavy scenario snapshot builder; we only care about transport.
    monkeypatch.setattr(
        agent_mod, "_snapshot_payload", lambda s, *, reason: {"type": "session_snapshot"}
    )
    participant = _FakeParticipant()
    state = SessionState()
    state.room = _FakeRoom(participant)
    return state, participant


@pytest.mark.asyncio
async def test_repeated_failures_back_off_then_retry(monkeypatch):
    state, participant = _make_state(monkeypatch)
    participant.mode = "raise"

    # Below threshold: keeps trying every call (no cooldown yet).
    for _ in range(agent_mod.TELEMETRY_PUBLISH_FAILURE_THRESHOLD):
        await _publish_session_snapshot(state, reason="t")
    assert participant.calls == agent_mod.TELEMETRY_PUBLISH_FAILURE_THRESHOLD

    # Threshold reached -> cooldown scheduled, counter reset, NOT disabled forever.
    assert state.telemetry_cooldown_until > time.time()
    assert state.telemetry_publish_failures == 0

    # During cooldown the publish is skipped entirely (no new attempt).
    calls_before = participant.calls
    await _publish_session_snapshot(state, reason="t")
    assert participant.calls == calls_before

    # After cooldown elapses and the transport recovers, it publishes again and
    # the failure counter stays clean — telemetry self-healed.
    state.telemetry_cooldown_until = 0.0
    participant.mode = "ok"
    await _publish_session_snapshot(state, reason="t")
    assert participant.calls == calls_before + 1
    assert state.telemetry_publish_failures == 0


@pytest.mark.asyncio
async def test_slow_publish_is_bounded(monkeypatch):
    state, participant = _make_state(monkeypatch)
    participant.mode = "hang"

    started = time.monotonic()
    await _publish_session_snapshot(state, reason="t")
    elapsed = time.monotonic() - started

    # Must return within roughly the cap, not hang on the 10s sleep.
    assert elapsed < agent_mod.TELEMETRY_PUBLISH_TIMEOUT_SECONDS + 1.0
    assert state.telemetry_publish_failures == 1
