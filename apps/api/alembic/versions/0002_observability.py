"""phase 5 observability: transcript_turns, call_events, recording_url, call_intent

Revision ID: 0002_observability
Revises: 0001_phase1_persistence
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_observability"
down_revision = "0001_phase1_persistence"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "transcript_turns",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("call_id", sa.String(length=120), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("ts_start", sa.Float(), nullable=True),
        sa.Column("ts_end", sa.Float(), nullable=True),
        sa.Column("stt_confidence", sa.Float(), nullable=True),
        sa.Column("state_node", sa.String(length=80), nullable=True),
        sa.Column("intent", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transcript_turns_call_id", "transcript_turns", ["call_id"])
    op.create_index("ix_transcript_turns_call_seq", "transcript_turns", ["call_id", "seq"])

    op.create_table(
        "call_events",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("call_id", sa.String(length=120), nullable=False),
        sa.Column("ts", sa.Float(), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_call_events_call_id", "call_events", ["call_id"])
    op.create_index("ix_call_events_type", "call_events", ["type"])
    op.create_index("ix_call_events_call_ts", "call_events", ["call_id", "ts"])

    op.add_column(
        "call_sessions",
        sa.Column("recording_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "call_sessions",
        sa.Column("call_intent", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call_sessions", "call_intent")
    op.drop_column("call_sessions", "recording_url")
    op.drop_index("ix_call_events_call_ts", table_name="call_events")
    op.drop_index("ix_call_events_type", table_name="call_events")
    op.drop_index("ix_call_events_call_id", table_name="call_events")
    op.drop_table("call_events")
    op.drop_index("ix_transcript_turns_call_seq", table_name="transcript_turns")
    op.drop_index("ix_transcript_turns_call_id", table_name="transcript_turns")
    op.drop_table("transcript_turns")
