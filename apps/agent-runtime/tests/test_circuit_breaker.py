from __future__ import annotations

import time

import pytest

from conversation_core.circuit_breaker import CircuitBreaker, CircuitState


class _FailAfter:
    def __init__(self, n: int) -> None:
        self._n = n
        self._calls = 0

    def __call__(self) -> str:
        self._calls += 1
        if self._calls >= self._n:
            return "ok"
        raise ConnectionError("transient failure")


def test_closed_passes_through() -> None:
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout_seconds=30.0)
    result = cb.call(lambda: "ok")
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30.0)
    fn = _FailAfter(999)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            cb.call(fn)
    assert cb.state == CircuitState.OPEN


def test_fallback_on_failure() -> None:
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30.0)
    result = cb.call(lambda: (_ for _ in ()).throw(ConnectionError("fail")), fallback="fallback_val")
    assert result == "fallback_val"


def test_fallback_on_open() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=30.0)
    with pytest.raises(ConnectionError):
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError("fail")))
    assert cb.state == CircuitState.OPEN
    result = cb.call(lambda: "should_not_run", fallback="open_fallback")
    assert result == "open_fallback"


def test_half_open_recovers() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=0.05, half_open_max_retries=3)
    with pytest.raises(ConnectionError):
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError("fail")))
    assert cb.state == CircuitState.OPEN
    time.sleep(0.06)
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    assert cb.state == CircuitState.CLOSED


def test_reset() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=30.0)
    with pytest.raises(ConnectionError):
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError("fail")))
    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_acall() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=30.0)

    async def _ok() -> str:
        return "ok"

    result = await cb.acall(_ok)
    assert result == "ok"

    async def _fail() -> str:
        raise ConnectionError("async fail")

    with pytest.raises(ConnectionError):
        await cb.acall(_fail)

    assert cb.state == CircuitState.OPEN
    result = await cb.acall(_ok, fallback="async_fallback")
    assert result == "async_fallback"


@pytest.mark.asyncio
async def test_circuit_breaker_forced_failure_uses_fallback_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error
    monkeypatch.setattr("scenarios.wingstop._BACKEND_CIRCUIT_BREAKER_SKIP", True)
    from scenarios.wingstop import _submit_order_via_backend
    from voix_ordering import OrderState

    order = OrderState()
    order.customer_name = "Test"

    with pytest.raises((OSError, urllib.error.URLError, RuntimeError)):
        await _submit_order_via_backend("test-room", order)
