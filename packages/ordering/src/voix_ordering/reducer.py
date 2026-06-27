"""Reducer that owns reliable order mutation and event emission."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field

from .intents import (
    INTENT_ADD_ITEM,
    INTENT_CANCEL_ORDER,
    INTENT_CHANGE_FLAVOR,
    INTENT_CHANGE_QUANTITY,
    INTENT_COMPLAINT,
    INTENT_CONFIRM_ORDER,
    INTENT_HANDOFF_REQUEST,
    INTENT_MODIFY_ITEM,
    INTENT_REMOVE_ITEM,
    INTENT_REPLACE_ITEM,
    INTENT_RESTART_ORDER,
    INTENT_UNKNOWN,
    OrderIntent,
)
from .menu import (
    MENU_ITEMS,
    MODIFIER_GROUPS,
    OPTION_TO_GROUP_IDS,
    _normalize_lookup_key,
    get_item_type,
    get_item_template,
    get_combo_template,
    get_group_pack_template,
    _get_max_flavors,
)
from .models import OrderEvent, OrderLineItem, OrderState
from .serialization import serialize_order_state
from .state_machine import OrderPhase, OrderStateMachine
from .validation import validate_order

MAX_RECORDED_EVENTS = 50


@dataclass
class ReducerResult:
    order: OrderState
    events: list[OrderEvent] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    clarification_question: str | None = None
    applied: bool = True


def _event(event_type: str, detail: str, **data: object) -> OrderEvent:
    return OrderEvent(type=event_type, detail=detail, data=data)


def _append_events(order: OrderState, events: list[OrderEvent]) -> None:
    if not events:
        return
    order.recent_events.extend(events)
    if len(order.recent_events) > MAX_RECORDED_EVENTS:
        order.recent_events = order.recent_events[-MAX_RECORDED_EVENTS:]


def _modifier_allowed_for_item(item_id: str, modifier_id: str) -> bool:
    menu_item = MENU_ITEMS[item_id]
    allowed_groups = set(menu_item.required_modifier_group_ids) | set(
        menu_item.optional_modifier_group_ids
    )
    modifier_group_ids = OPTION_TO_GROUP_IDS.get(modifier_id, set())
    return not modifier_group_ids.isdisjoint(allowed_groups)


def _prune_invalid_modifiers(line: OrderLineItem) -> list[str]:
    removed: list[str] = []
    kept: list[str] = []
    for modifier_id in line.selected_modifier_ids:
        if _modifier_allowed_for_item(line.item_id, modifier_id):
            kept.append(modifier_id)
        else:
            removed.append(modifier_id)
    line.selected_modifier_ids = kept
    return removed


def _find_target_line(order: OrderState, intent: OrderIntent) -> OrderLineItem | None:
    if intent.target_line_id:
        for line in order.items:
            if line.line_id == intent.target_line_id:
                return line

    if intent.target_item_id:
        for line in reversed(order.items):
            if line.item_id == intent.target_item_id:
                return line

    if intent.target_item:
        normalized_target = _normalize_lookup_key(intent.target_item)
        matches: list[OrderLineItem] = []
        for line in order.items:
            menu_item = MENU_ITEMS[line.item_id]
            candidates = {
                _normalize_lookup_key(menu_item.display_name),
                _normalize_lookup_key(menu_item.category),
                _normalize_lookup_key(menu_item.item_kind),
                _normalize_lookup_key(menu_item.order_style or ""),
            }
            if normalized_target in candidates:
                matches.append(line)
                continue
            if normalized_target in {"wings", "wing"} and "wing" in _normalize_lookup_key(
                menu_item.display_name
            ):
                matches.append(line)
            if normalized_target in {"fries", "fry"} and "fries" in _normalize_lookup_key(
                menu_item.display_name
            ):
                matches.append(line)
            if normalized_target in {"dip", "dips", "ranch"} and menu_item.item_kind == "dip":
                matches.append(line)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return None

    if len(order.items) == 1:
        return order.items[0]
    return order.items[-1] if order.items and not intent.target_item else None


def _clarify(
    order: OrderState,
    question: str,
    *,
    event_type: str = "clarification_required",
    preserve_status: bool = False,
) -> ReducerResult:
    machine = OrderStateMachine(order)
    order.last_clarification_question = question
    order.metrics.clarification_count += 1
    if not preserve_status:
        machine.reset_to_collecting()
    events = [_event(event_type, question)]
    _append_events(order, events)
    return ReducerResult(
        order=order,
        events=events,
        validation_errors=list(order.last_validation_errors),
        clarification_question=question,
        applied=False,
    )


def _clear_for_restart(order: OrderState) -> None:
    preserved_language = order.language
    preserved_archives = list(order.archived_orders)
    preserved_metrics = copy.deepcopy(order.metrics)
    order.items = []
    order.modifiers = []
    order.quantity = 1
    order.order_type = "pickup"
    order.customer_name = ""
    order.phone = ""
    order.notes = ""
    order.status = OrderPhase.IDLE.value
    order.confirmed = False
    order.pickup_time = None
    order.language = preserved_language
    order.total_shown = False
    order.recap_readback = False
    order.pos_validation_passed = False
    order.last_validation_errors = []
    order.last_clarification_question = None
    order.recent_events = []
    order.archived_orders = preserved_archives
    order.metrics = preserved_metrics


def apply_order_intent(order: OrderState, intent: OrderIntent) -> ReducerResult:
    machine = OrderStateMachine(order)
    if not intent.requires_clarification and intent.name not in {INTENT_UNKNOWN}:
        order.last_clarification_question = None
    events = [
        _event("intent_detected", intent.name, confidence=intent.confidence),
        _event("order_state_before", "Order state before reducer mutation", snapshot=serialize_order_state(order, include_history=False)),
    ]

    if intent.requires_clarification and intent.clarification_question:
        _append_events(order, events)
        result = _clarify(order, intent.clarification_question)
        result.events = events + result.events
        _append_events(order, result.events[len(events):])
        return result

    immutable_block = machine.phase == OrderPhase.COMPLETED and intent.name not in {
        INTENT_RESTART_ORDER,
        INTENT_HANDOFF_REQUEST,
    }
    if immutable_block:
        if intent.name == INTENT_CONFIRM_ORDER:
            order.metrics.duplicate_confirmation_prevented += 1
        _append_events(order, events)
        result = _clarify(
            order,
            "That order is already completed. Say start over if you want to make a new order.",
            preserve_status=True,
        )
        result.events = events + result.events
        return result

    if intent.name == INTENT_UNKNOWN:
        order.metrics.unknown_item_count += 1
        _append_events(order, events)
        result = _clarify(
            order,
            intent.clarification_question or "I want to make sure I got that right. What would you like to change?",
        )
        machine.mark_collecting()
        result.events = events + result.events
        return result

    if intent.name in {INTENT_HANDOFF_REQUEST, INTENT_COMPLAINT}:
        order.metrics.handoff_required_count += 1
        machine.mark_handoff_required()
        events.append(_event("handoff_required", "Customer requested a human handoff."))
        events.append(_event("order_state_after", "Order state after reducer mutation", snapshot=serialize_order_state(order, include_history=False)))
        _append_events(order, events)
        return ReducerResult(order=order, events=events, validation_errors=[])

    if intent.name == INTENT_CANCEL_ORDER:
        order.items = []
        order.quantity = 1
        order.confirmed = False
        order.total_shown = False
        order.recap_readback = False
        order.pos_validation_passed = False
        order.last_validation_errors = []
        order.metrics.cancellation_count += 1
        machine.mark_cancelled()
        events.append(_event("order_cancelled", "Entire order cancelled."))
        events.append(_event("order_state_after", "Order state after reducer mutation", snapshot=serialize_order_state(order, include_history=False)))
        _append_events(order, events)
        return ReducerResult(order=order, events=events, validation_errors=[])

    if intent.name == INTENT_RESTART_ORDER:
        if order.items or order.customer_name:
            order.archived_orders.append(serialize_order_state(copy.deepcopy(order)))
        _clear_for_restart(order)
        machine.reset_to_collecting()
        events.append(_event("order_restarted", "Order restarted from a fresh state.", archived_count=len(order.archived_orders)))
        events.append(_event("order_state_after", "Order state after reducer mutation", snapshot=serialize_order_state(order, include_history=False)))
        _append_events(order, events)
        return ReducerResult(order=order, events=events, validation_errors=[])

    if intent.name == INTENT_ADD_ITEM:
        if not intent.replacement_item_id:
            _append_events(order, events)
            result = _clarify(order, "Which item would you like to add?")
            result.events = events + result.events
            return result

        # Dedup: if a line with the same item_id already exists, merge into it
        # instead of creating a duplicate. This prevents the agent from
        # accidentally adding the same combo/wings item twice.
        existing_line = None
        for existing in order.items:
            if existing.item_id == intent.replacement_item_id:
                existing_line = existing
                break

        if existing_line is not None:
            existing_line.quantity = max(1, intent.quantity or existing_line.quantity)
            if intent.flavor_ids:
                existing_line.selected_flavor_ids = list(intent.flavor_ids)
            merged_modifiers = list(existing_line.selected_modifier_ids)
            for modifier_id in intent.add_modifier_ids:
                if modifier_id not in merged_modifiers:
                    merged_modifiers.append(modifier_id)
            existing_line.selected_modifier_ids = merged_modifiers
            if intent.notes:
                existing_line.notes = intent.notes
            removed_modifiers = _prune_invalid_modifiers(existing_line)
            order.quantity = sum(l.quantity for l in order.items)
            machine.reset_to_collecting()
            events.append(_event("item_merged", "Merged into existing item instead of duplicating.", item_id=existing_line.item_id, line_id=existing_line.line_id))
            for modifier_id in removed_modifiers:
                events.append(
                    _event("invalid_modifier_removed", "Removed modifier that was invalid.", modifier_id=modifier_id, line_id=existing_line.line_id)
                )
            if removed_modifiers:
                order.metrics.correction_count += 1
        else:
            line = OrderLineItem(
                line_id=intent.target_line_id or f"line-{len(order.items) + 1}",
                item_id=intent.replacement_item_id,
                quantity=max(1, intent.quantity or 1),
                selected_flavor_ids=list(intent.flavor_ids),
                selected_modifier_ids=list(intent.add_modifier_ids),
                notes=intent.notes or "",
            )
            removed_modifiers = _prune_invalid_modifiers(line)
            order.items.append(line)
            order.quantity = sum(existing_line.quantity for existing_line in order.items)
            machine.reset_to_collecting()
            events.append(_event("item_added", "Item added to order.", item_id=line.item_id, line_id=line.line_id))
            for modifier_id in removed_modifiers:
                events.append(
                    _event(
                        "invalid_modifier_removed",
                        "Removed modifier that was invalid for the selected item.",
                        modifier_id=modifier_id,
                        line_id=line.line_id,
                    )
                )
            if removed_modifiers:
                order.metrics.correction_count += 1
    else:
        target_line = _find_target_line(order, intent)
        if target_line is None:
            _append_events(order, events)
            result = _clarify(
                order,
                intent.clarification_question
                or "Which item did you mean? I have more than one item on the order.",
            )
            result.events = events + result.events
            return result

        if intent.name == INTENT_REMOVE_ITEM:
            order.items = [line for line in order.items if line.line_id != target_line.line_id]
            order.quantity = sum(existing_line.quantity for existing_line in order.items) or 1
            order.metrics.cancellation_count += 1
            machine.reset_to_collecting()
            events.append(
                _event("item_removed", "Item removed from order.", item_id=target_line.item_id, line_id=target_line.line_id)
            )
        elif intent.name == INTENT_REPLACE_ITEM:
            if not intent.replacement_item_id:
                _append_events(order, events)
                result = _clarify(order, "What should I change that item to?")
                result.events = events + result.events
                return result
            old_item_id = target_line.item_id
            new_item_id = intent.replacement_item_id
            old_type = get_item_type(old_item_id)
            new_type = get_item_type(new_item_id)

            # Safe replacement: preserve valid fields, remove invalid ones
            target_line.item_id = new_item_id
            if intent.quantity is not None:
                target_line.quantity = max(1, intent.quantity)
            if intent.flavor_ids:
                target_line.selected_flavor_ids = list(intent.flavor_ids)
            if intent.notes is not None:
                target_line.notes = intent.notes

            # Check flavor count against new max
            new_max_flavors = _get_max_flavors(new_item_id)
            if new_max_flavors > 0 and len(target_line.selected_flavor_ids) > new_max_flavors:
                target_line.selected_flavor_ids = target_line.selected_flavor_ids[:new_max_flavors]
                events.append(
                    _event(
                        "flavor_limit_adjusted",
                        f"Reduced flavors to fit {new_max_flavors} max for new item.",
                        old_count=len(target_line.selected_flavor_ids),
                        new_count=new_max_flavors,
                        line_id=target_line.line_id,
                    )
                )

            removed_modifiers = _prune_invalid_modifiers(target_line)

            # Classic <-> Boneless: handle piece_preference
            if old_type == "classic_wings" and new_type == "boneless_wings":
                piece_mods = [m for m in target_line.selected_modifier_ids
                              if "piece_preference" in OPTION_TO_GROUP_IDS.get(m, set())]
                for pm in piece_mods:
                    target_line.selected_modifier_ids.remove(pm)
                    if pm not in removed_modifiers:
                        removed_modifiers.append(pm)
                events.append(
                    _event(
                        "invalid_modifier_removed",
                        "Piece preference (all flats/all drums) is not available for boneless wings.",
                        modifier_id="piece_preference",
                        line_id=target_line.line_id,
                    )
                )

            if old_type == "boneless_wings" and new_type == "classic_wings":
                events.append(
                    _event(
                        "piece_preference_allowed",
                        "Piece preference is now available for classic bone-in wings.",
                        line_id=target_line.line_id,
                    )
                )

            # Combo type change: preserve valid side/drink/dip
            if old_type == new_type and old_type == "combo":
                pass  # same combo type, preserve everything valid

            machine.reset_to_collecting()
            order.metrics.correction_count += 1
            events.append(
                _event("item_replaced", "Item replaced on order.", item_id=target_line.item_id, line_id=target_line.line_id, old_item_id=old_item_id)
            )
            for modifier_id in removed_modifiers:
                events.append(
                    _event(
                        "invalid_modifier_removed",
                        "Removed modifier that no longer applies after item replacement.",
                        modifier_id=modifier_id,
                        line_id=target_line.line_id,
                    )
                )
        else:
            if intent.name == INTENT_CHANGE_QUANTITY and intent.quantity is not None:
                target_line.quantity = max(1, intent.quantity)
                # If piece count changed, recompute max_flavors and trim
                new_max_flavors = _get_max_flavors(target_line.item_id)
                if new_max_flavors > 0 and len(target_line.selected_flavor_ids) > new_max_flavors:
                    target_line.selected_flavor_ids = target_line.selected_flavor_ids[:new_max_flavors]
                    events.append(
                        _event(
                            "flavor_limit_adjusted",
                            f"Reduced flavors to fit {new_max_flavors} max for this size.",
                            old_count=len(target_line.selected_flavor_ids),
                            new_count=new_max_flavors,
                            line_id=target_line.line_id,
                        )
                    )
                order.metrics.correction_count += 1
            if intent.name in {INTENT_CHANGE_FLAVOR, INTENT_MODIFY_ITEM} and intent.flavor_ids:
                target_line.selected_flavor_ids = list(intent.flavor_ids)
                order.metrics.correction_count += 1
            if intent.add_modifier_ids:
                for modifier_id in intent.add_modifier_ids:
                    if modifier_id not in target_line.selected_modifier_ids:
                        # Auto-replace when adding to a group already at capacity.
                        for group_id in OPTION_TO_GROUP_IDS.get(modifier_id, set()):
                            group = MODIFIER_GROUPS.get(group_id)
                            if group is not None and group.max_selections > 0:
                                existing = [
                                    m for m in target_line.selected_modifier_ids
                                    if group_id in OPTION_TO_GROUP_IDS.get(m, set())
                                ]
                                while len(existing) >= group.max_selections:
                                    removed = existing.pop(0)
                                    target_line.selected_modifier_ids.remove(removed)
                                    events.append(
                                        _event(
                                            "modifier_replaced",
                                            f"Replaced {removed} with {modifier_id} in {group_id}.",
                                            modifier_id=modifier_id,
                                            replaced_id=removed,
                                            line_id=target_line.line_id,
                                        )
                                    )
                        target_line.selected_modifier_ids.append(modifier_id)
                        events.append(
                            _event("modifier_added", "Modifier added to item.", modifier_id=modifier_id, line_id=target_line.line_id)
                        )
            if intent.remove_modifier_ids:
                kept_modifiers: list[str] = []
                for modifier_id in target_line.selected_modifier_ids:
                    if modifier_id in intent.remove_modifier_ids:
                        events.append(
                            _event("modifier_removed", "Modifier removed from item.", modifier_id=modifier_id, line_id=target_line.line_id)
                        )
                        order.metrics.correction_count += 1
                        continue
                    kept_modifiers.append(modifier_id)
                target_line.selected_modifier_ids = kept_modifiers
            if intent.notes is not None:
                target_line.notes = intent.notes
            if intent.quantity is not None and intent.name == INTENT_MODIFY_ITEM:
                target_line.quantity = max(1, intent.quantity)
                order.metrics.correction_count += 1
            removed_modifiers = _prune_invalid_modifiers(target_line)
            if removed_modifiers:
                order.metrics.correction_count += 1
                for modifier_id in removed_modifiers:
                    events.append(
                        _event(
                            "invalid_modifier_removed",
                            "Removed modifier that is invalid for the item.",
                            modifier_id=modifier_id,
                            line_id=target_line.line_id,
                        )
                    )
            machine.reset_to_collecting()

        order.quantity = sum(existing_line.quantity for existing_line in order.items) or 1

    machine.start_validation()
    validation_errors = validate_order(order)
    machine.apply_validation(validation_errors)
    if intent.name == INTENT_REMOVE_ITEM and not order.items:
        machine.mark_collecting()
    if validation_errors:
        order.metrics.validation_failure_count += 1
        events.append(_event("validation_failed", "Validation failed after reducer mutation.", errors=list(validation_errors)))
    else:
        events.append(_event("validation_passed", "Validation passed after reducer mutation."))

    events.append(_event("order_state_after", "Order state after reducer mutation", snapshot=serialize_order_state(order, include_history=False)))
    _append_events(order, events)
    return ReducerResult(order=order, events=events, validation_errors=validation_errors)
