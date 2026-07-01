"""Tests for call telemetry + analytics endpoints (dashboard)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import main as api_main
from storage import SqliteStorage


@pytest.fixture()
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteStorage:
    store = SqliteStorage(tmp_path / "calls.db")
    monkeypatch.setattr(api_main, "ORDER_STORAGE", store)
    return store


def _start_req(call_id: str = "call-1", room: str = "room-1") -> "api_main.CallStartRequest":
    return api_main.CallStartRequest(
        call_id=call_id,
        room_name=room,
        scenario="wingstop_inbound_ordering",
        channel="web",
        voice_provider="classic",
        llm_model="openai/gpt-5.3-chat-latest",
    )


@pytest.mark.asyncio
async def test_start_call_opens_in_progress_record(storage: SqliteStorage) -> None:
    detail = await api_main.start_call(_start_req())

    assert detail.call_id == "call-1"
    assert detail.status == "in_progress"
    assert detail.outcome == "unknown"
    assert detail.transcript == []


@pytest.mark.asyncio
async def test_start_call_is_idempotent_on_call_id(storage: SqliteStorage) -> None:
    first = await api_main.start_call(_start_req())
    # A retried start (e.g. worker restart) must not create a second row.
    second = await api_main.start_call(_start_req(room="room-DIFFERENT"))

    assert first.call_id == second.call_id
    assert second.room_name == "room-1"  # original wins; no duplicate
    listed, total = storage.list_calls()
    assert total == 1


@pytest.mark.asyncio
async def test_update_call_finalizes_with_transcript(storage: SqliteStorage) -> None:
    await api_main.start_call(_start_req())
    detail = await api_main.update_call(
        "call-1",
        api_main.CallUpdateRequest(
            status="completed",
            outcome="order_placed",
            ended_at=time.time(),
            duration_seconds=92.0,
            turn_count=8,
            sentiment=0.88,
            order_number="MOCK-22222",
            transcript=[
                api_main.TranscriptTurn(role="assistant", text="Welcome to Voix Wings"),
                api_main.TranscriptTurn(role="user", text="I'd like 10 wings"),
            ],
        ),
    )

    assert detail.status == "completed"
    assert detail.outcome == "order_placed"
    assert detail.duration_seconds == 92.0
    assert detail.order_number == "MOCK-22222"
    assert len(detail.transcript) == 2
    assert detail.transcript[1].role == "user"


@pytest.mark.asyncio
async def test_update_missing_call_raises_404(storage: SqliteStorage) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await api_main.update_call("nope", api_main.CallUpdateRequest(status="completed"))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_calls_filters_by_outcome(storage: SqliteStorage) -> None:
    await api_main.start_call(_start_req("call-a"))
    await api_main.update_call("call-a", api_main.CallUpdateRequest(status="completed", outcome="order_placed"))
    await api_main.start_call(_start_req("call-b"))
    await api_main.update_call("call-b", api_main.CallUpdateRequest(status="completed", outcome="transfer"))

    placed = await api_main.list_calls(limit=50, offset=0, status=None, outcome="order_placed", search=None)
    assert placed.total == 1
    assert placed.calls[0].call_id == "call-a"


@pytest.mark.asyncio
async def test_analytics_overview_aggregates(storage: SqliteStorage) -> None:
    # Two completed calls: one placed an order, one was transferred.
    await api_main.start_call(_start_req("call-a"))
    await api_main.update_call(
        "call-a",
        api_main.CallUpdateRequest(
            status="completed", outcome="order_placed", duration_seconds=80.0,
            ended_at=time.time(), turn_count=6, sentiment=0.9, order_number="MOCK-1",
        ),
    )
    await api_main.start_call(_start_req("call-b"))
    await api_main.update_call(
        "call-b",
        api_main.CallUpdateRequest(
            status="completed", outcome="transfer", duration_seconds=40.0,
            ended_at=time.time(), turn_count=2, sentiment=0.4,
        ),
    )

    overview = await api_main.analytics_overview(window_hours=24, buckets=6)
    assert overview.total_calls == 2
    assert overview.orders_placed == 1
    assert overview.transfers == 1
    assert overview.containment_rate == 0.5  # 1 transfer of 2 finished calls
    assert overview.success_rate == 1.0  # both completed
    assert len(overview.series) == 6


@pytest.mark.asyncio
async def test_observability_health_reports_components(storage: SqliteStorage) -> None:
    snapshot = await api_main.observability_health()
    assert snapshot.status in {"operational", "degraded", "down"}
    names = {c.name for c in snapshot.components}
    assert "Order datastore" in names
    assert "Idempotency guard" in names


# ── Transcript turns ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_append_transcript_turns(storage: SqliteStorage) -> None:
    await api_main.start_call(api_main.CallStartRequest(call_id="call-t1", room_name="room-t"))
    result = await api_main.append_call_turns(
        "call-t1",
        api_main.TurnAppendBatchRequest(
            turns=[
                api_main.TurnAppendRequest(speaker="assistant", text="Hello", state_node="GREETING"),
                api_main.TurnAppendRequest(
                    speaker="user", text="track my order", intent="track_order"
                ),
            ]
        ),
    )
    assert result["inserted"] == 2

    turns = await api_main.get_call_transcript("call-t1")
    assert len(turns) == 2
    assert turns[0].speaker == "assistant"
    assert turns[0].state_node == "GREETING"
    assert turns[1].speaker == "user"
    assert turns[1].intent == "track_order"
    assert turns[1].seq == 2


@pytest.mark.asyncio
async def test_append_turns_missing_call_returns_404(storage: SqliteStorage) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await api_main.append_call_turns("no-such", api_main.TurnAppendBatchRequest(turns=[]))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_transcript_missing_call_returns_404(storage: SqliteStorage) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await api_main.get_call_transcript("no-such")
    assert exc.value.status_code == 404


# ── Analytics events ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_and_list_call_events(storage: SqliteStorage) -> None:
    await api_main.start_call(api_main.CallStartRequest(call_id="call-e1", room_name="room-e"))
    r1 = await api_main.record_call_event(
        "call-e1",
        api_main.EventRequest(ts=100.0, type="state_enter", payload={"node": "GREETING"}),
    )
    assert r1["status"] == "ok"

    r2 = await api_main.record_call_event(
        "call-e1",
        api_main.EventRequest(ts=101.0, type="slot_filled", payload={"slot": "customer_name"}),
    )
    assert r2["status"] == "ok"

    events = await api_main.get_call_events("call-e1")
    assert len(events) == 2
    assert events[0].type == "state_enter"
    assert events[0].payload["node"] == "GREETING"
    assert events[1].type == "slot_filled"


@pytest.mark.asyncio
async def test_record_event_missing_call_returns_404(storage: SqliteStorage) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await api_main.record_call_event("no-such", api_main.EventRequest(ts=0, type="test"))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_analytics_overview_includes_new_fields(storage: SqliteStorage) -> None:
    await api_main.start_call(api_main.CallStartRequest(call_id="call-x", room_name="room-x"))
    await api_main.update_call(
        "call-x",
        api_main.CallUpdateRequest(
            status="completed", outcome="order_placed", duration_seconds=60.0,
            ended_at=time.time(), turn_count=5, sentiment=0.8, order_number="WS-1",
        ),
    )
    now = time.time()
    storage.insert_event("call-x", now - 60, "latency_sample", {"value_seconds": 0.45})
    storage.insert_event("call-x", now - 30, "latency_sample", {"value_seconds": 1.2})
    storage.insert_event("call-x", now - 10, "latency_sample", {"value_seconds": 0.35})

    overview = await api_main.analytics_overview(window_hours=24, buckets=6)
    assert overview.total_calls >= 1
    assert overview.completion_rate is not None
    assert overview.aov is not None
    assert overview.p50_latency_seconds is not None
    assert overview.p95_latency_seconds is not None
    assert isinstance(overview.intent_distribution, dict)
    assert overview.abandonment_rate is not None
