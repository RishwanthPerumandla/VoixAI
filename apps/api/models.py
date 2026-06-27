"""SQLAlchemy models for VoixAI Phase 1 persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON as SAJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()
JsonType = SAJSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid4().hex


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(32), primary_key=True, default=new_id)
    phone = Column(String(32), nullable=False, unique=True, index=True)
    name = Column(String(160), nullable=True)
    preferred_language = Column(String(32), nullable=True)
    order_count = Column(Integer, nullable=False, default=0)
    total_spend = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    orders = relationship("Order", back_populates="customer")


class Store(Base):
    __tablename__ = "stores"

    id = Column(String(32), primary_key=True, default=new_id)
    name = Column(String(160), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(32), nullable=False)
    timezone = Column(String(64), nullable=False, default="America/Chicago")
    hours = Column(JsonType, nullable=False, default=dict)
    is_open_now = Column(Boolean, nullable=False, default=False)

    orders = relationship("Order", back_populates="store")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(String(80), primary_key=True)
    sku = Column(String(80), nullable=False, unique=True, index=True)
    name = Column(String(160), nullable=False)
    category = Column(String(80), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    options_schema = Column(JsonType, nullable=False, default=dict)

    order_items = relationship("OrderItem", back_populates="menu_item")


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(String(32), primary_key=True, default=new_id)
    call_id = Column(String(120), nullable=False, unique=True, index=True)
    room_name = Column(String(255), nullable=False, index=True)
    current_node = Column(String(80), nullable=True)
    outcome = Column(String(40), nullable=True)
    recording_url = Column(Text, nullable=True)
    call_intent = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    orders = relationship("Order", back_populates="source_call")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
        Index("idx_orders_room_name", "room_name"),
        Index("idx_orders_placed_at", "placed_at"),
        Index("idx_orders_customer_status", "customer_id", "status"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    public_code = Column(String(32), nullable=False, unique=True, index=True)
    idempotency_key = Column(String(255), nullable=True)
    customer_id = Column(String(32), ForeignKey("customers.id"), nullable=True)
    store_id = Column(String(32), ForeignKey("stores.id"), nullable=True)
    source_call_id = Column(String(32), ForeignKey("call_sessions.id"), nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    channel = Column(String(32), nullable=False, default="voice")
    room_name = Column(String(255), nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tax = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    currency = Column(String(3), nullable=False, default="USD")
    eta_minutes = Column(Integer, nullable=False, default=20)
    order_json = Column(Text, nullable=False, default="{}")
    kitchen_ticket = Column(Text, nullable=False, default="")
    placed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    customer = relationship("Customer", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    source_call = relationship("CallSession", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(32), primary_key=True, default=new_id)
    order_id = Column(String(32), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(String(80), ForeignKey("menu_items.id"), nullable=True)
    name = Column(String(160), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    line_total = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    modifiers = Column(JsonType, nullable=False, default=dict)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")


class TranscriptTurnModel(Base):
    __tablename__ = "transcript_turns"

    id = Column(String(32), primary_key=True, default=new_id)
    call_id = Column(String(120), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    speaker = Column(String(32), nullable=False)
    text = Column(Text, nullable=False, default="")
    ts_start = Column(Float, nullable=True)
    ts_end = Column(Float, nullable=True)
    stt_confidence = Column(Float, nullable=True)
    state_node = Column(String(80), nullable=True)
    intent = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (Index("ix_transcript_turns_call_seq", "call_id", "seq"),)


class CallEventModel(Base):
    __tablename__ = "call_events"

    id = Column(String(32), primary_key=True, default=new_id)
    call_id = Column(String(120), nullable=False, index=True)
    ts = Column(Float, nullable=False)
    type = Column(String(80), nullable=False, index=True)
    payload = Column(JsonType, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (Index("ix_call_events_call_ts", "call_id", "ts"),)


class EscalationModel(Base):
    __tablename__ = "escalations"

    id = Column(String(32), primary_key=True, default=new_id)
    call_id = Column(String(120), nullable=False, index=True)
    reason_code = Column(String(80), nullable=False)
    frustration_score = Column(Float, nullable=False, default=0.0)
    triggered_at = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class RuntimeSession(Base):
    __tablename__ = "sessions"

    room_name = Column(String(255), primary_key=True)
    runtime_config_json = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)


class CallRecordModel(Base):
    __tablename__ = "calls"

    call_id = Column(String(120), primary_key=True)
    room_name = Column(String(255), nullable=False, index=True)
    scenario = Column(String(120), nullable=False, default="")
    channel = Column(String(32), nullable=False, default="")
    voice_provider = Column(String(64), nullable=False, default="")
    llm_model = Column(String(120), nullable=False, default="")
    status = Column(String(32), nullable=False, default="in_progress")
    outcome = Column(String(32), nullable=False, default="unknown")
    call_intent = Column(String(80), nullable=True)
    started_at = Column(Float, nullable=False)
    ended_at = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    turn_count = Column(Integer, nullable=False, default=0)
    sentiment = Column(Float, nullable=True)
    language = Column(String(32), nullable=False, default="english")
    order_number = Column(String(32), nullable=True)
    recording_url = Column(Text, nullable=True)
    transcript_json = Column(Text, nullable=False, default="[]")
    guardrail_violations = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(Float, nullable=False)

    __table_args__ = (Index("idx_calls_started_at", "started_at"),)
