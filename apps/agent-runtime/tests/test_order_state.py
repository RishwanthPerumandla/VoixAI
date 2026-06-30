import agent as agent_module
import logging
import urllib.error
import pytest
import scenarios.wingstop as wingstop_module
from decimal import Decimal
from livekit.agents.llm import ChatMessage
from types import SimpleNamespace

from agent import (
    DEFAULT_CHANNEL_ID,
    DEFAULT_SCENARIO_ID,
    ACCEPTABLE_E2E_LATENCY_MS,
    SUPPORTED_VOICE_PROVIDERS,
    VOICE_PROVIDER_CLASSIC,
    VOICE_PROVIDER_GEMINI_LIVE,
    VOICE_PROVIDER_OPENAI_REALTIME,
    VOICE_ENGINE_GEMINI_LIVE,
    VOICE_ENGINE_GEMINI_LIVE_TEXT,
    VOICE_ENGINE_OPENAI_REALTIME,
    VOICE_ENGINE_OPENAI_REALTIME_TEXT,
    VOICE_ENGINE_PIPELINE,
    RuntimeConfig,
    SessionState,
    SUPPORTED_VOICE_ENGINES,
    TARGET_E2E_LATENCY_MS,
    _publish_session_snapshot,
    _is_closed_connection_error,
    _is_publisher_connection_failure_error,
    _is_publisher_connection_timeout_error,
    _probe_realtime_publisher_connection,
    _fallback_runtime_config_to_classic,
    _format_duration_metric,
    _handle_conversation_item,
    _should_fallback_to_classic_after_probe,
    _normalize_voice_provider,
    _preload_optional_realtime_plugins,
    _runtime_config_from_metadata,
    _needs_tts_fallback_for_forced_speech,
    _resolve_runtime_config,
    _runtime_profile_payload,
    _supports_generate_reply,
    _snapshot_payload,
    _speech_duration_metric,
    _trigger_initial_greeting,
    _trigger_away_prompt,
    _validate_runtime_config,
    _voice_engine_for_provider,
)
from channels import get_channel_definition
from scenarios.wingstop import (
    WingstopAssistant,
    MENU_ITEMS,
    MODIFIER_OPTIONS,
    MockOrder,
    OrderLineItem,
    OrderState,
    audit_assistant_response,
    build_confirmation_summary,
    build_initial_greeting,
    build_wingstop_instructions,
    build_price_quote,
    calculate_order_total,
    create_mock_order,
    detect_order_correction,
    serialize_order_state,
    summarize_order_state,
    validate_order,
    _resolve_flavor_id,
    _resolve_item_id,
    _resolve_modifier_id,
    _validation_errors_for_line,
    _missing_confirmation_reasons,
)


def test_initial_greeting_is_simple_wingstop_dallas_greeting() -> None:
    greeting = build_initial_greeting(get_channel_definition("web"))

    assert greeting == "Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?"


def test_instructions_require_order_name_before_collecting_items() -> None:
    instructions = build_wingstop_instructions(get_channel_definition("web"))

    assert "Ask for the order name next" in instructions
    assert "before collecting any menu items" in instructions


def test_instructions_allow_split_flavors_on_supported_wing_sizes() -> None:
    instructions = build_wingstop_instructions(get_channel_definition("web"))

    assert "Flavor splits are allowed" in instructions
    assert "half Lemon Pepper and half Mango Habanero" in instructions


def test_summarize_order_state_with_structured_items() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=2,
                selected_flavor_ids=["lemon_pepper", "mango_habanero"],
                selected_modifier_ids=["all_flats", "well_done", "ranch"],
            )
        ],
        order_type="pickup",
        customer_name="Jordan",
        phone="2145550199",
        status="collecting",
    )

    summary = summarize_order_state(order)

    assert "order type: pickup" in summary
    assert "2 10 Classic Wings" in summary
    assert "Lemon Pepper" in summary
    assert "All Flats" in summary
    assert "name: Jordan" in summary


def test_summarize_order_state_empty() -> None:
    assert summarize_order_state(OrderState()) == "No order details yet."


def test_format_duration_metric_formats_numbers_and_missing_values() -> None:
    assert _format_duration_metric(0.333) == "0.33s"
    assert _format_duration_metric(None) == "n/a"


def test_speech_duration_metric_uses_started_and_stopped_times() -> None:
    assert _speech_duration_metric(
        {
            "started_speaking_at": 1781810330.72,
            "stopped_speaking_at": 1781810334.45,
        }
    ) == pytest.approx(3.73)
    assert _speech_duration_metric({"started_speaking_at": 4.0, "stopped_speaking_at": 3.0}) is None


def test_handle_conversation_item_logs_clean_assistant_latency_metrics(caplog: pytest.LogCaptureFixture) -> None:
    message = ChatMessage.model_construct(
        role="assistant",
        content=[],
        metrics={
            "started_speaking_at": 1781810330.72,
            "stopped_speaking_at": 1781810334.45,
        },
    )

    with caplog.at_level(logging.INFO, logger="agent"):
        _handle_conversation_item(SimpleNamespace(item=message))

    assert "llm_ttft=n/a" in caplog.text
    assert "tts_ttfb=n/a" in caplog.text
    assert "e2e_latency=n/a" in caplog.text
    assert "speech_duration=3.73s" in caplog.text
    assert "n/as" not in caplog.text
    assert "started_speaking_at" not in caplog.text
    assert "stopped_speaking_at" not in caplog.text


