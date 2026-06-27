"""Persistence services for customers, stores, menu, and orders."""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from models import CallSession, Customer, MenuItem, Order, OrderItem, Store, utc_now
from voix_ordering import MENU_ITEMS, MODIFIER_OPTIONS


ACTIVE_ORDER_STATUSES = ("confirmed", "in_kitchen", "ready")
ORDER_STATUSES = ("draft", "confirmed", "in_kitchen", "ready", "completed", "cancelled")


def normalize_phone(phone: str | None) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def phone_from_caller_id(caller_id: str | None) -> str:
    return normalize_phone(caller_id)


def parse_money(value: str | Decimal | int | float | None) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    cleaned = str(value or "0").replace("$", "").replace(",", "").strip()
    return Decimal(cleaned or "0").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value: Decimal | int | float | str | None) -> str:
    amount = parse_money(value)
    return f"${amount:,.2f}"


@dataclass(frozen=True)
class OrderLineInput:
    menu_item_id: str
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    modifiers: dict[str, object]


class CustomerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_by_phone(
        self,
        phone: str,
        *,
        name: str | None = None,
        preferred_language: str | None = None,
    ) -> Customer:
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError("phone is required")

        customer = self.session.scalar(select(Customer).where(Customer.phone == normalized))
        now = utc_now()
        if customer is None:
            customer = Customer(
                phone=normalized,
                name=(name or "").strip() or None,
                preferred_language=(preferred_language or "").strip() or None,
                created_at=now,
                last_seen_at=now,
            )
            self.session.add(customer)
            self.session.flush()
            return customer

        if name and name.strip():
            customer.name = name.strip()
        if preferred_language and preferred_language.strip():
            customer.preferred_language = preferred_language.strip()
        customer.last_seen_at = now
        self.session.flush()
        return customer

    def attach_name(self, customer_id: str, name: str) -> Customer:
        customer = self.session.get(Customer, customer_id)
        if customer is None:
            raise LookupError("customer not found")
        customer.name = name.strip()
        customer.last_seen_at = utc_now()
        self.session.flush()
        return customer

    def roll_up_confirmed_order(self, customer: Customer, total: Decimal) -> None:
        customer.order_count = int(customer.order_count or 0) + 1
        customer.total_spend = parse_money(customer.total_spend) + parse_money(total)
        customer.last_seen_at = utc_now()


class StoreService:
    DEMO_STORE_ID = "demo-wingstop-dallas"

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def demo_hours() -> dict[str, dict[str, str]]:
        return {
            day: {"open": "10:30", "close": "23:00"}
            for day in ("mon", "tue", "wed", "thu", "sun")
        } | {
            day: {"open": "10:30", "close": "00:00"}
            for day in ("fri", "sat")
        }

    def seed_demo_store(self) -> Store:
        store = self.session.get(Store, self.DEMO_STORE_ID)
        if store is None:
            store = Store(
                id=self.DEMO_STORE_ID,
                name="Wingstop Dallas Demo",
                address="Demo Store - Dallas, TX",
                phone="2145550100",
                timezone="America/Chicago",
                hours=self.demo_hours(),
                is_open_now=True,
            )
            self.session.add(store)
        else:
            store.name = "Wingstop Dallas Demo"
            store.address = "Demo Store - Dallas, TX"
            store.phone = "2145550100"
            store.timezone = "America/Chicago"
            store.hours = self.demo_hours()
        self.session.flush()
        return store

    def get_default_store(self) -> Store:
        store = self.session.get(Store, self.DEMO_STORE_ID)
        if store is None:
            store = self.seed_demo_store()
        return store

    def is_open_now(self, store: Store, *, at: datetime | None = None) -> bool:
        check_time = at or datetime.now(timezone.utc)
        local_time = check_time.time()
        day_key = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[check_time.weekday()]
        window = (store.hours or {}).get(day_key)
        if not window:
            return False
        open_time = datetime.strptime(window["open"], "%H:%M").time()
        close_time = datetime.strptime(window["close"], "%H:%M").time()
        if close_time <= open_time:
            return local_time >= open_time or local_time < close_time
        return open_time <= local_time < close_time


