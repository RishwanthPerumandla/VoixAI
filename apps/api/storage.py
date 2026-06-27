"""Durable persistence adapter for VoixAI.

The public class name stays ``SqliteStorage`` for existing tests and endpoint
fixtures, but the implementation now uses SQLAlchemy models shared with the
Postgres/Alembic path. SQLite remains the fast, key-free test/dev database.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database import build_engine, build_session_factory, sqlite_url_from_path
from models import Base, CallRecordModel, Order, RuntimeSession
from services import format_money, parse_money


@dataclass
class OrderRecord:
    order_number: str
    idempotency_key: str
    room_name: str
    status: str
    subtotal: str
    tax: str
    total: str
    eta_minutes: int
    order_json: str
    kitchen_ticket: str
    created_at: float


@dataclass
class SessionRecord:
    room_name: str
    runtime_config_json: str
    created_at: float
    updated_at: float


@dataclass
class CallRecord:
    call_id: str
    room_name: str
    scenario: str
    channel: str
    voice_provider: str
    llm_model: str
    status: str
    outcome: str
    started_at: float
    ended_at: float | None
    duration_seconds: float | None
    turn_count: int
    sentiment: float | None
    language: str
    order_number: str | None
    transcript_json: str
    guardrail_violations: int
    error: str | None
    created_at: float


def _dt_to_epoch(value) -> float:
    if value is None:
        return time.time()
    if hasattr(value, "timestamp"):
        return float(value.timestamp())
    return float(value)


class SqliteStorage:
    """SQLAlchemy-backed implementation of order + session repositories."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._engine = build_engine(sqlite_url_from_path(self._db_path))
        self._Session = build_session_factory(self._engine)
        Base.metadata.create_all(self._engine)

    # --- orders -------------------------------------------------------------

    @staticmethod
    def _model_to_order(row: Order) -> OrderRecord:
        return OrderRecord(
            order_number=row.public_code,
            idempotency_key=row.idempotency_key or "",
            room_name=row.room_name or "",
            status=row.status,
            subtotal=format_money(row.subtotal),
            tax=format_money(row.tax),
            total=format_money(row.total),
            eta_minutes=row.eta_minutes,
            order_json=row.order_json,
            kitchen_ticket=row.kitchen_ticket,
            created_at=_dt_to_epoch(row.placed_at or row.updated_at),
        )

    def get_order_by_idempotency_key(self, key: str) -> OrderRecord | None:
        with self._lock, self._Session() as session:
            row = session.scalar(select(Order).where(Order.idempotency_key == key))
            return self._model_to_order(row) if row else None

    def get_order_by_number(self, order_number: str) -> OrderRecord | None:
        with self._lock, self._Session() as session:
            row = session.scalar(select(Order).where(Order.public_code == order_number))
            return self._model_to_order(row) if row else None

    def list_orders(
        self, *, limit: int = 50, offset: int = 0, room_name: str | None = None
    ) -> tuple[list[OrderRecord], int]:
        with self._lock, self._Session() as session:
            filters = [Order.room_name == room_name] if room_name else []
            total = session.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
            rows = session.scalars(
                select(Order)
                .where(*filters)
                .order_by(Order.placed_at.desc().nullslast(), Order.updated_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._model_to_order(r) for r in rows], int(total)

    def insert_order(self, record: OrderRecord) -> OrderRecord | None:
        with self._lock, self._Session() as session:
            row = Order(
                public_code=record.order_number,
                idempotency_key=record.idempotency_key,
                room_name=record.room_name,
                status=record.status,
                channel="voice",
                subtotal=parse_money(record.subtotal),
                tax=parse_money(record.tax),
                total=parse_money(record.total),
                eta_minutes=record.eta_minutes,
                order_json=record.order_json,
                kitchen_ticket=record.kitchen_ticket,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return None
            return record

    # --- sessions -----------------------------------------------------------

    def upsert_session(self, room_name: str, runtime_config_json: str) -> None:
        now = time.time()
        with self._lock, self._Session() as session:
            row = session.get(RuntimeSession, room_name)
            if row is None:
                row = RuntimeSession(
                    room_name=room_name,
                    runtime_config_json=runtime_config_json,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.runtime_config_json = runtime_config_json
                row.updated_at = now
            session.commit()

    def get_session(self, room_name: str) -> SessionRecord | None:
        with self._lock, self._Session() as session:
            row = session.get(RuntimeSession, room_name)
            if row is None:
                return None
            return SessionRecord(
                room_name=row.room_name,
                runtime_config_json=row.runtime_config_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    # --- calls --------------------------------------------------------------

    @staticmethod
    def _model_to_call(row: CallRecordModel) -> CallRecord:
        return CallRecord(
            call_id=row.call_id,
            room_name=row.room_name,
            scenario=row.scenario,
            channel=row.channel,
            voice_provider=row.voice_provider,
            llm_model=row.llm_model,
            status=row.status,
            outcome=row.outcome,
            started_at=row.started_at,
            ended_at=row.ended_at,
            duration_seconds=row.duration_seconds,
            turn_count=row.turn_count,
            sentiment=row.sentiment,
            language=row.language,
            order_number=row.order_number,
            transcript_json=row.transcript_json,
            guardrail_violations=row.guardrail_violations,
            error=row.error,
            created_at=row.created_at,
        )

    def insert_call(self, record: CallRecord) -> CallRecord | None:
        with self._lock, self._Session() as session:
            row = CallRecordModel(
                call_id=record.call_id,
                room_name=record.room_name,
                scenario=record.scenario,
                channel=record.channel,
                voice_provider=record.voice_provider,
                llm_model=record.llm_model,
                status=record.status,
                outcome=record.outcome,
                started_at=record.started_at,
                ended_at=record.ended_at,
                duration_seconds=record.duration_seconds,
                turn_count=record.turn_count,
                sentiment=record.sentiment,
                language=record.language,
                order_number=record.order_number,
                transcript_json=record.transcript_json,
                guardrail_violations=record.guardrail_violations,
                error=record.error,
                created_at=record.created_at,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return None
            return record

    _CALL_UPDATABLE = (
        "status",
        "outcome",
        "ended_at",
        "duration_seconds",
        "turn_count",
        "sentiment",
        "language",
        "order_number",
        "transcript_json",
        "guardrail_violations",
        "error",
        "scenario",
        "channel",
        "voice_provider",
        "llm_model",
    )

    def update_call(self, call_id: str, **fields: object) -> CallRecord | None:
        updates = {k: v for k, v in fields.items() if k in self._CALL_UPDATABLE and v is not None}
        with self._lock, self._Session() as session:
            row = session.get(CallRecordModel, call_id)
            if row is None:
                return None
            for key, value in updates.items():
                setattr(row, key, value)
            session.commit()
            session.refresh(row)
            return self._model_to_call(row)

    def get_call_by_id(self, call_id: str) -> CallRecord | None:
        with self._lock, self._Session() as session:
            row = session.get(CallRecordModel, call_id)
            return self._model_to_call(row) if row else None

    def list_calls(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        outcome: str | None = None,
        search: str | None = None,
    ) -> tuple[list[CallRecord], int]:
        with self._lock, self._Session() as session:
            filters = []
            if status:
                filters.append(CallRecordModel.status == status)
            if outcome:
                filters.append(CallRecordModel.outcome == outcome)
            if search:
                like = f"%{search}%"
                filters.append(
                    (CallRecordModel.room_name.like(like))
                    | (CallRecordModel.order_number.like(like))
                    | (CallRecordModel.transcript_json.like(like))
                )
            total = session.scalar(select(func.count()).select_from(CallRecordModel).where(*filters)) or 0
            rows = session.scalars(
                select(CallRecordModel)
                .where(*filters)
                .order_by(CallRecordModel.started_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._model_to_call(r) for r in rows], int(total)

    def list_calls_since(self, since: float) -> list[CallRecord]:
        with self._lock, self._Session() as session:
            rows = session.scalars(
                select(CallRecordModel)
                .where(CallRecordModel.started_at >= since)
                .order_by(CallRecordModel.started_at.asc())
            ).all()
            return [self._model_to_call(r) for r in rows]

    def count_orders(self) -> int:
        with self._lock, self._Session() as session:
            return int(session.scalar(select(func.count()).select_from(Order)) or 0)


def default_db_path() -> Path:
    explicit = os.getenv("VOIXAI_DB_PATH")
    if explicit:
        return Path(explicit)
    root = Path(__file__).resolve().parent.parent.parent
    return root / ".voixai" / "voixai.db"


def build_storage() -> SqliteStorage:
    return SqliteStorage(default_db_path())
