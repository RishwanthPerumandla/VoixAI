from __future__ import annotations

from pathlib import Path

import pytest

import main as api_main
from models import CallSession, Customer
from storage import SqliteStorage


@pytest.fixture()
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqliteStorage:
    store = SqliteStorage(tmp_path / "conversation.db")
    monkeypatch.setattr(api_main, "ORDER_STORAGE", store)
    return store


def _confirmed_payload(phone: str = "2145550101") -> "api_main.OrderPayload":
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
        phone=phone,
        confirmed=True,
        total_shown=True,
        recap_readback=True,
        pos_validation_passed=True,
        status="confirmed_pending_submit",
    )


@pytest.mark.asyncio
async def test_conversation_node_persists_for_reconnect(storage: SqliteStorage) -> None:
    updated = await api_main.update_conversation_node(
        "call-node",
        api_main.ConversationNodeUpdateRequest(room_name="room-node", current_node="ORDER"),
    )
    fetched = await api_main.get_conversation_session("call-node")

    assert updated.current_node == "ORDER"
    assert fetched.current_node == "ORDER"

    with storage._Session() as session:
        row = session.query(CallSession).filter_by(call_id="call-node").one()
        assert row.room_name == "room-node"


@pytest.mark.asyncio
async def test_identify_returning_caller_by_phone_surfaces_last_order(storage: SqliteStorage) -> None:
    order = await api_main.submit_order(
        api_main.OrderSubmitRequest(room_name="room-order", order=_confirmed_payload())
    )

    identified = await api_main.identify_conversation_caller(
        api_main.ConversationIdentifyRequest(
            call_id="call-identify",
            room_name="room-identify",
            caller_id="+1 (214) 555-0101",
        )
    )

    assert identified.is_returning is True
    assert identified.name == "Sam"
    assert identified.phone == "2145550101"
    assert identified.last_order_code == order.order_number
    assert order.order_number in (identified.last_order_summary or "")


@pytest.mark.asyncio
async def test_name_capture_persists_to_customer(storage: SqliteStorage) -> None:
    identified = await api_main.identify_conversation_caller(
        api_main.ConversationIdentifyRequest(
            call_id="call-name",
            room_name="room-name",
            phone="214-555-0199",
        )
    )

    named = await api_main.persist_conversation_name(
        api_main.ConversationNameRequest(
            call_id="call-name",
            room_name="room-name",
            customer_id=identified.customer_id,
            phone="214-555-0199",
            name="Nithin",
        )
    )

    assert named.name == "Nithin"
    with storage._Session() as session:
        customer = session.query(Customer).filter_by(phone="2145550199").one()
        assert customer.name == "Nithin"
