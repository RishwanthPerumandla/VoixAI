"""Demo kitchen ticker — advances confirmed→in_kitchen→ready→completed on timers.

Toggle off by setting ``KITCHEN_TICKER_DISABLED=true`` in the environment or by
calling ``stop()`` in test teardown.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Callable

from services import OrderService

logger = logging.getLogger("voixai.kitchen_ticker")

# Default intervals (seconds) between each kitchen stage
STAGE_INTERVAL = int(os.getenv("KITCHEN_TICKER_INTERVAL", "30"))


@dataclass
class KitchenTicker:
    session_factory: Callable[[], object]  # returns a Session
    interval: int = STAGE_INTERVAL
    _task: asyncio.Task | None = field(default=None, repr=False, compare=False)

    def start(self) -> None:
        if os.getenv("KITCHEN_TICKER_DISABLED", "").lower() in ("true", "1", "yes"):
            logger.info("Kitchen ticker disabled via KITCHEN_TICKER_DISABLED")
            return
        self._task = asyncio.create_task(self._run())
        logger.info("Kitchen ticker started (interval=%ds)", self.interval)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Kitchen ticker stopped")

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            try:
                self._advance()
            except Exception:
                logger.exception("Kitchen ticker advance failed")

    def _advance(self) -> None:
        session = self.session_factory()
        try:
            svc = OrderService(session)
            advanced = svc.advance_kitchen_ticker()
            if advanced:
                logger.debug("Kitchen ticker advanced %d orders", advanced)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
