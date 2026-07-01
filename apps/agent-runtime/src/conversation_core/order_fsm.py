"""ORDER sub-FSM — drives the ordering flow behind the ORDER node.

This is the "hard part" from the brief. It implements the ordering conversation
as an explicit state machine:

    SELECT_ITEM -> CONFIGURE_ITEM -> ADD_SIDES -> ADD_DRINKS
               -> REVIEW -> CONFIRM(gate) -> PLACE

Each state knows which slots are required vs filled for the current item, and
never re-asks a filled slot. The LLM supplies intent+slots; the machine enforces
ordering and drives what to ask next.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .state_machine import ConversationContext, NodeName, StateAction


class OrderSubNode(str, Enum):
    SELECT_ITEM = "SELECT_ITEM"
    CONFIGURE_ITEM = "CONFIGURE_ITEM"
    ADD_SIDES = "ADD_SIDES"
    ADD_DRINKS = "ADD_DRINKS"
    REVIEW = "REVIEW"
    CONFIRM = "CONFIRM"
    PLACE = "PLACE"


# ── Slot helpers — inspect an OrderState + specific line for missing slots ──


def _has_flavor(line: Any) -> bool:
    return bool(getattr(line, "selected_flavor_ids", []))


def _modifier_ids(line: Any) -> list[str]:
    return list(getattr(line, "selected_modifier_ids", []))


def _has_group_modifier(line: Any, group_name: str) -> bool:
    try:
        from voix_ordering.menu import MODIFIER_GROUPS, _selected_by_group
    except ImportError:
        return True
    for gid, g in MODIFIER_GROUPS.items():
        if g.display_name.lower() == group_name.lower():
            return bool(_selected_by_group(line, gid))
    return False


def _has_side(line: Any) -> bool:
    try:
        from voix_ordering.menu import OPTION_TO_GROUP_IDS
        return any(
            "combo_side" in (OPTION_TO_GROUP_IDS.get(mid, set()) or set())
            or "side" in (mid or "").lower()
            for mid in _modifier_ids(line)
        )
    except ImportError:
        return False


def _has_drink(line: Any) -> bool:
    try:
        from voix_ordering.menu import OPTION_TO_GROUP_IDS
        return any(
            "combo_drink" in (OPTION_TO_GROUP_IDS.get(mid, set()) or set())
            or "drink" in (mid or "").lower()
            for mid in _modifier_ids(line)
        )
    except ImportError:
        return False


def _is_combo(item_id: str) -> bool:
    return "combo" in (item_id or "").lower()


def _has_well_done(line: Any) -> bool:
    return "well_done" in _modifier_ids(line)


def _has_dip(line: Any) -> bool:
    try:
        from voix_ordering.menu import OPTION_TO_GROUP_IDS
        return any(
            "dip" in (OPTION_TO_GROUP_IDS.get(mid, set()) or set())
            for mid in _modifier_ids(line)
        )
    except ImportError:
        return False


def _item_name(item_id: str) -> str:
    try:
        from voix_ordering.menu import MENU_ITEMS
        return MENU_ITEMS[item_id].display_name if item_id in MENU_ITEMS else item_id
    except ImportError:
        return item_id


def _missing_slots_text(order: Any, line_index: int) -> str | None:
    """Return a human-readable prompt for the *first* missing required slot on
    the given line, or None if all required slots are filled."""
    order_items = getattr(order, "items", [])
    if line_index >= len(order_items):
        return None
    line = order_items[line_index]
    item_id = getattr(line, "item_id", "")

    # Check required modifier groups from the menu item
    try:
        from voix_ordering.menu import MENU_ITEMS, MODIFIER_GROUPS, _selected_by_group
    except ImportError:
        return None

    menu_item = MENU_ITEMS.get(item_id)
    if menu_item is None:
        return "What item did you want?"

    # Flavors required?
    if menu_item.requires_flavors and not _has_flavor(line):
        if menu_item.max_flavors and menu_item.max_flavors > 1:
            return "What flavor would you like? You can choose up to " + str(menu_item.max_flavors) + " flavors."
        return "What flavor would you like?"

    # Combo required groups (side, drink)
    for group_id in menu_item.required_modifier_group_ids:
        group = MODIFIER_GROUPS.get(group_id)
        if group is None:
            continue
        selected = _selected_by_group(line, group_id)
        if not selected:
            if "side" in group_id.lower():
                options = [o.name for o in group.options]
                return "What side would you like? Options: " + ", ".join(options) + "."
            elif "drink" in group_id.lower():
                options = [o.name for o in group.options]
                return "What drink would you like? Options: " + ", ".join(options) + "."
            return group.name + " is required. What would you like?"

    # All required slots filled
    return None


def _all_order_slots_filled(order: Any) -> list[str]:
    """Return a list of missing-slot prompts for all lines in the order.
    Empty list means every line has all required slots."""
    missing: list[str] = []
    order_items = getattr(order, "items", [])
    for i in range(len(order_items)):
        slot = _missing_slots_text(order, i)
        if slot:
            missing.append(slot)
    return missing


def _build_readback(order: Any) -> str:
    """Build a human-readable order summary for the REVIEW state."""
    try:
        from voix_ordering.menu import MENU_ITEMS
        from voix_ordering.pricing import build_price_quote
        from voix_ordering.serialization import summarize_order_state
    except ImportError:
        return ""
    try:
        quote = build_price_quote(order)
    except Exception:
        quote = None
    summary = summarize_order_state(order)
    if quote:
        return f"Here is your order so far: {summary}. Total is {quote.total}, tax {quote.tax}. Should I place it?"
    return f"Here is your order so far: {summary}. Should I place it?"


# ── OrderSubFSM ────────────────────────────────────────────────────────────


@dataclass
class OrderContext:
    """Mutable state tracked within the ORDER sub-FSM."""
    line_index: int = 0                          # which line we are configuring
    waiting_for_next_item: bool = True           # SELECT_ITEM active
    multiple_items_loop: bool = False             # user said "also"/"and another" for more items
    review_read: bool = False                     # REVIEW message already spoken
    confirm_pending: bool = False                 # awaiting explicit yes in CONFIRM
    placed: bool = False                          # PLACE executed
    cancelled: bool = False                       # mid-order cancellation fired
    last_asked: str | None = None                 # deduplicate "what would you like"


class OrderSubFSM:
    """Deterministic conversation FSM for the ordering flow.

    One instance per ORDER session (lives on ConversationContext). The top-level
    FSM delegates to this when the user is in the ORDER node.
    """

    def __init__(self, context: ConversationContext) -> None:
        self._state = OrderSubNode.SELECT_ITEM
        self._ctx = OrderContext()
        self._context = context

    @property
    def state(self) -> OrderSubNode:
        return self._state

    def handle_turn(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """Route a user turn through the sub-FSM.

        *order* is the mutable OrderState from the session. The method inspects
        it to determine filled vs missing slots and returns a StateAction with
        the next message.
        """
        normalized = re.sub(r"\s+", " ", text.strip().lower())

        # ── Detect mid-order cancellation — any state → back to ROUTE ──
        if self._is_cancel_request(normalized):
            self._ctx.cancelled = True
            context.current_node = NodeName.ROUTE
            self._state = OrderSubNode.SELECT_ITEM
            return StateAction(
                NodeName.ORDER,
                "OK, no problem. Is there anything else I can help you with?",
                ({"type": "order_cancelled_mid_order", "sub_node": self._state.value},),
                router_result=None,
            )

        # ── Route by current sub-state ──
        dispatch = {
            OrderSubNode.SELECT_ITEM: self._on_select_item,
            OrderSubNode.CONFIGURE_ITEM: self._on_configure_item,
            OrderSubNode.ADD_SIDES: self._on_add_sides,
            OrderSubNode.ADD_DRINKS: self._on_add_drinks,
            OrderSubNode.REVIEW: self._on_review,
            OrderSubNode.CONFIRM: self._on_confirm,
            OrderSubNode.PLACE: self._on_place,
        }
        handler = dispatch.get(self._state, self._on_select_item)
        return handler(context, order, normalized)

    def reset(self) -> None:
        self._state = OrderSubNode.SELECT_ITEM
        self._ctx = OrderContext()

    # ── Intent detection within the sub-FSM ──

    @staticmethod
    def _is_cancel_request(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "cancel everything",
                "cancel the order",
                "cancel my order",
                "never mind",
                "forget it",
                "cancela todo",
                "olvida",
                "actually cancel",
                "just cancel",
                "start over",
                "restart",
            )
        )

    @staticmethod
    def _is_affirmative(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "yes",
                "yes please",
                "yeah",
                "sure",
                "correct",
                "that's right",
                "si",
                "si por favor",
                "place it",
                "place the order",
                "go ahead",
                "confirm",
            )
        )

    @staticmethod
    def _is_negative(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "no",
                "not yet",
                "hold on",
                "wait",
                "actually no",
                "no, don't",
                "no, wait",
            )
        )

    @staticmethod
    def _is_correction(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "actually",
                "make that",
                "change ",
                "instead",
                "switch",
                "make it",
                "correction",
                "no, i said",
                "i meant",
                "mejor",
                "hazlas",
            )
        )

    @staticmethod
    def _is_add_another(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "also",
                "and",
                "plus",
                "add another",
                "also want",
                "one more",
                "another",
                "tambien",
                "ademas",
            )
        )

    # ── State handlers ──

    def _on_select_item(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """SELECT_ITEM: user told us what they want. Move to CONFIGURE_ITEM."""
        if not getattr(order, "items", []):
            return StateAction(
                NodeName.ORDER,
                "What would you like to order today?",
                ({"type": "order_ask_item", "sub_node": self._state.value},),
                router_result=None,
            )
        self._state = OrderSubNode.CONFIGURE_ITEM
        return self._advance_to_next_missing_slot(order)

    def _on_configure_item(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """CONFIGURE_ITEM: check what's missing on the current line and ask."""
        # If all slots are already filled and we are waiting for "anything else?",
        # detect "no" / "that's it" → transition to REVIEW.
        order_items = getattr(order, "items", [])
        if self._ctx.waiting_for_next_item and self._is_negative(text):
            self._ctx.waiting_for_next_item = False
            self._state = OrderSubNode.REVIEW
            return self._on_review(context, order, text)

        missing = _all_order_slots_filled(order)
        if missing:
            return StateAction(
                NodeName.ORDER,
                missing[0],
                ({"type": "order_ask_slot", "sub_node": self._state.value},),
                router_result=None,
            )

        # Check if current line is a combo that needs side/drink
        if self._ctx.line_index < len(order_items):
            line = order_items[self._ctx.line_index]
            if _is_combo(getattr(line, "item_id", "")):
                if not _has_side(line):
                    self._state = OrderSubNode.ADD_SIDES
                    return self._on_add_sides(context, order, text)
                if not _has_drink(line):
                    self._state = OrderSubNode.ADD_DRINKS
                    return self._on_add_drinks(context, order, text)

        # All slots filled for current item. Ask if user wants more items.
        self._ctx.waiting_for_next_item = True
        item_name = _item_name(getattr(order_items[self._ctx.line_index], "item_id", "")) if order_items else "that"
        return StateAction(
            NodeName.ORDER,
            f"Got it, {item_name} added. Would you like anything else?",
            ({"type": "order_item_complete", "sub_node": self._state.value},),
            router_result=None,
        )

    def _on_add_sides(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """ADD_SIDES: the current item needs a combo side."""
        order_items = getattr(order, "items", [])
        if self._ctx.line_index < len(order_items):
            line = order_items[self._ctx.line_index]
            if not _has_side(line):
                return StateAction(
                    NodeName.ORDER,
                    "What side would you like with that combo?",
                    ({"type": "order_ask_side", "sub_node": self._state.value},),
                    router_result=None,
                )
        self._state = OrderSubNode.ADD_DRINKS
        return self._on_add_drinks(context, order, text)

    def _on_add_drinks(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """ADD_DRINKS: the current item needs a combo drink."""
        order_items = getattr(order, "items", [])
        if self._ctx.line_index < len(order_items):
            line = order_items[self._ctx.line_index]
            if not _has_drink(line):
                return StateAction(
                    NodeName.ORDER,
                    "What drink would you like with that combo?",
                    ({"type": "order_ask_drink", "sub_node": self._state.value},),
                    router_result=None,
                )
        self._state = OrderSubNode.REVIEW
        return self._on_review(context, order, text)

    def _on_review(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """REVIEW: read back the order and ask for confirmation."""
        if not self._ctx.review_read:
            self._ctx.review_read = True
            readback = _build_readback(order)
            self._state = OrderSubNode.CONFIRM
            return StateAction(
                NodeName.ORDER,
                readback,
                ({"type": "order_review", "sub_node": self._state.value},),
                router_result=None,
            )
        self._state = OrderSubNode.CONFIRM
        return self._on_confirm(context, order, text)

    def _on_confirm(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """CONFIRM: explicit gate — only PLACE on explicit yes, else loop back."""
        if self._is_affirmative(text):
            self._state = OrderSubNode.PLACE
            return self._on_place(context, order, text)
        if self._is_correction(text) or not self._is_negative(text):
            # User said something ambiguous or a correction — go back to configure
            self._state = OrderSubNode.CONFIGURE_ITEM
            self._ctx.review_read = False
            return self._advance_to_next_missing_slot(order)
        # User said no — back to CONFIGURE_ITEM
        self._state = OrderSubNode.CONFIGURE_ITEM
        self._ctx.review_read = False
        return StateAction(
            NodeName.ORDER,
            "No problem. What would you like to change?",
            ({"type": "order_confirm_negative", "sub_node": self._state.value},),
            router_result=None,
        )

    def _on_place(self, context: ConversationContext, order: Any, text: str) -> StateAction:
        """PLACE: the sub-FSM completes. The caller (top-level FSM) persists the
        order and returns to ROUTE."""
        if self._ctx.placed:
            return StateAction(
                NodeName.ORDER,
                "That order is already placed.",
                ({"type": "order_duplicate_prevented", "sub_node": self._state.value},),
                router_result=None,
            )
        self._ctx.placed = True
        context.current_node = NodeName.ROUTE
        return StateAction(
            NodeName.ROUTE,
            "",
            ({"type": "order_placed", "sub_node": self._state.value},),
            router_result=None,
            requires_response=False,
        )

    # ── Helpers ──

    def _advance_to_next_missing_slot(self, order: Any) -> StateAction:
        """Find the first line with a missing slot and ask for it."""
        missing = _all_order_slots_filled(order)
        if missing:
            self._state = OrderSubNode.CONFIGURE_ITEM
            return StateAction(
                NodeName.ORDER,
                missing[0],
                ({"type": "order_ask_slot", "sub_node": self._state.value},),
                router_result=None,
            )
        self._state = OrderSubNode.REVIEW
        return self._on_review(self._context, order, "")