def test_validate_order_rejects_all_flats_on_boneless() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="boneless_10",
                quantity=1,
                selected_flavor_ids=["lemon_pepper"],
                selected_modifier_ids=["all_flats"],
            )
        ],
        order_type="pickup",
    )

    errors = validate_order(order)

    assert "All flats is only available for classic bone-in wings." in errors


def test_validate_order_rejects_too_many_flavors() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_6",
                quantity=1,
                selected_flavor_ids=["lemon_pepper", "garlic_parmesan", "atomic"],
            )
        ],
        order_type="pickup",
    )

    errors = validate_order(order)

    assert "6 Classic Wings can include up to 1 flavor." in errors


def test_resolve_flavor_id_accepts_half_split_phrasing() -> None:
    assert _resolve_flavor_id("half lemon pepper") == "lemon_pepper"
    assert _resolve_flavor_id("half mango habanero") == "mango_habanero"


def test_validate_combo_requires_drink_and_side() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="combo_classic_6",
                quantity=1,
                selected_flavor_ids=["plain"],
            )
        ],
        order_type="pickup",
    )

    errors = validate_order(order)

    assert "This combo requires a drink selection." in errors
    assert "This combo requires a side selection." in errors


def test_calculate_order_total_uses_structured_menu_pricing() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=1,
                selected_flavor_ids=["lemon_pepper", "mango_habanero"],
                selected_modifier_ids=["all_flats", "well_done", "ranch"],
            )
        ],
        order_type="pickup",
    )

    total = calculate_order_total(order)

    assert str(total.quantize(Decimal("0.01"))) == "17.30"


def test_build_price_quote_includes_tax_and_breakdown() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="large_fries",
                quantity=1,
                selected_modifier_ids=["extra_crispy", "extra_seasoning"],
            )
        ],
        order_type="pickup",
    )

    quote = build_price_quote(order)

    assert quote.subtotal == "$5.49"
    assert quote.tax == "$0.45"
    assert quote.total == "$5.94"
    assert quote.line_items[0].name == "Large Seasoned Fries"


def test_build_confirmation_summary_requires_price_and_recap_shape() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="chicken_sandwich",
                quantity=1,
                selected_flavor_ids=["plain"],
            )
        ],
        order_type="pickup",
        customer_name="Taylor",
        phone="2145550101",
    )

    summary = build_confirmation_summary(order, build_price_quote(order))

    assert "Your order is 1 Chicken Sandwich with Plain." in summary
    assert "Total is $7.57." in summary
    assert "Should I place it?" in summary


def test_missing_confirmation_reasons_require_pickup_name_before_placement() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="combo_boneless_6",
                quantity=1,
                selected_flavor_ids=["cajun"],
                selected_modifier_ids=["regular_seasoned_fries", "ranch", "coke"],
            )
        ],
        order_type="pickup",
    )

    reasons = _missing_confirmation_reasons(order)

    assert "the pickup name is missing" in reasons


def test_included_combo_dip_is_not_charged_as_extra_modifier() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="combo_boneless_6",
                quantity=1,
                selected_flavor_ids=["cajun"],
                selected_modifier_ids=["regular_seasoned_fries", "ranch", "coke"],
            )
        ],
        order_type="pickup",
    )

    quote = build_price_quote(order)

    assert quote.subtotal == "$11.99"
    assert quote.total == "$12.98"


def test_create_mock_order_generates_realistic_ticket() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=1,
                selected_flavor_ids=["lemon_pepper", "mango_habanero"],
                selected_modifier_ids=["all_flats", "well_done", "ranch"],
            )
        ],
        order_type="pickup",
        confirmed=True,
        total_shown=True,
        recap_readback=True,
        pos_validation_passed=True,
        status="confirmed_pending_submit",
    )

    mock_order = create_mock_order(order, build_price_quote(order))

    assert mock_order.order_number.startswith("MOCK-")
    assert "VOIX WINGS DEMO" in mock_order.kitchen_ticket
    assert "10 Classic Wings" in mock_order.kitchen_ticket
    assert "ETA:" in mock_order.kitchen_ticket


def test_serialize_order_state_exposes_structured_and_legacy_fields() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="drink_water_item",
                quantity=1,
            )
        ],
        order_type="pickup",
    )

    payload = serialize_order_state(order)

    assert payload["pickup_or_delivery"] == "pickup"
    assert payload["items"] == ["Bottled Water"]
    assert payload["line_items"][0]["name"] == "Bottled Water"
    assert payload["drink"] == "Bottled Water"


def test_detect_order_correction_finds_quantity_change() -> None:
    previous_order = OrderState(
        items=[OrderLineItem(line_id="line-1", item_id="classic_6", quantity=1)],
        order_type="pickup",
    )
    current_order = OrderState(
        items=[OrderLineItem(line_id="line-1", item_id="classic_6", quantity=2)],
        order_type="pickup",
    )

    corrections = detect_order_correction(previous_order, current_order)

    assert corrections == ["items"]


