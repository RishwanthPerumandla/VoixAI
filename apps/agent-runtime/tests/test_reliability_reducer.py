from voix_ordering import (
    INTENT_CANCEL_ORDER,
    INTENT_REPLACE_ITEM,
    INTENT_RESTART_ORDER,
    OrderIntent,
    OrderLineItem,
    OrderState,
    apply_order_intent,
    replay_order_intents,
)


def test_reducer_replaces_item_and_removes_invalid_modifiers() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=1,
                selected_flavor_ids=["lemon_pepper"],
                selected_modifier_ids=["all_flats", "well_done"],
            )
        ],
        order_type="pickup",
    )

    result = apply_order_intent(
        order,
        OrderIntent(
            name=INTENT_REPLACE_ITEM,
            target_line_id="line-1",
            replacement_item_id="boneless_10",
        ),
    )

    assert result.order.items[0].item_id == "boneless_10"
    assert result.order.items[0].selected_modifier_ids == ["well_done"]
    assert any(event.type == "invalid_modifier_removed" for event in result.events)


def test_reducer_cancel_order_sets_cancelled_status() -> None:
    order = OrderState(
        items=[OrderLineItem(line_id="line-1", item_id="classic_6", quantity=1)],
        order_type="pickup",
    )

    result = apply_order_intent(order, OrderIntent(name=INTENT_CANCEL_ORDER))

    assert result.order.status == "cancelled"
    assert result.order.items == []
    assert result.order.metrics.cancellation_count == 1


def test_replay_support_preserves_archived_orders_on_restart() -> None:
    replay = replay_order_intents(
        [
            OrderIntent(
                name="add_item",
                replacement_item_id="classic_10",
                quantity=1,
                flavor_ids=("lemon_pepper",),
            ),
            OrderIntent(name=INTENT_RESTART_ORDER),
            OrderIntent(
                name="add_item",
                replacement_item_id="chicken_sandwich",
                quantity=1,
                flavor_ids=("plain",),
            ),
        ],
        order=OrderState(order_type="pickup", customer_name="Rishi"),
    )

    assert [line.item_id for line in replay.order.items] == ["chicken_sandwich"]
    assert len(replay.order.archived_orders) == 1