class MenuSeedService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed_menu(self) -> int:
        count = 0
        for item in MENU_ITEMS.values():
            schema = {
                "aliases": list(item.aliases),
                "required_modifier_group_ids": list(item.required_modifier_group_ids),
                "optional_modifier_group_ids": list(item.optional_modifier_group_ids),
                "requires_flavors": item.requires_flavors,
                "max_flavors": item.max_flavors,
                "included_dip_count": item.included_dip_count,
                "supports_piece_preference": item.supports_piece_preference,
                "allowed_piece_preference_ids": list(item.allowed_piece_preference_ids),
                "prep_time_minutes": item.prep_time_minutes,
                "order_style": item.order_style,
                "item_kind": item.item_kind,
            }
            row = self.session.get(MenuItem, item.id)
            if row is None:
                row = MenuItem(id=item.id, sku=item.id, name=item.display_name)
                self.session.add(row)
            row.sku = item.id
            row.name = item.display_name
            row.category = item.category
            row.base_price = item.base_price
            row.is_available = item.available
            row.options_schema = schema
            count += 1
        self.session.flush()
        return count


class ConversationSessionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start_or_resume(self, *, call_id: str, room_name: str, current_node: str | None = None) -> CallSession:
        row = self.session.scalar(select(CallSession).where(CallSession.call_id == call_id))
        if row is None:
            row = CallSession(
                call_id=call_id,
                room_name=room_name,
                current_node=current_node or "GREETING",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.session.add(row)
        else:
            row.room_name = room_name or row.room_name
            if current_node:
                row.current_node = current_node
            row.updated_at = utc_now()
        self.session.flush()
        return row

    def set_current_node(self, *, call_id: str, room_name: str, current_node: str) -> CallSession:
        row = self.start_or_resume(call_id=call_id, room_name=room_name, current_node=current_node)
        row.current_node = current_node
        row.updated_at = utc_now()
        self.session.flush()
        return row

    def identify(
        self,
        *,
        call_id: str,
        room_name: str,
        caller_id: str | None = None,
        phone: str | None = None,
    ) -> tuple[CallSession, Customer | None, bool, Order | None]:
        call_session = self.start_or_resume(call_id=call_id, room_name=room_name, current_node="IDENTIFY")
        normalized_phone = normalize_phone(phone) or phone_from_caller_id(caller_id)
        if not normalized_phone:
            return call_session, None, False, None

        existing = self.session.scalar(select(Customer).where(Customer.phone == normalized_phone))
        is_returning = existing is not None
        customer = CustomerService(self.session).upsert_by_phone(normalized_phone)
        latest_order = OrderService(self.session).get_latest_by_phone(normalized_phone)
        self.session.flush()
        return call_session, customer, is_returning, latest_order


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_draft(
        self,
        *,
        public_code: str,
        customer: Customer | None,
        store: Store | None,
        room_name: str | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        existing = self._by_idempotency_key(idempotency_key) if idempotency_key else None
        if existing is not None:
            return existing
        order = Order(
            public_code=public_code,
            idempotency_key=idempotency_key,
            customer=customer,
            store=store,
            status="draft",
            channel="voice",
            room_name=room_name,
            placed_at=None,
        )
        self.session.add(order)
        self.session.flush()
        return order

    def mutate_lines(
        self,
        order: Order,
        lines: Iterable[OrderLineInput],
        *,
        subtotal: Decimal,
        tax: Decimal,
        total: Decimal,
        eta_minutes: int,
        order_json: str = "{}",
        kitchen_ticket: str = "",
    ) -> Order:
        order.items.clear()
        self.session.flush()
        for line in lines:
            order.items.append(
                OrderItem(
                    menu_item_id=line.menu_item_id,
                    name=line.name,
                    quantity=max(1, int(line.quantity)),
                    unit_price=parse_money(line.unit_price),
                    line_total=parse_money(line.line_total),
                    modifiers=dict(line.modifiers),
                )
            )
        order.subtotal = parse_money(subtotal)
        order.tax = parse_money(tax)
        order.total = parse_money(total)
        order.eta_minutes = int(eta_minutes)
        order.order_json = order_json
        order.kitchen_ticket = kitchen_ticket
        order.updated_at = utc_now()
        self.session.flush()
        return order

    def confirm(
        self,
        order: Order,
        *,
        public_code: str | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        existing = self._by_idempotency_key(idempotency_key) if idempotency_key else None
        if existing is not None and existing.id != order.id:
            return existing

        if public_code:
            order.public_code = public_code
        if idempotency_key:
            order.idempotency_key = idempotency_key
        if order.status == "confirmed":
            return order
        if order.status not in {"draft", "confirmed"}:
            raise ValueError(f"cannot confirm order from status {order.status}")
        order.status = "confirmed"
        order.placed_at = order.placed_at or utc_now()
        order.updated_at = utc_now()
        if order.customer is not None:
            CustomerService(self.session).roll_up_confirmed_order(order.customer, order.total)
        self.session.flush()
        return order

    def cancel(self, order: Order) -> Order:
        if order.status in {"completed", "cancelled"}:
            return order
        order.status = "cancelled"
        order.updated_at = utc_now()
        self.session.flush()
        return order

    def get_by_code(self, public_code: str) -> Order | None:
        return self.session.scalar(select(Order).where(Order.public_code == public_code))

    def get_latest_by_phone(self, phone: str) -> Order | None:
        normalized = normalize_phone(phone)
        if not normalized:
            return None
        return self.session.scalar(
            select(Order)
            .join(Customer)
            .where(Customer.phone == normalized)
            .order_by(Order.placed_at.desc().nullslast(), Order.updated_at.desc())
            .limit(1)
        )

    def get_latest_active_by_phone(self, phone: str) -> Order | None:
        normalized = normalize_phone(phone)
        if not normalized:
            return None
        return self.session.scalar(
            select(Order)
            .join(Customer)
            .where(Customer.phone == normalized, Order.status.in_(ACTIVE_ORDER_STATUSES))
            .order_by(Order.placed_at.desc().nullslast(), Order.updated_at.desc())
            .limit(1)
        )

    def _by_idempotency_key(self, key: str | None) -> Order | None:
        if not key:
            return None
        return self.session.scalar(select(Order).where(Order.idempotency_key == key))


def make_public_code(session: Session, *, prefix: str = "WS") -> str:
    for _ in range(20):
        code = f"{prefix}-{random.randint(1000, 9999)}"
        if session.scalar(select(func.count()).select_from(Order).where(Order.public_code == code)) == 0:
            return code
    return f"{prefix}-{int(time.time() * 1000) % 1000000:06d}"


def line_inputs_from_quote(order_payload: dict[str, object], quote_lines: list[object]) -> list[OrderLineInput]:
    payload_lines = order_payload.get("items", []) if isinstance(order_payload, dict) else []
    by_line_id = {
        str(line.get("line_id")): line
        for line in payload_lines
        if isinstance(line, dict) and line.get("line_id")
    }
    inputs: list[OrderLineInput] = []
    for line in quote_lines:
        line_id = str(getattr(line, "line_id", ""))
        payload_line = by_line_id.get(line_id, {})
        modifier_ids = list(payload_line.get("selected_modifier_ids", [])) if isinstance(payload_line, dict) else []
        inputs.append(
            OrderLineInput(
                menu_item_id=str(payload_line.get("item_id", "")) if isinstance(payload_line, dict) else "",
                name=str(getattr(line, "name", "")),
                quantity=int(getattr(line, "quantity", 1)),
                unit_price=parse_money(getattr(line, "unit_price", "0")),
                line_total=parse_money(getattr(line, "line_subtotal", "0")),
                modifiers={
                    "flavor_ids": list(payload_line.get("selected_flavor_ids", [])) if isinstance(payload_line, dict) else [],
                    "modifier_ids": modifier_ids,
                    "modifier_names": [
                        MODIFIER_OPTIONS[mid].display_name for mid in modifier_ids if mid in MODIFIER_OPTIONS
                    ],
                    "notes": str(payload_line.get("notes", "")) if isinstance(payload_line, dict) else "",
                },
            )
        )
    return inputs
