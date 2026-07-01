"""Tests for durable, idempotent order persistence (M3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

import main as api_main
from storage import SqliteStorage


def _confirmed_order_payload() -> "api_main.OrderPayload":
    """A valid, fully-confirmed pickup order that passes the submit gate."""
    return api_main.OrderPayload(
        items=[
            api_main.OrderLinePayload(
                line_id="line-1",
                item_id="boneless_6",
                quantity=1,
                selected_flavor_ids=["cajun"],
            )
        ],
        order_type="pickup",
        customer_name="Sam",
        confirmed=True,
        total_shown=True,
        recap_readback=True,
        pos_validation_passed=True,
        status="confirmed_pending_submit",
    )


@pytest.fixture()
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteStorage:
    store = SqliteStorage(tmp_path / "orders.db")
    monkeypatch.setattr(api_main, "ORDER_STORAGE", store)
    return store


@pytest.mark.asyncio
async def test_submit_order_persists_and_returns_number(storage: SqliteStorage) -> None:
    response = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-a", order=_confirmed_order_payload())
    )

    assert response.order_number.startswith("WS-")
    assert response.status == "confirmed"
    assert response.total == "$8.65"  # boneless_6 ($7.99) + 8.25% tax
    assert response.idempotent_replay is False
    assert "VOIX WINGS DEMO" in response.kitchen_ticket

    # It is durable: a brand-new storage handle on the same file can read it.
    reopened = SqliteStorage(Path(storage._db_path))
    assert reopened.get_order_by_number(response.order_number) is not None


@pytest.mark.asyncio
async def test_submit_order_is_idempotent(storage: SqliteStorage) -> None:
    payload = _confirmed_order_payload()
    first = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-b", order=payload)
    )
    second = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-b", order=payload)
    )

    assert first.order_number == second.order_number
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True


@pytest.mark.asyncio
async def test_submit_order_rejects_unconfirmed_order(storage: SqliteStorage) -> None:
    payload = _confirmed_order_payload()
    payload.confirmed = False  # customer never confirmed

    with pytest.raises(HTTPException) as exc:
        await api_main.submit_order(
            api_main.OrderSubmitRequest(room_name="room-c", order=payload)
        )

    assert exc.value.status_code == 422
    assert "customer confirmation is missing" in exc.value.detail["reasons"]


@pytest.mark.asyncio
async def test_submit_order_rejects_invalid_order(storage: SqliteStorage) -> None:
    payload = _confirmed_order_payload()
    payload.items[0].selected_flavor_ids = []  # required flavor missing

    with pytest.raises(HTTPException) as exc:
        await api_main.submit_order(
            api_main.OrderSubmitRequest(room_name="room-d", order=payload)
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["errors"]


@pytest.mark.asyncio
async def test_get_order_returns_persisted_record(storage: SqliteStorage) -> None:
    submitted = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-e", order=_confirmed_order_payload())
    )

    fetched = await api_main.get_order(submitted.order_number)
    assert fetched.order_number == submitted.order_number
    assert fetched.total == submitted.total


@pytest.mark.asyncio
async def test_get_order_404_when_missing(storage: SqliteStorage) -> None:
    with pytest.raises(HTTPException) as exc:
        await api_main.get_order("MOCK-00000")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_orders_filters_by_room(storage: SqliteStorage) -> None:
    await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-x", order=_confirmed_order_payload())
    )
    placed_y = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-y", order=_confirmed_order_payload())
    )

    scoped = await api_main.list_orders(limit=50, offset=0, room_name="room-y")
    assert scoped.total == 1
    assert scoped.orders[0].room_name == "room-y"
    assert scoped.orders[0].order_number == placed_y.order_number

    empty = await api_main.list_orders(limit=50, offset=0, room_name="room-none")
    assert empty.total == 0

    every = await api_main.list_orders(limit=50, offset=0, room_name=None)
    assert every.total == 2


def test_kitchen_ticker_advances_orders(storage: SqliteStorage) -> None:
    from sqlalchemy import select
    from models import Order, utc_now
    from services import OrderService

    session = storage._Session()
    try:
        svc = OrderService(session)
        now = utc_now()
        svc.create_draft(public_code="K-1", customer=None, store=None)
        svc.create_draft(public_code="K-2", customer=None, store=None)
        svc.create_draft(public_code="K-3", customer=None, store=None)
        for code, status in [("K-1", "confirmed"), ("K-2", "in_kitchen"), ("K-3", "ready")]:
            row = session.scalar(select(Order).where(Order.public_code == code))
            row.status = status
            row.placed_at = now
        session.flush()

        # First tick advances all confirmed orders (only K-1)
        assert svc.advance_kitchen_ticker() == 1
        # Second tick advances all in_kitchen orders (K-1, K-2)
        assert svc.advance_kitchen_ticker() == 2
        # Third tick advances all ready orders (K-1, K-2, K-3)
        assert svc.advance_kitchen_ticker() == 3

        for code, expected in [("K-1", "completed"), ("K-2", "completed"), ("K-3", "completed")]:
            row = session.scalar(select(Order).where(Order.public_code == code))
            assert row.status == expected, f"{code} expected {expected} got {row.status}"

        assert svc.advance_kitchen_ticker() == 0
    finally:
        session.close()