@pytest.mark.asyncio
async def test_update_last_item_blank_optional_fields_do_not_clear_existing_flavor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_validate_order_via_backend(order: OrderState) -> list[str]:
        return validate_order(order)

    async def fail_if_resolve_called(**_: object) -> dict[str, object]:
        raise AssertionError("resolve-selection should not run for blank optional updates")

    monkeypatch.setattr(wingstop_module, "_validate_order_via_backend", fake_validate_order_via_backend)
    monkeypatch.setattr(wingstop_module, "_resolve_selection_via_backend", fail_if_resolve_called)

    session_state = SessionState(
        order=OrderState(
            items=[
                OrderLineItem(
                    line_id="line-1",
                    item_id="classic_8",
                    quantity=1,
                    selected_flavor_ids=["original_hot"],
                    selected_modifier_ids=["ranch"],
                )
            ],
            order_type="pickup",
            customer_name="Rishi",
        )
    )

    async def publish_snapshot(*, reason: str) -> None:
        _ = reason

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.update_last_item(
        context,
        flavors="",
        add_modifiers="",
        remove_modifiers="",
        special_instructions="",
    )

    assert session_state.order.items[-1].selected_flavor_ids == ["original_hot"]
    assert "Please choose a flavor for your wings." not in response


@pytest.mark.asyncio
async def test_add_menu_item_falls_back_to_local_resolution_when_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_resolve_selection_via_backend(**_: object) -> dict[str, object]:
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(wingstop_module, "_resolve_selection_via_backend", fail_resolve_selection_via_backend)

    session_state = SessionState(
        order=OrderState(
            order_type="pickup",
            customer_name="Rishi",
        )
    )

    async def publish_snapshot(*, reason: str) -> None:
        _ = reason

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.add_menu_item(
        context,
        item_name="10 bone in wings",
        quantity=1,
        flavors="lemon pepper",
    )

    assert session_state.order.items[0].item_id == "classic_10"
    assert session_state.order.items[0].selected_flavor_ids == ["lemon_pepper"]
    assert "10 Classic Wings" in response


@pytest.mark.asyncio
async def test_update_last_item_reclassifies_standalone_side_from_modifier_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_resolve_selection_via_backend(
        *,
        item_name: str,
        quantity: int = 1,
        flavors: list[str] | None = None,
        modifiers: list[str] | None = None,
        special_instructions: str | None = None,
        validate_line: bool = True,
    ) -> dict[str, object]:
        item_id = _resolve_item_id(item_name)
        assert item_id is not None

        flavor_ids: list[str] = []
        modifier_ids: list[str] = []
        line_errors: list[str] = []

        for flavor_name in flavors or []:
            flavor_id = _resolve_flavor_id(flavor_name)
            if flavor_id is None:
                line_errors.append(f"{flavor_name} is not available in this demo menu.")
                continue
            if flavor_id not in flavor_ids:
                flavor_ids.append(flavor_id)

        for modifier_name in modifiers or []:
            modifier_id = _resolve_modifier_id(modifier_name)
            if modifier_id is None:
                line_errors.append(f"{modifier_name} is not a valid option for this demo menu.")
                continue
            if modifier_id not in modifier_ids:
                modifier_ids.append(modifier_id)

        if validate_line and not line_errors:
            preview_line = OrderLineItem(
                line_id="line-preview",
                item_id=item_id,
                quantity=quantity,
                selected_flavor_ids=flavor_ids,
                selected_modifier_ids=modifier_ids,
                notes=(special_instructions or "").strip(),
            )
            line_errors = _validation_errors_for_line(preview_line)

        return {
            "item_id": item_id,
            "item_name": MENU_ITEMS[item_id].display_name,
            "flavor_ids": flavor_ids,
            "modifier_ids": modifier_ids,
            "line_errors": line_errors,
            "suggestions": [],
        }

    async def fake_validate_order_via_backend(order: OrderState) -> list[str]:
        return validate_order(order)

    async def fake_price_order_via_backend(order: OrderState) -> tuple[list[str], object]:
        errors = validate_order(order)
        return errors, (None if errors else build_price_quote(order))

    monkeypatch.setattr(wingstop_module, "_resolve_selection_via_backend", fake_resolve_selection_via_backend)
    monkeypatch.setattr(wingstop_module, "_validate_order_via_backend", fake_validate_order_via_backend)
    monkeypatch.setattr(wingstop_module, "_price_order_via_backend", fake_price_order_via_backend)

    session_state = SessionState(
        order=OrderState(
            items=[
                OrderLineItem(
                    line_id="line-1",
                    item_id="classic_10",
                    quantity=1,
                    selected_flavor_ids=["lemon_pepper", "mango_habanero"],
                )
            ],
            order_type="pickup",
            customer_name="Rishi",
        )
    )

    async def publish_snapshot(*, reason: str) -> None:
        _ = reason

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    update_response = await assistant.update_last_item(
        context,
        add_modifiers="all flats, well done, ranch, large seasoned fries, extra crispy",
    )

    assert "Large Seasoned Fries" in update_response
    assert len(session_state.order.items) == 2
    assert session_state.order.items[0].item_id == "classic_10"
    assert session_state.order.items[0].selected_modifier_ids == ["all_flats", "well_done", "ranch"]
    assert session_state.order.items[1].item_id == "large_fries"
    assert session_state.order.items[1].selected_modifier_ids == ["extra_crispy"]

    price_response = await assistant.price_order(context)

    assert "$23.24" in price_response


