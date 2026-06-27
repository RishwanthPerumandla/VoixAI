"""Seed the Phase 1 persistence database with demo store and menu data."""

from __future__ import annotations

from database import build_engine, build_session_factory
from models import Base
from services import MenuSeedService, StoreService


def seed() -> dict[str, object]:
    engine = build_engine()
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    with session_factory() as session:
        store = StoreService(session).seed_demo_store()
        menu_count = MenuSeedService(session).seed_menu()
        session.commit()
        return {"store_id": store.id, "menu_items": menu_count}


if __name__ == "__main__":
    result = seed()
    print(f"Seeded store={result['store_id']} menu_items={result['menu_items']}")
