"""Pluggable handoff interface for manager escalation.

``MockHandoffHandler`` works without telephony (the demo default).
``SipHandoffHandler`` wraps LiveKit's SIP transfer API.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

logger = logging.getLogger("agent.handoff")

HANDOFF_MESSAGE = "I'm sorry about that. I'll connect you with a team member now. Goodbye."
HANDOFF_MESSAGE_NO_NUMBER = (
    "I'm sorry about that. I'll make sure a team member follows up with you shortly. Goodbye."
)


class HandoffHandler(Protocol):
    def handoff(
        self,
        call_id: str,
        reason_code: str,
        *,
        room_name: str = "",
    ) -> str:
        """Execute a handoff. Returns the message to play to the customer."""
        ...


class MockHandoffHandler:
    """Best-effort handoff that plays a TTS message.

    In production this would be swapped for a real SIP transfer.  The handoff
    always succeeds from the handler's perspective.
    """

    def __init__(self, message: str = "") -> None:
        self._message = message or HANDOFF_MESSAGE

    def handoff(
        self,
        call_id: str,
        reason_code: str,
        *,
        room_name: str = "",
    ) -> str:
        return self._message


class SipHandoffHandler:
    """LiveKit SIP warm-transfer handoff.

    Requires ``LIVEKIT_URL`` / ``LIVEKIT_API_KEY`` / ``LIVEKIT_API_SECRET``
    (already present for the agent) plus ``MANAGER_HANDOFF_NUMBER``.
    Falls back to the mock message if the number is unset.
    """

    def __init__(
        self,
        manager_number: str = "",
        fallback_message: str = "",
    ) -> None:
        self._manager_number = manager_number or os.getenv("MANAGER_HANDOFF_NUMBER", "")
        self._fallback_message = fallback_message or HANDOFF_MESSAGE_NO_NUMBER

    def handoff(
        self,
        call_id: str,
        reason_code: str,
        *,
        room_name: str = "",
    ) -> str:
        if not self._manager_number:
            logger.info("MANAGER_HANDOFF_NUMBER unset; falling back to mock handoff for %s", call_id)
            return self._fallback_message

        try:
            self._do_sip_transfer(call_id, room_name)
            return f"I'm transferring you to a manager now. Please hold."
        except Exception:
            logger.exception("SIP handoff failed for %s; using fallback", call_id)
            return self._fallback_message

    def _do_sip_transfer(self, call_id: str, room_name: str) -> None:
        """LiveKit SIP transfer — wrap ``livekit-api`` create_sip_participant."""
        # Lazy import so the module is usable without livekit installed.
        from livekit.api import LiveKitAPI
        from livekit.protocol.sip import CreateSIPParticipantRequest

        api = LiveKitAPI()
        try:
            api.sip.create_sip_participant(
                CreateSIPParticipantRequest(
                    sip_call_to=self._manager_number,
                    room_name=room_name,
                    participant_identity=f"manager-{call_id[:8]}",
                    participant_name="Manager",
                    play_dialtone=True,
                )
            )
        finally:
            pass  # api.aclose() — caller responsibility in async context


def build_handoff_handler() -> HandoffHandler:
    """Factory: returns a ``SipHandoffHandler`` unless ``ENABLE_MOCK_HANDOFF`` is true."""
    if os.getenv("ENABLE_MOCK_HANDOFF", "true").lower() in ("true", "1", "yes"):
        return MockHandoffHandler()
    return SipHandoffHandler()