@pytest.mark.asyncio
async def test_update_last_item_can_switch_boneless_back_to_classic_and_placeable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_resolve_selection_via_backend(
        *,
        item_name: str,
        quantity: int = 1,
        flavors: list[str] | None = None,
        modifiers: list[str] | None = None,
        special_instructions: str | None = None,
        validate_line: bool = True,
    ) -> dict[str, object]:
        item_id = _resolve_item_id(item_name)
        assert item_id is not None

        flavor_ids: list[str] = []
        modifier_ids: list[str] = []
        line_errors: list[str] = []

        for flavor_name in flavors or []:
            flavor_id = _resolve_flavor_id(flavor_name)
            if flavor_id is None:
                line_errors.append(f"{flavor_name} is not available in this demo menu.")
                continue
            if flavor_id not in flavor_ids:
                flavor_ids.append(flavor_id)

        for modifier_name in modifiers or []:
            modifier_id = _resolve_modifier_id(modifier_name)
            if modifier_id is None:
                line_errors.append(f"{modifier_name} is not a valid option for this demo menu.")
                continue
            if modifier_id not in modifier_ids:
                modifier_ids.append(modifier_id)

        if validate_line and not line_errors:
            preview_line = OrderLineItem(
                line_id="line-preview",
                item_id=item_id,
                quantity=quantity,
                selected_flavor_ids=flavor_ids,
                selected_modifier_ids=modifier_ids,
                notes=(special_instructions or "").strip(),
            )
            line_errors = _validation_errors_for_line(preview_line)

        return {
            "item_id": item_id,
            "item_name": MENU_ITEMS[item_id].display_name,
            "flavor_ids": flavor_ids,
            "modifier_ids": modifier_ids,
            "line_errors": line_errors,
            "suggestions": [],
        }

    async def fake_validate_order_via_backend(order: OrderState) -> list[str]:
        return validate_order(order)

    async def fake_price_order_via_backend(order: OrderState) -> tuple[list[str], object]:
        errors = validate_order(order)
        return errors, (None if errors else build_price_quote(order))

    monkeypatch.setattr(wingstop_module, "_resolve_selection_via_backend", fake_resolve_selection_via_backend)
    monkeypatch.setattr(wingstop_module, "_validate_order_via_backend", fake_validate_order_via_backend)
    monkeypatch.setattr(wingstop_module, "_price_order_via_backend", fake_price_order_via_backend)

    session_state = SessionState(
        order=OrderState(
            items=[
                OrderLineItem(
                    line_id="line-1",
                    item_id="boneless_10",
                    quantity=1,
                    selected_flavor_ids=["mango_habanero", "lemon_pepper"],
                    selected_modifier_ids=["well_done", "all_flats", "ranch"],
                ),
                OrderLineItem(
                    line_id="line-2",
                    item_id="large_fries",
                    quantity=1,
                    selected_modifier_ids=["extra_crispy"],
                ),
            ],
            order_type="pickup",
            customer_name="Rishi",
        )
    )

    async def publish_snapshot(*, reason: str) -> None:
        _ = reason

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.update_last_item(
        context,
        target_item_name="wings",
        item_name="10 bone in wings",
        add_modifiers="all flats",
    )

    updated_line = session_state.order.items[0]

    assert updated_line.item_id == "classic_10"
    assert "all_flats" in updated_line.selected_modifier_ids
    assert "All flats is only available for classic bone-in wings." not in response

    price_response = await assistant.price_order(context)

    assert "$23.24" in price_response


@pytest.mark.asyncio
async def test_update_last_item_falls_back_to_local_resolution_when_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_resolve_selection_via_backend(**_: object) -> dict[str, object]:
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(wingstop_module, "_resolve_selection_via_backend", fail_resolve_selection_via_backend)

    session_state = SessionState(
        order=OrderState(
            items=[
                OrderLineItem(
                    line_id="line-1",
                    item_id="classic_10",
                    quantity=1,
                    selected_flavor_ids=["plain"],
                )
            ],
            order_type="pickup",
            customer_name="Rishi",
        )
    )

    async def publish_snapshot(*, reason: str) -> None:
        _ = reason

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.update_last_item(
        context,
        flavors="lemon pepper, mango habanero",
        add_modifiers="all flats",
    )

    assert session_state.order.items[0].selected_flavor_ids == ["lemon_pepper", "mango_habanero"]
    assert "all_flats" in session_state.order.items[0].selected_modifier_ids
    assert "Lemon Pepper" in response


@pytest.mark.asyncio
async def test_review_order_for_confirmation_falls_back_to_local_quote_when_backend_pricing_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_price_order_via_backend(order: OrderState) -> tuple[list[str], object]:
        _ = order
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(wingstop_module, "_price_order_via_backend", fake_price_order_via_backend)

    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=1,
                selected_flavor_ids=["plain"],
            )
        ],
        order_type="pickup",
        customer_name="Rishi",
    )
    session_state = SessionState(order=order)
    published_reasons: list[str] = []

    async def publish_snapshot(*, reason: str) -> None:
        published_reasons.append(reason)

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.review_order_for_confirmation(context)

    assert response == build_confirmation_summary(order, build_price_quote(order))
    assert session_state.price_quote == build_price_quote(order)
    assert published_reasons == ["confirmation_review_ready"]


