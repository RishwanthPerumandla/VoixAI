"""phase 6 frustration monitor — escalations table

Revision ID: 0003_escalations
Revises: 0002_observability
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_escalations"
down_revision = "0002_observability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "escalations",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("call_id", sa.String(length=120), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("frustration_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("triggered_at", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_escalations_call_id", "escalations", ["call_id"])


def downgrade() -> None:
    op.drop_index("ix_escalations_call_id", table_name="escalations")
    op.drop_table("escalations")
