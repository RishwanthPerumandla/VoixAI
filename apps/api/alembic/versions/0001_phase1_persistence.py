"""phase 1 persistence foundation

Revision ID: 0001_phase1_persistence
Revises:
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_phase1_persistence"
down_revision = None
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("preferred_language", sa.String(length=32), nullable=True),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spend", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("phone"),
    )
    op.create_index("ix_customers_phone", "customers", ["phone"])

    op.create_table(
        "stores",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Chicago"),
        sa.Column("hours", json_type, nullable=False),
        sa.Column("is_open_now", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("options_schema", json_type, nullable=False),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_menu_items_sku", "menu_items", ["sku"])

    op.create_table(
        "call_sessions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("call_id", sa.String(length=120), nullable=False),
        sa.Column("room_name", sa.String(length=255), nullable=False),
        sa.Column("current_node", sa.String(length=80), nullable=True),
        sa.Column("outcome", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("call_id"),
    )
    op.create_index("ix_call_sessions_call_id", "call_sessions", ["call_id"])
    op.create_index("ix_call_sessions_room_name", "call_sessions", ["room_name"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("public_code", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("customer_id", sa.String(length=32), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("store_id", sa.String(length=32), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("source_call_id", sa.String(length=32), sa.ForeignKey("call_sessions.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="voice"),
        sa.Column("room_name", sa.String(length=255), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("tax", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("eta_minutes", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("order_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("kitchen_ticket", sa.Text(), nullable=False, server_default=""),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("public_code"),
        sa.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
    )
    op.create_index("ix_orders_public_code", "orders", ["public_code"])
    op.create_index("idx_orders_room_name", "orders", ["room_name"])
    op.create_index("idx_orders_placed_at", "orders", ["placed_at"])
    op.create_index("idx_orders_customer_status", "orders", ["customer_id", "status"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("order_id", sa.String(length=32), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("menu_item_id", sa.String(length=80), sa.ForeignKey("menu_items.id"), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("modifiers", json_type, nullable=False),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "sessions",
        sa.Column("room_name", sa.String(length=255), primary_key=True),
        sa.Column("runtime_config_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )

    op.create_table(
        "calls",
        sa.Column("call_id", sa.String(length=120), primary_key=True),
        sa.Column("room_name", sa.String(length=255), nullable=False),
        sa.Column("scenario", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("voice_provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("llm_model", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("started_at", sa.Float(), nullable=False),
        sa.Column("ended_at", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sentiment", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=False, server_default="english"),
        sa.Column("order_number", sa.String(length=32), nullable=True),
        sa.Column("transcript_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("guardrail_violations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_calls_room_name", "calls", ["room_name"])
    op.create_index("idx_calls_started_at", "calls", ["started_at"])


def downgrade() -> None:
    op.drop_table("calls")
    op.drop_table("sessions")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("idx_orders_customer_status", table_name="orders")
    op.drop_index("idx_orders_placed_at", table_name="orders")
    op.drop_index("idx_orders_room_name", table_name="orders")
    op.drop_index("ix_orders_public_code", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_call_sessions_room_name", table_name="call_sessions")
    op.drop_index("ix_call_sessions_call_id", table_name="call_sessions")
    op.drop_table("call_sessions")
    op.drop_index("ix_menu_items_sku", table_name="menu_items")
    op.drop_table("menu_items")
    op.drop_table("stores")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_table("customers")