@pytest.mark.asyncio
async def test_create_mock_order_recovers_missing_state_from_transcript_before_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted = {"order_number": "MOCK-55555", "total": "$63.86", "kitchen_ticket": "TICKET"}

    async def fake_submit(room_name: str, order: OrderState) -> dict[str, object]:
        assert room_name == "demo-room"
        assert order.order_type == "pickup"
        assert order.customer_name == "Cherry"
        assert [line.item_id for line in order.items] == ["boneless_50"]
        assert order.items[0].selected_flavor_ids == ["lemon_pepper", "original_hot"]
        return submitted

    monkeypatch.setattr(wingstop_module, "_submit_order_via_backend", fake_submit)

    session_state = SessionState(
        order=OrderState(
            confirmed=True,
            total_shown=True,
            recap_readback=True,
            pos_validation_passed=True,
            status="awaiting_confirmation",
        ),
        room=SimpleNamespace(name="demo-room"),
    )
    session_state.transcript = [
        {
            "role": "assistant",
            "text": (
                "Got it. So, that's 50 boneless wings, half Lemon Pepper, half Original Hot, "
                "for pickup for Cherry. Your total is $63.86. Should I place that order for you?"
            ),
            "ts": 1.0,
        }
    ]
    published_reasons: list[str] = []

    async def publish_snapshot(*, reason: str) -> None:
        published_reasons.append(reason)

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.create_mock_order(context)

    assert "MOCK-55555" in response
    assert session_state.mock_order is not None
    assert session_state.mock_order.order_number == "MOCK-55555"
    assert published_reasons == ["mock_order_created"]


@pytest.mark.asyncio
async def test_force_handoff_marks_order_and_publishes_snapshot() -> None:
    session_state = SessionState(order=OrderState())
    published_reasons: list[str] = []

    async def publish_snapshot(*, reason: str) -> None:
        published_reasons.append(reason)

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]
    session_state.placement_failure_count = 3

    response = await wingstop_module.force_handoff(
        session_state,
        reason="Customer explicitly asked for a human.",
    )

    assert "team member" in response
    assert session_state.order.status == "handoff_required"
    assert session_state.order.metrics.handoff_required_count == 1
    assert session_state.placement_failure_count == 0
    assert published_reasons == ["handoff_required"]


@pytest.mark.asyncio
async def test_create_mock_order_escalates_to_handoff_after_repeated_failures() -> None:
    session_state = SessionState(
        order=OrderState(),
        placement_failure_count=1,
    )
    published_reasons: list[str] = []

    async def publish_snapshot(*, reason: str) -> None:
        published_reasons.append(reason)

    session_state.publish_snapshot = publish_snapshot  # type: ignore[method-assign]

    assistant = WingstopAssistant(llm=object(), channel=get_channel_definition("web"))
    context = SimpleNamespace(userdata=session_state)

    response = await assistant.create_mock_order(context)

    assert "team member" in response
    assert session_state.order.status == "handoff_required"
    assert published_reasons == ["handoff_required"]


def test_audit_assistant_response_blocks_hallucinated_price_and_success() -> None:
    order = OrderState(
        items=[OrderLineItem(line_id="line-1", item_id="classic_6", quantity=1, selected_flavor_ids=["plain"])],
        order_type="pickup",
    )
    quote = build_price_quote(order)

    violations = audit_assistant_response(
        "Great, your order was placed and the total is $99.00.",
        order,
        quote,
        None,
    )

    assert any("did not match" in violation for violation in violations)
    assert any("claimed the order was placed" in violation for violation in violations)


def test_snapshot_payload_includes_price_quote_and_guardrails() -> None:
    order = OrderState(
        items=[
            OrderLineItem(
                line_id="line-1",
                item_id="classic_10",
                quantity=1,
                selected_flavor_ids=["plain"],
            )
        ],
        order_type="pickup",
        confirmed=False,
    )
    quote = build_price_quote(order)
    session_state = SessionState(
        scenario_id=DEFAULT_SCENARIO_ID,
        channel_id=DEFAULT_CHANNEL_ID,
        order=order,
        price_quote=quote,
        mock_order=MockOrder(
            order_number="MOCK-10001",
            total=quote.total,
            summary="summary",
            kitchen_ticket="ticket",
        ),
        runtime_profile=_runtime_profile_payload(
            RuntimeConfig(
                voice_engine="openai_realtime",
                preset_id="openai-realtime-voice",
                preset_label="OpenAI Realtime Voice",
            )
        ),
        turn_count=3,
        user_turn_metrics={
            "transcription_delay": 0.22,
            "end_of_turn_delay": 0.41,
            "on_user_turn_completed_delay": 0.55,
        },
        assistant_turn_metrics={
            "llm_ttft": 0.33,
            "tts_ttfb": 0.11,
            "e2e_latency": 0.71,
            "started_speaking_at": 0.5,
            "stopped_speaking_at": 1.4,
        },
        assistant_guardrail_violations=["example violation"],
    )

    payload = _snapshot_payload(session_state, reason="assistant_turn_metrics")

    assert payload["type"] == "session_snapshot"
    assert payload["scenario_id"] == DEFAULT_SCENARIO_ID
    assert payload["target_e2e_latency_ms"] == TARGET_E2E_LATENCY_MS
    assert payload["acceptable_e2e_latency_ms"] == ACCEPTABLE_E2E_LATENCY_MS
    assert payload["order"]["line_items"][0]["name"] == "10 Classic Wings"
    assert payload["price_quote"]["total"] == quote.total
    assert payload["assistant_guardrail_violations"] == ["example violation"]
    assert payload["transcript"] == []


@pytest.mark.asyncio
async def test_publish_session_snapshot_retries_on_transient_publisher_failure() -> None:
    """A transient publisher blip must NOT take telemetry dark for the rest of
    the call — the live UI (transcript, order, confirmation) depends on it, so it
    keeps retrying and only backs off after repeated consecutive failures."""
    calls = 0

    class FakeParticipant:
        async def publish_data(self, *_: object, **__: object) -> None:
            nonlocal calls
            calls += 1
            raise RuntimeError("engine: connection error: could not establish publisher connection: timeout")

    session_state = SessionState(
        room=SimpleNamespace(name="demo-room", local_participant=FakeParticipant()),
    )

    # Two failures (below the back-off threshold) both still attempt to publish —
    # telemetry is not permanently disabled after a single blip.
    await _publish_session_snapshot(session_state, reason="session_started")
    await _publish_session_snapshot(session_state, reason="order_state_updated")

    assert calls == 2
    assert session_state.telemetry_publish_failures == 2
    assert session_state.telemetry_cooldown_until == 0.0


