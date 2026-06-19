"""Durable persistence for VoixAI (M3+).

The shipped adapter is SQLite (stdlib ``sqlite3``), which gives durable storage
and idempotency with zero external infrastructure.

Design notes:
- Order submission is idempotent on ``idempotency_key`` via ``INSERT OR IGNORE``.
  A retried submit returns the original order instead of creating a duplicate.
- All writes use explicit ``BEGIN IMMEDIATE`` / ``COMMIT`` transactions to
  guarantee atomicity and prevent partial-write corruption.
- ``sqlite3`` calls are synchronous; the async endpoints wrap them in
  ``asyncio.to_thread`` and a re-entrant process-wide lock guards the connection.
- Foreign keys are enforced via ``PRAGMA foreign_keys=ON``.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path


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
    """A single voice call handled by the agent.

    A call row is created when the session starts (``status='in_progress'``) and
    finalized when it ends. The transcript is stored as a JSON array of turns so
    the dashboard can replay the conversation; aggregate columns (duration,
    outcome, sentiment) are denormalized for fast analytics queries.
    """

    call_id: str
    room_name: str
    scenario: str
    channel: str
    voice_provider: str
    llm_model: str
    status: str  # in_progress | completed | failed
    outcome: str  # order_placed | info_only | transfer | abandoned | unknown
    started_at: float
    ended_at: float | None
    duration_seconds: float | None
    turn_count: int
    sentiment: float | None  # 0.0 (negative) .. 1.0 (positive)
    language: str
    order_number: str | None
    transcript_json: str
    guardrail_violations: int
    error: str | None
    created_at: float


class SqliteStorage:
    """SQLite-backed implementation of the order + session repositories."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_number TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    room_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    subtotal TEXT NOT NULL,
                    tax TEXT NOT NULL,
                    total TEXT NOT NULL,
                    eta_minutes INTEGER NOT NULL,
                    order_json TEXT NOT NULL,
                    kitchen_ticket TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_room_name ON orders (room_name)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    room_name TEXT PRIMARY KEY,
                    runtime_config_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calls (
                    call_id TEXT PRIMARY KEY,
                    room_name TEXT NOT NULL,
                    scenario TEXT NOT NULL DEFAULT '',
                    channel TEXT NOT NULL DEFAULT '',
                    voice_provider TEXT NOT NULL DEFAULT '',
                    llm_model TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    outcome TEXT NOT NULL DEFAULT 'unknown',
                    started_at REAL NOT NULL,
                    ended_at REAL,
                    duration_seconds REAL,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    sentiment REAL,
                    language TEXT NOT NULL DEFAULT 'english',
                    order_number TEXT,
                    transcript_json TEXT NOT NULL DEFAULT '[]',
                    guardrail_violations INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_calls_started_at ON calls (started_at DESC)"
            )

    # --- orders -------------------------------------------------------------

    @staticmethod
    def _row_to_order(row: sqlite3.Row) -> OrderRecord:
        return OrderRecord(
            order_number=row["order_number"],
            idempotency_key=row["idempotency_key"],
            room_name=row["room_name"],
            status=row["status"],
            subtotal=row["subtotal"],
            tax=row["tax"],
            total=row["total"],
            eta_minutes=row["eta_minutes"],
            order_json=row["order_json"],
            kitchen_ticket=row["kitchen_ticket"],
            created_at=row["created_at"],
        )

    def get_order_by_idempotency_key(self, key: str) -> OrderRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM orders WHERE idempotency_key = ?", (key,)
            ).fetchone()
        return self._row_to_order(row) if row else None

    def get_order_by_number(self, order_number: str) -> OrderRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM orders WHERE order_number = ?", (order_number,)
            ).fetchone()
        return self._row_to_order(row) if row else None

    def list_orders(
        self, *, limit: int = 50, offset: int = 0, room_name: str | None = None
    ) -> tuple[list[OrderRecord], int]:
        where = "WHERE room_name = ?" if room_name else ""
        params: list[object] = [room_name] if room_name else []
        with self._lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM orders {where}", params
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"SELECT * FROM orders {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return [self._row_to_order(r) for r in rows], total

    def insert_order(self, record: OrderRecord) -> OrderRecord | None:
        """Atomically insert an order.

        Returns ``None`` when the ``idempotency_key`` already exists (the caller
        should look up and return the existing order). Uses ``INSERT OR IGNORE``
        inside an explicit ``BEGIN IMMEDIATE`` transaction so there is no
        check-then-insert race window.
        """
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = self._conn.execute(
                    """
                    INSERT OR IGNORE INTO orders (
                        order_number, idempotency_key, room_name, status,
                        subtotal, tax, total, eta_minutes, order_json,
                        kitchen_ticket, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.order_number,
                        record.idempotency_key,
                        record.room_name,
                        record.status,
                        record.subtotal,
                        record.tax,
                        record.total,
                        record.eta_minutes,
                        record.order_json,
                        record.kitchen_ticket,
                        record.created_at,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        if cursor.rowcount == 0:
            return None
        return record

    # --- sessions -----------------------------------------------------------

    def upsert_session(self, room_name: str, runtime_config_json: str) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO sessions (room_name, runtime_config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(room_name) DO UPDATE SET
                    runtime_config_json = excluded.runtime_config_json,
                    updated_at = excluded.updated_at
                """,
                (room_name, runtime_config_json, now, now),
            )

    def get_session(self, room_name: str) -> SessionRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE room_name = ?", (room_name,)
            ).fetchone()
        if not row:
            return None
        return SessionRecord(
            room_name=row["room_name"],
            runtime_config_json=row["runtime_config_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # --- calls --------------------------------------------------------------

    @staticmethod
    def _row_to_call(row: sqlite3.Row) -> CallRecord:
        return CallRecord(
            call_id=row["call_id"],
            room_name=row["room_name"],
            scenario=row["scenario"],
            channel=row["channel"],
            voice_provider=row["voice_provider"],
            llm_model=row["llm_model"],
            status=row["status"],
            outcome=row["outcome"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            duration_seconds=row["duration_seconds"],
            turn_count=row["turn_count"],
            sentiment=row["sentiment"],
            language=row["language"],
            order_number=row["order_number"],
            transcript_json=row["transcript_json"],
            guardrail_violations=row["guardrail_violations"],
            error=row["error"],
            created_at=row["created_at"],
        )

    def insert_call(self, record: CallRecord) -> CallRecord | None:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = self._conn.execute(
                    """
                    INSERT OR IGNORE INTO calls (
                        call_id, room_name, scenario, channel, voice_provider,
                        llm_model, status, outcome, started_at, ended_at,
                        duration_seconds, turn_count, sentiment, language,
                        order_number, transcript_json, guardrail_violations,
                        error, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.call_id,
                        record.room_name,
                        record.scenario,
                        record.channel,
                        record.voice_provider,
                        record.llm_model,
                        record.status,
                        record.outcome,
                        record.started_at,
                        record.ended_at,
                        record.duration_seconds,
                        record.turn_count,
                        record.sentiment,
                        record.language,
                        record.order_number,
                        record.transcript_json,
                        record.guardrail_violations,
                        record.error,
                        record.created_at,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        if cursor.rowcount == 0:
            return None
        return record

    # Columns the finalize call is allowed to update. Keeps the partial update
    # honest: the call_id and started_at are immutable once a call begins.
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
        if not updates:
            return self.get_call_by_id(call_id)
        assignments = ", ".join(f"{col} = ?" for col in updates)
        params = list(updates.values())
        params.append(call_id)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = self._conn.execute(
                    f"UPDATE calls SET {assignments} WHERE call_id = ?", params
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        if cursor.rowcount == 0:
            return None
        return self.get_call_by_id(call_id)

    def get_call_by_id(self, call_id: str) -> CallRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM calls WHERE call_id = ?", (call_id,)
            ).fetchone()
        return self._row_to_call(row) if row else None

    def list_calls(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        outcome: str | None = None,
        search: str | None = None,
    ) -> tuple[list[CallRecord], int]:
        where: list[str] = []
        params: list[object] = []
        if status:
            where.append("status = ?")
            params.append(status)
        if outcome:
            where.append("outcome = ?")
            params.append(outcome)
        if search:
            where.append("(room_name LIKE ? OR order_number LIKE ? OR transcript_json LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM calls {clause}", params
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"SELECT * FROM calls {clause} ORDER BY started_at DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return [self._row_to_call(r) for r in rows], total

    def list_calls_since(self, since: float) -> list[CallRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM calls WHERE started_at >= ? ORDER BY started_at ASC",
                (since,),
            ).fetchall()
        return [self._row_to_call(r) for r in rows]

    def count_orders(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]


def default_db_path() -> Path:
    explicit = os.getenv("VOIXAI_DB_PATH")
    if explicit:
        return Path(explicit)
    root = Path(__file__).resolve().parent.parent.parent
    return root / ".voixai" / "voixai.db"


def build_storage() -> SqliteStorage:
    """Construct the configured storage adapter.

    ``DATABASE_URL`` is reserved for the production Postgres adapter; until that
    adapter lands we always use the SQLite adapter so local dev needs no infra.
    """
    return SqliteStorage(default_db_path())
