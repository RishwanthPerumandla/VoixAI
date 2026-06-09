from agent import (
    OrderState,
    build_confirmation_summary,
    calculate_order_total,
    create_mock_order,
    summarize_order_state,
)


def test_summarize_order_state_with_details() -> None:
    order = OrderState(
        pickup_or_delivery="pickup",
        items=["wings", "fries"],
        flavor="lemon pepper",
        classic_or_boneless="boneless",
        drink="lemonade",
        pickup_time="six thirty",
        confirmed=False,
    )

    summary = summarize_order_state(order)

    assert "pickup order" in summary
    assert "wings, fries" in summary
    assert "flavor: lemon pepper" in summary
    assert "style: boneless" in summary
    assert "drink: lemonade" in summary
    assert "pickup time: six thirty" in summary
    assert "not confirmed" in summary


def test_summarize_order_state_empty() -> None:
    assert summarize_order_state(OrderState()) == "No order details yet."


def test_calculate_order_total_uses_mock_menu() -> None:
    order = OrderState(
        items=["wings", "fries"],
        drink="soda",
    )

    total = calculate_order_total(order)

    assert str(total) == "17.97"


def test_build_confirmation_summary_includes_total() -> None:
    order = OrderState(
        pickup_or_delivery="pickup",
        items=["burger"],
        drink="lemonade",
    )

    summary = build_confirmation_summary(order)

    assert "Current order:" in summary
    assert "Demo total: $11.98." in summary
    assert "Should I place this mock order?" in summary


def test_create_mock_order_generates_expected_shape() -> None:
    order = OrderState(
        pickup_or_delivery="delivery",
        items=["salad"],
        confirmed=True,
    )

    mock_order = create_mock_order(order)

    assert mock_order.order_number.startswith("VX-")
    assert len(mock_order.order_number) == 7
    assert mock_order.total == "$7.99"
    assert "delivery order" in mock_order.summary