def test_is_publisher_connection_timeout_error_detects_livekit_timeout_shape() -> None:
    assert _is_publisher_connection_timeout_error(
        RuntimeError("engine: connection error: could not establish publisher connection: timeout")
    )
    assert not _is_publisher_connection_timeout_error(RuntimeError("something else"))


def test_is_closed_connection_error_detects_closed_shape() -> None:
    assert _is_closed_connection_error(RuntimeError("engine: connection error: closed"))
    assert not _is_closed_connection_error(RuntimeError("engine: connection error: timeout"))


def test_is_publisher_connection_failure_error_detects_timeout_and_closed() -> None:
    assert _is_publisher_connection_failure_error(
        RuntimeError("engine: connection error: could not establish publisher connection: timeout")
    )
    assert _is_publisher_connection_failure_error(RuntimeError("engine: connection error: closed"))


@pytest.mark.asyncio
async def test_probe_realtime_publisher_connection_streams_probe_bytes() -> None:
    calls: list[tuple[str, bytes]] = []

    class FakeWriter:
        async def write(self, data: bytes) -> None:
            calls.append(("write", data))

        async def aclose(self) -> None:
            calls.append(("close", b""))

    class FakeParticipant:
        async def stream_bytes(self, *, name: str, topic: str) -> FakeWriter:
            assert name.startswith("probe_")
            assert topic == "voixai.publisher_probe"
            calls.append(("open", b""))
            return FakeWriter()

    room = SimpleNamespace(local_participant=FakeParticipant())

    await _probe_realtime_publisher_connection(room)

    assert calls == [("open", b""), ("write", b"ok"), ("close", b"")]


def test_should_fallback_to_classic_after_probe_for_publisher_timeout() -> None:
    assert _should_fallback_to_classic_after_probe(
        RuntimeError("engine: connection error: could not establish publisher connection: timeout")
    )
    assert not _should_fallback_to_classic_after_probe(RuntimeError("different failure"))


def test_fallback_runtime_config_to_classic_sets_runtime_profile_fields() -> None:
    runtime_config = RuntimeConfig(
        voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
        voice_engine=VOICE_ENGINE_GEMINI_LIVE,
        preset_id="gemini-live-voice",
        preset_label="Gemini Live",
        comparison_label="Native Gemini speech to speech",
    )

    fallback = _fallback_runtime_config_to_classic(
        runtime_config,
        reason="Realtime publisher connection failed during startup probe. Falling back to the classic pipeline.",
    )

    assert fallback.voice_provider == VOICE_PROVIDER_CLASSIC
    assert fallback.voice_engine == VOICE_ENGINE_PIPELINE
    assert fallback.preset_id == "classic-pipeline"
    assert fallback.preset_label == "Classic Voice (fallback)"
    assert fallback.fallback_reason is not None


def test_runtime_profile_payload_includes_scenario_id() -> None:
    payload = _runtime_profile_payload(
        RuntimeConfig(
            scenario_id=DEFAULT_SCENARIO_ID,
            channel_id=DEFAULT_CHANNEL_ID,
        )
    )

    assert payload["scenario_id"] == DEFAULT_SCENARIO_ID
    assert payload["channel_id"] == DEFAULT_CHANNEL_ID


def test_resolve_runtime_config_falls_back_to_default_scenario() -> None:
    runtime_config = RuntimeConfig(
        scenario_id="unknown_scenario",
        voice_provider=VOICE_PROVIDER_CLASSIC,
        voice_engine=VOICE_ENGINE_PIPELINE,
    )

    resolved = _resolve_runtime_config(runtime_config)

    assert resolved.scenario_id == DEFAULT_SCENARIO_ID


def test_resolve_runtime_config_falls_back_to_default_channel() -> None:
    runtime_config = RuntimeConfig(
        channel_id="unknown_channel",
        voice_provider=VOICE_PROVIDER_CLASSIC,
        voice_engine=VOICE_ENGINE_PIPELINE,
    )

    resolved = _resolve_runtime_config(runtime_config)

    assert resolved.channel_id == DEFAULT_CHANNEL_ID


def test_supported_voice_engines_cover_pipeline_and_realtime_modes() -> None:
    assert SUPPORTED_VOICE_ENGINES == {
        VOICE_ENGINE_PIPELINE,
        VOICE_ENGINE_OPENAI_REALTIME,
        VOICE_ENGINE_OPENAI_REALTIME_TEXT,
        VOICE_ENGINE_GEMINI_LIVE,
        VOICE_ENGINE_GEMINI_LIVE_TEXT,
    }


def test_supported_voice_providers_cover_classic_and_openai_realtime() -> None:
    assert SUPPORTED_VOICE_PROVIDERS == {
        VOICE_PROVIDER_CLASSIC,
        VOICE_PROVIDER_OPENAI_REALTIME,
        VOICE_PROVIDER_GEMINI_LIVE,
    }


