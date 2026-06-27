"""HTTP-backed repository for the conversation FSM.

The runtime keeps this thin and best-effort. If the API is unavailable, callers
can fall back to the in-memory repository without affecting the live voice path.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from .state_machine import ConversationContext, NodeName

logger = logging.getLogger("agent.conversation_core")

API_BASE_URL = (
    os.getenv("VOIXAI_API_URL")
    or os.getenv("VOIXAI_API_BASE_URL")
    or "http://127.0.0.1:8000"
).rstrip("/")

_HTTP_TIMEOUT = 1.5


class ApiConversationRepository:
    def __init__(self, *, base_url: str = API_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def get_current_node(self, call_id: str) -> NodeName | None:
        try:
            data = self._request("GET", f"/api/conversation/sessions/{call_id}")
        except Exception as exc:
            logger.debug("Conversation resume lookup failed: %s", exc)
            return None
        node = data.get("current_node")
        try:
            return NodeName(str(node)) if node else None
        except ValueError:
            return None

    def persist_node(self, context: ConversationContext, node: NodeName) -> None:
        try:
            self._request(
                "PATCH",
                f"/api/conversation/sessions/{context.call_id}/node",
                {"room_name": context.room_name, "current_node": node.value},
            )
        except Exception as exc:
            logger.debug("Conversation node persistence failed: %s", exc)

    def identify_customer(self, context: ConversationContext) -> ConversationContext:
        try:
            data = self._request(
                "POST",
                "/api/conversation/identify",
                {
                    "call_id": context.call_id,
                    "room_name": context.room_name,
                    "caller_id": context.caller_id,
                    "phone": context.caller_phone,
                },
            )
        except Exception as exc:
            logger.debug("Conversation identify failed: %s", exc)
            return context

        context.caller_phone = data.get("phone") or context.caller_phone
        context.customer_id = data.get("customer_id") or context.customer_id
        context.customer_name = data.get("name") or context.customer_name
        context.is_returning_customer = bool(data.get("is_returning"))
        context.last_order_code = data.get("last_order_code") or None
        context.last_order_summary = data.get("last_order_summary") or None
        context.name_confirmed = bool(context.customer_name)
        return context

    def persist_customer_name(self, context: ConversationContext, name: str) -> ConversationContext:
        try:
            data = self._request(
                "POST",
                "/api/conversation/name",
                {
                    "call_id": context.call_id,
                    "room_name": context.room_name,
                    "customer_id": context.customer_id,
                    "phone": context.caller_phone,
                    "name": name,
                },
            )
        except Exception as exc:
            logger.debug("Conversation name persistence failed: %s", exc)
            context.customer_name = name
            context.name_confirmed = True
            return context

        context.customer_id = data.get("customer_id") or context.customer_id
        context.caller_phone = data.get("phone") or context.caller_phone
        context.customer_name = data.get("name") or name
        context.name_confirmed = True
        return context

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {body[:200]}") from exc
        return json.loads(raw) if raw else {}
