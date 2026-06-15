"""Durable persistence for VoixAI (M3).

This is the storage *port* for the API. Orders and sessions are persisted behind
a small repository interface so the backing store can change without touching
the HTTP layer or the ordering domain.

The shipped adapter is SQLite (stdlib ``sqlite3``), which gives durable storage
and idempotency with zero external infrastructure — the local demo keeps working
with no Postgres/Redis to stand up. A Postgres adapter is a drop-in via the same
``Storage`` surface (gate it on ``DATABASE_URL`` in production).

Design notes:
- Order submission is idempotent on ``idempotency_key`` (a unique index). A
  retried submit returns the original order instead of creating a duplicate.
- ``sqlite3`` calls are synchronous; the async endpoints wrap them in
  ``asyncio.to_thread`` and a process-wide lock guards the shared connection.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path


class DuplicateKeyError(Exception):
    """Raised when an insert violates a uniqueness constraint (idempotency key
    or order number). The caller decides whether to replay or retry."""


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


class SqliteStorage:
    """SQLite-backed implementation of the order + session repositories."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
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
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    room_name TEXT PRIMARY KEY,
                    runtime_config_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
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

    def insert_order(self, record: OrderRecord) -> None:
        try:
            with self._lock, self._conn:
                self._conn.execute(
                    """
                    INSERT INTO orders (
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
        except sqlite3.IntegrityError as exc:
            raise DuplicateKeyError(str(exc)) from exc

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