def test_voice_provider_normalization_maps_legacy_pipeline_value() -> None:
    assert _normalize_voice_provider("pipeline") == VOICE_PROVIDER_CLASSIC
    assert _normalize_voice_provider("classic") == VOICE_PROVIDER_CLASSIC
    assert _normalize_voice_provider("openai_realtime") == VOICE_PROVIDER_OPENAI_REALTIME
    assert _normalize_voice_provider("gemini_live") == VOICE_PROVIDER_GEMINI_LIVE


def test_voice_engine_mapping_uses_pipeline_for_classic_provider() -> None:
    assert _voice_engine_for_provider(VOICE_PROVIDER_CLASSIC) == VOICE_ENGINE_PIPELINE
    assert (
        _voice_engine_for_provider(VOICE_PROVIDER_OPENAI_REALTIME)
        == VOICE_ENGINE_OPENAI_REALTIME
    )
    assert _voice_engine_for_provider(VOICE_PROVIDER_GEMINI_LIVE) == VOICE_ENGINE_GEMINI_LIVE


def test_runtime_config_from_metadata_parses_dispatch_json() -> None:
    config = _runtime_config_from_metadata(
        '{"voice_engine": "gemini_live", "scenario_id": "wingstop_inbound_ordering"}'
    )

    assert config is not None
    assert config.voice_provider == VOICE_PROVIDER_GEMINI_LIVE
    assert config.voice_engine == VOICE_ENGINE_GEMINI_LIVE
    assert config.scenario_id == "wingstop_inbound_ordering"


def test_runtime_config_from_metadata_returns_none_for_unusable_input() -> None:
    assert _runtime_config_from_metadata(None) is None
    assert _runtime_config_from_metadata("") is None
    assert _runtime_config_from_metadata("   ") is None
    assert _runtime_config_from_metadata("not json") is None
    assert _runtime_config_from_metadata("[1, 2, 3]") is None


