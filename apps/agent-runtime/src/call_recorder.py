"""Best-effort call telemetry recording for the dashboard.

The agent runtime opens a call record when a session starts and finalizes it on
shutdown (duration, transcript, outcome, sentiment, linked order). Every call to
the API is fire-and-forget and fully guarded: telemetry must never be able to
break or slow down a live voice session, so failures are logged and swallowed.

HTTP uses the stdlib ``urllib`` in a worker thread to avoid adding a dependency
to the runtime image.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("agent.call_recorder")

# The dashboard API. Defaults to the local API service; override in deployment.
API_BASE_URL = (
    os.getenv("VOIXAI_API_URL")
    or os.getenv("NEXT_PUBLIC_API_BASE_URL")
    or "http://127.0.0.1:8000"
).rstrip("/")

_HTTP_TIMEOUT = 4.0

_POSITIVE_WORDS = {
    "thanks",
    "thank",
    "great",
    "perfect",
    "awesome",
    "good",
    "yes",
    "please",
    "appreciate",
    "love",
    "sounds good",
    "correct",
}
_NEGATIVE_WORDS = {
    "no",
    "wrong",
    "bad",
    "terrible",
    "cancel",
    "frustrated",
    "angry",
    "annoyed",
    "hate",
    "stupid",
    "useless",
    "not working",
    "never",
}


def estimate_sentiment(transcript: list[dict[str, Any]]) -> float:
    """A cheap, deterministic sentiment estimate (0=negative .. 1=positive).

    This is intentionally lightweight keyword scoring over the customer's turns.
    Swap for a model-based score later behind this same signature.
    """
    score = 0
    counted = 0
    for turn in transcript:
        if turn.get("role") != "user":
            continue
        text = str(turn.get("text", "")).lower()
        if not text.strip():
            continue
        counted += 1
        if any(word in text for word in _POSITIVE_WORDS):
            score += 1
        if any(word in text for word in _NEGATIVE_WORDS):
            score -= 1
    if counted == 0:
        return 0.6  # neutral-leaning default when there's nothing to judge
    # Map the average [-1, 1] signal into [0, 1], anchored at a friendly 0.6.
    normalized = 0.6 + (score / counted) * 0.4
    return max(0.0, min(1.0, round(normalized, 3)))


def _post_json(path: str, payload: dict[str, Any], *, method: str = "POST") -> None:
    url = f"{API_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        logger.warning("Call telemetry %s %s failed: HTTP %s", method, path, exc.code)
    except Exception as exc:  # noqa: BLE001 - telemetry is strictly best-effort
        logger.warning("Call telemetry %s %s failed: %s", method, path, exc)


def open_call(
    *,
    call_id: str,
    room_name: str,
    scenario: str,
    channel: str,
    voice_provider: str,
    llm_model: str,
    language: str,
    started_at: float,
) -> None:
    """Synchronous; call via ``asyncio.to_thread`` from the runtime."""
    _post_json(
        "/api/calls",
        {
            "call_id": call_id,
            "room_name": room_name,
            "scenario": scenario,
            "channel": channel,
            "voice_provider": voice_provider,
            "llm_model": llm_model,
            "language": language,
            "started_at": started_at,
        },
    )


def finalize_call(
    *,
    call_id: str,
    started_at: float,
    transcript: list[dict[str, Any]],
    turn_count: int,
    order_number: str | None,
    order_total: str | None,
    guardrail_violations: int,
    language: str,
    error: str | None = None,
) -> None:
    """Synchronous; call via ``asyncio.to_thread`` from the runtime."""
    ended_at = time.time()
    if error:
        status, outcome = "failed", "abandoned"
    elif order_number:
        status, outcome = "completed", "order_placed"
    elif turn_count == 0:
        status, outcome = "completed", "abandoned"
    else:
        status, outcome = "completed", "info_only"

    _post_json(
        f"/api/calls/{call_id}",
        {
            "status": status,
            "outcome": outcome,
            "ended_at": ended_at,
            "duration_seconds": round(ended_at - started_at, 1),
            "turn_count": turn_count,
            "sentiment": estimate_sentiment(transcript),
            "language": language,
            "order_number": order_number,
            "guardrail_violations": guardrail_violations,
            "error": error,
            "transcript": transcript,
        },
        method="PATCH",
    )
