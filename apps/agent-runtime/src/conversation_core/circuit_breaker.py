from __future__ import annotations

import functools
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("agent.circuit_breaker")


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_retries: int = 3
    jitter_max_seconds: float = 0.5

    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_at: float = 0.0
    _half_open_tries: int = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_at >= self.recovery_timeout_seconds:
                logger.info("Circuit breaker transitioning OPEN -> HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_tries = 0
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN

    def call(self, fn, *args, fallback=None, **kwargs):
        if self.is_open:
            logger.warning("Circuit breaker OPEN — using fallback")
            return self._use_fallback(fallback, *args, **kwargs)

        if self.is_half_open and self._half_open_tries >= self.half_open_max_retries:
            logger.warning("Circuit breaker HALF_OPEN max retries reached — using fallback")
            return self._use_fallback(fallback, *args, **kwargs)

        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._record_failure(exc)
            if fallback is not None:
                logger.warning("Circuit breaker call failed — using fallback: %s", exc)
                return self._use_fallback(fallback, *args, **kwargs)
            raise

        self._record_success()
        return result

    async def acall(self, fn, *args, fallback=None, **kwargs):
        if self.is_open:
            logger.warning("Circuit breaker OPEN — using fallback")
            return self._use_fallback(fallback, *args, **kwargs)

        if self.is_half_open and self._half_open_tries >= self.half_open_max_retries:
            logger.warning("Circuit breaker HALF_OPEN max retries reached — using fallback")
            return self._use_fallback(fallback, *args, **kwargs)

        try:
            result = await fn(*args, **kwargs)
        except Exception as exc:
            self._record_failure(exc)
            if fallback is not None:
                logger.warning("Circuit breaker call failed — using fallback: %s", exc)
                return self._use_fallback(fallback, *args, **kwargs)
            raise

        self._record_success()
        return result

    def _record_failure(self, exc: Exception) -> None:
        self._failure_count += 1
        self._last_failure_at = time.time()
        logger.warning("Circuit breaker failure %d/%d: %s", self._failure_count, self.failure_threshold, exc)
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_tries += 1
        if self._failure_count >= self.failure_threshold:
            logger.warning("Circuit breaker threshold reached — opening")
            self._state = CircuitState.OPEN

    def _record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker HALF_OPEN call succeeded — closing")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_tries = 0
        elif self._failure_count > 0:
            self._failure_count = max(0, self._failure_count - 1)

    def _use_fallback(self, fallback, *args, **kwargs):
        if callable(fallback):
            return fallback(*args, **kwargs)
        return fallback

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_at = 0.0
        self._half_open_tries = 0


def with_retry(
    max_attempts: int = 3,
    base_delay_seconds: float = 0.3,
    jitter_max: float = 0.5,
    timeout_seconds: float | None = None,
):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                if timeout_seconds is not None:
                    import signal
                    def _timeout_handler(*_):
                        raise TimeoutError(f"Operation timed out after {timeout_seconds}s")
                    try:
                        signal.signal(signal.SIGALRM, _timeout_handler)
                        signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
                    except (ValueError, OSError):
                        pass
                try:
                    result = fn(*args, **kwargs)
                    if timeout_seconds is not None:
                        try:
                            signal.setitimer(signal.ITIMER_REAL, 0)
                        except (ValueError, OSError):
                            pass
                    return result
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = base_delay_seconds * (2 ** (attempt - 1)) + random.uniform(0, jitter_max)
                        logger.debug("Retry %d/%d after %.2fs: %s", attempt, max_attempts, delay, exc)
                        time.sleep(delay)
                    else:
                        logger.warning("All %d retries exhausted: %s", max_attempts, exc)
            if timeout_seconds is not None:
                try:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                except (ValueError, OSError):
                    pass
            raise last_exc
        return wrapper
    return decorator