def test_realtime_validation_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_config = RuntimeConfig(
        voice_provider=VOICE_PROVIDER_OPENAI_REALTIME,
        voice_engine=VOICE_ENGINE_OPENAI_REALTIME,
    )
    monkeypatch.setattr(agent_module, "LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setattr(agent_module, "LIVEKIT_API_KEY", "lk-api-key")
    monkeypatch.setattr(agent_module, "LIVEKIT_API_SECRET", "lk-api-secret")
    monkeypatch.setattr(agent_module, "OPENAI_API_KEY", "")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        _validate_runtime_config(runtime_config)


def test_gemini_validation_requires_google_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_config = RuntimeConfig(
        voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
        voice_engine=VOICE_ENGINE_GEMINI_LIVE,
    )
    monkeypatch.setattr(agent_module, "LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setattr(agent_module, "LIVEKIT_API_KEY", "lk-api-key")
    monkeypatch.setattr(agent_module, "LIVEKIT_API_SECRET", "lk-api-secret")
    monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", "")

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        _validate_runtime_config(runtime_config)


def test_preload_optional_realtime_plugins_caches_openai_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    turn_detection = type("FakeTurnDetection", (), {})

    def fake_import_module(name: str) -> object:
        if name == "livekit.plugins.openai":
            return SimpleNamespace(realtime=SimpleNamespace(RealtimeModel=object))
        if name == "openai.types.beta.realtime.session":
            return SimpleNamespace(TurnDetection=turn_detection)
        raise AssertionError(f"unexpected import {name}")

    monkeypatch.setattr(agent_module, "_OPENAI_REALTIME_PLUGIN", None)
    monkeypatch.setattr(agent_module, "_OPENAI_REALTIME_TURN_DETECTION", None)
    monkeypatch.setattr(agent_module, "_GOOGLE_REALTIME_PLUGIN", None)
    monkeypatch.setattr(agent_module, "_OPTIONAL_PLUGIN_IMPORT_ERRORS", {})
    monkeypatch.setattr(
        agent_module,
        "_has_module",
        lambda module_name: module_name in {"livekit.plugins.openai", "openai"},
    )
    monkeypatch.setattr(agent_module.importlib, "import_module", fake_import_module)

    _preload_optional_realtime_plugins()

    assert agent_module._OPENAI_REALTIME_PLUGIN is not None
    assert agent_module._OPENAI_REALTIME_TURN_DETECTION is turn_detection


def test_trigger_away_prompt_uses_say_for_classic() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeSession:
        def say(self, *args: object, **kwargs: object) -> None:
            calls.append(("say", args, kwargs))

        def generate_reply(self, *args: object, **kwargs: object) -> None:
            calls.append(("generate_reply", args, kwargs))

    _trigger_away_prompt(
        FakeSession(),
        RuntimeConfig(voice_provider=VOICE_PROVIDER_CLASSIC, voice_engine=VOICE_ENGINE_PIPELINE),
    )

    assert calls == [
        (
            "say",
            ("Are you still there?",),
            {"allow_interruptions": True, "add_to_chat_ctx": False},
        )
    ]


def test_trigger_away_prompt_uses_generate_reply_for_realtime() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeSession:
        def say(self, *args: object, **kwargs: object) -> None:
            calls.append(("say", args, kwargs))

        def generate_reply(self, *args: object, **kwargs: object) -> None:
            calls.append(("generate_reply", args, kwargs))

    _trigger_away_prompt(
        FakeSession(),
        RuntimeConfig(
            voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
            voice_engine=VOICE_ENGINE_GEMINI_LIVE,
            google_realtime_model="gemini-2.5-flash-native-audio-preview-12-2025",
        ),
    )

    assert calls == [
        (
            "generate_reply",
            (),
            {
                "instructions": "The user went silent. Ask only one short question: are you still there?"
            },
        )
    ]


def test_trigger_away_prompt_uses_generate_reply_for_gemini_31_realtime() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeSession:
        def say(self, *args: object, **kwargs: object) -> None:
            calls.append(("say", args, kwargs))

        def generate_reply(self, *args: object, **kwargs: object) -> None:
            calls.append(("generate_reply", args, kwargs))

    _trigger_away_prompt(
        FakeSession(),
        RuntimeConfig(
            voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
            voice_engine=VOICE_ENGINE_GEMINI_LIVE,
            google_realtime_model="gemini-3.1-flash-live-preview",
        ),
    )

    # Gemini 3.1 now greets/prompts in its own voice via generate_reply (forked
    # plugin), not the TTS say() fallback.
    assert calls == [
        (
            "generate_reply",
            (),
            {
                "instructions": "The user went silent. Ask only one short question: are you still there?"
            },
        )
    ]


def test_trigger_initial_greeting_uses_say_for_classic() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeSession:
        def say(self, *args: object, **kwargs: object) -> None:
            calls.append(("say", args, kwargs))

        def generate_reply(self, *args: object, **kwargs: object) -> None:
            calls.append(("generate_reply", args, kwargs))

    _trigger_initial_greeting(
        FakeSession(),
        RuntimeConfig(voice_provider=VOICE_PROVIDER_CLASSIC, voice_engine=VOICE_ENGINE_PIPELINE),
        "Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?",
    )

    assert calls == [
        (
            "say",
            ("Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?",),
            {"allow_interruptions": True, "add_to_chat_ctx": True},
        )
    ]


def test_trigger_initial_greeting_uses_generate_reply_for_realtime() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeSession:
        def say(self, *args: object, **kwargs: object) -> None:
            calls.append(("say", args, kwargs))

        def generate_reply(self, *args: object, **kwargs: object) -> None:
            calls.append(("generate_reply", args, kwargs))

    _trigger_initial_greeting(
        FakeSession(),
        RuntimeConfig(
            voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
            voice_engine=VOICE_ENGINE_GEMINI_LIVE,
            google_realtime_model="gemini-2.5-flash-native-audio-preview-12-2025",
        ),
        "Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?",
    )

    assert calls == [
        (
            "generate_reply",
            (),
            {
                "instructions": "Greet the customer first. Use this exact greeting content naturally and only once: Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?"
            },
        )
    ]


def test_trigger_initial_greeting_uses_generate_reply_for_gemini_31_realtime() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeSession:
        def say(self, *args: object, **kwargs: object) -> None:
            calls.append(("say", args, kwargs))

        def generate_reply(self, *args: object, **kwargs: object) -> None:
            calls.append(("generate_reply", args, kwargs))

    _trigger_initial_greeting(
        FakeSession(),
        RuntimeConfig(
            voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
            voice_engine=VOICE_ENGINE_GEMINI_LIVE,
            google_realtime_model="gemini-3.1-flash-live-preview",
        ),
        "Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?",
    )

    # Gemini 3.1 now greets once in its own voice via generate_reply, so there is
    # no separate TTS say() greeting and no duplicate.
    assert calls == [
        (
            "generate_reply",
            (),
            {
                "instructions": "Greet the customer first. Use this exact greeting content naturally and only once: Hey, thanks for calling Wingstop Dallas, this is Mia — what can I get started for you?"
            },
        )
    ]


def test_supports_generate_reply_for_gemini_31() -> None:
    assert (
        _supports_generate_reply(
            RuntimeConfig(
                voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
                voice_engine=VOICE_ENGINE_GEMINI_LIVE,
                google_realtime_model="gemini-3.1-flash-live-preview",
            )
        )
        is True
    )


def test_no_tts_fallback_for_forced_speech_on_gemini_31() -> None:
    assert (
        _needs_tts_fallback_for_forced_speech(
            RuntimeConfig(
                voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
                voice_engine=VOICE_ENGINE_GEMINI_LIVE,
                google_realtime_model="gemini-3.1-flash-live-preview",
            )
        )
        is False
    )


def test_build_realtime_session_skips_tts_for_gemini_31(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeAgentSession:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(agent_module, "AgentSession", FakeAgentSession)
    monkeypatch.setattr(
        agent_module.inference,
        "TTS",
        lambda **kwargs: {"kind": "tts", **kwargs},
    )

    agent_module._build_realtime_session(
        RuntimeConfig(
            voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
            voice_engine=VOICE_ENGINE_GEMINI_LIVE,
            google_realtime_model="gemini-3.1-flash-live-preview",
            tts_model="cartesia/sonic-3",
        ),
        text_only=False,
    )

    # Gemini 3.1 speaks natively now; no separate Cartesia TTS voice attached.
    assert "tts" not in captured


def test_build_realtime_session_skips_tts_for_gemini_25_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeAgentSession:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(agent_module, "AgentSession", FakeAgentSession)
    monkeypatch.setattr(
        agent_module.inference,
        "TTS",
        lambda **kwargs: {"kind": "tts", **kwargs},
    )

    agent_module._build_realtime_session(
        RuntimeConfig(
            voice_provider=VOICE_PROVIDER_GEMINI_LIVE,
            voice_engine=VOICE_ENGINE_GEMINI_LIVE,
            google_realtime_model="gemini-2.5-flash-native-audio-preview-12-2025",
            tts_model="cartesia/sonic-3",
        ),
        text_only=False,
    )

    assert "tts" not in captured
