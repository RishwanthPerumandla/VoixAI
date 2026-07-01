"""Database configuration for the VoixAI API persistence layer."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent.parent.parent


def default_db_path() -> Path:
    explicit = os.getenv("VOIXAI_DB_PATH")
    if explicit:
        return Path(explicit)
    return ROOT_DIR / ".voixai" / "voixai.db"


def sqlite_url_from_path(path: str | os.PathLike[str]) -> str:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


def default_database_url() -> str:
    return os.getenv("DATABASE_URL") or os.getenv("VOIXAI_DATABASE_URL") or sqlite_url_from_path(default_db_path())


def build_engine(database_url: str | None = None) -> Engine:
    url = database_url or default_database_url()
    _ensure_sqlite_parent(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    parsed = urlparse(database_url)
    raw_path = unquote(parsed.path)
    if parsed.netloc:
        raw_path = f"//{parsed.netloc}{raw_path}"
    if os.name == "nt" and raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path[1:]
    db_path = Path(raw_path)
    if db_path.name and db_path.parent != Path("."):
        db_path.parent.mkdir(parents=True, exist_ok=True)


def build_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or build_engine(), expire_on_commit=False, future=True)


SessionLocal = build_session_factory()


@contextmanager
def session_scope(factory: sessionmaker[Session] = SessionLocal) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
