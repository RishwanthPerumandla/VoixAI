from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

import main as api_main
from models import Customer, MenuItem, Order, OrderItem, Store
from services import (
    CustomerService,
    MenuSeedService,
    OrderLineInput,
    OrderService,
    StoreService,
    make_public_code,
)
from storage import SqliteStorage


@pytest.fixture()
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteStorage:
    store = SqliteStorage(tmp_path / "phase1.db")
    monkeypatch.setattr(api_main, "ORDER_STORAGE", store)
    return store


def test_seed_store_and_menu_is_idempotent(storage: SqliteStorage) -> None:
    with storage._Session() as session:
        first_store = StoreService(session).seed_demo_store()
        first_count = MenuSeedService(session).seed_menu()
        session.commit()

        second_store = StoreService(session).seed_demo_store()
        second_count = MenuSeedService(session).seed_menu()
        session.commit()

        assert first_store.id == second_store.id == StoreService.DEMO_STORE_ID
        assert first_count == second_count
        assert session.scalar(select(func.count()).select_from(Store)) == 1
        assert session.scalar(select(func.count()).select_from(MenuItem)) == first_count
        assert session.get(MenuItem, "boneless_6").options_schema["requires_flavors"] is True


def test_customer_and_order_services_are_idempotent(storage: SqliteStorage) -> None:
    with storage._Session() as session:
        MenuSeedService(session).seed_menu()
        store = StoreService(session).seed_demo_store()
        customer_service = CustomerService(session)
        customer = customer_service.upsert_by_phone("(214) 555-0101", name="Sam")
        same_customer = customer_service.upsert_by_phone("1-214-555-0101", name="Sam Carter")

        assert customer.id == same_customer.id
        assert same_customer.phone == "2145550101"
        assert same_customer.name == "Sam Carter"

        order_service = OrderService(session)
        public_code = make_public_code(session)
        draft = order_service.create_draft(
            public_code=public_code,
            customer=same_customer,
            store=store,
            room_name="room-phase1",
            idempotency_key="idem-phase1",
        )
        order_service.mutate_lines(
            draft,
            [
                OrderLineInput(
                    menu_item_id="boneless_6",
                    name="6 Boneless Wings",
                    quantity=1,
                    unit_price=Decimal("7.99"),
                    line_total=Decimal("7.99"),
                    modifiers={"flavor_ids": ["cajun"]},
                )
            ],
            subtotal=Decimal("7.99"),
            tax=Decimal("0.66"),
            total=Decimal("8.65"),
            eta_minutes=15,
            order_json="{}",
            kitchen_ticket="ticket",
        )
        confirmed = order_service.confirm(draft, idempotency_key="idem-phase1")
        replay = order_service.confirm(confirmed, idempotency_key="idem-phase1")
        session.commit()

        assert replay.id == confirmed.id
        assert replay.status == "confirmed"
        assert same_customer.order_count == 1
        assert same_customer.total_spend == Decimal("8.65")
        assert session.scalar(select(func.count()).select_from(Order)) == 1
        assert session.scalar(select(func.count()).select_from(OrderItem)) == 1
        assert order_service.get_latest_by_phone("2145550101").public_code == public_code

        cancelled = order_service.cancel(replay)
        session.commit()
        assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_submit_order_writes_phase1_schema(storage: SqliteStorage) -> None:
    payload = api_main.OrderPayload(
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
        phone="2145550101",
        confirmed=True,
        total_shown=True,
        recap_readback=True,
        pos_validation_passed=True,
        status="confirmed_pending_submit",
    )

    response = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-schema", order=payload)
    )
    replay = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-schema", order=payload)
    )

    with storage._Session() as session:
        order = session.scalar(select(Order).where(Order.public_code == response.order_number))
        customer = session.scalar(select(Customer).where(Customer.phone == "2145550101"))

        assert response.order_number.startswith("WS-")
        assert replay.order_number == response.order_number
        assert replay.idempotent_replay is True
        assert order is not None
        assert order.status == "confirmed"
        assert order.store_id == StoreService.DEMO_STORE_ID
        assert len(order.items) == 1
        assert order.items[0].menu_item_id == "boneless_6"
        assert customer is not None
        assert customer.order_count == 1
        assert customer.total_spend == Decimal("8.65")
