from agent import (
    ACCEPTABLE_E2E_LATENCY_MS,
    VOICE_ENGINE_GEMINI_LIVE,
    VOICE_ENGINE_GEMINI_LIVE_TEXT,
    VOICE_ENGINE_OPENAI_REALTIME,
    VOICE_ENGINE_OPENAI_REALTIME_TEXT,
    VOICE_ENGINE_PIPELINE,
    OrderState,
    RuntimeConfig,
    build_confirmation_summary,
    calculate_order_total,
    create_mock_order,
    SessionState,
    SUPPORTED_VOICE_ENGINES,
    TARGET_E2E_LATENCY_MS,
    _runtime_profile_payload,
    _snapshot_payload,
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


def test_snapshot_payload_includes_order_and_latency_targets() -> None:
    session_state = SessionState(
        order=OrderState(
            pickup_or_delivery="pickup",
            items=["wings"],
            drink="lemonade",
            confirmed=False,
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
    )

    payload = _snapshot_payload(session_state, reason="assistant_turn_metrics")

    assert payload["type"] == "session_snapshot"
    assert payload["reason"] == "assistant_turn_metrics"
    assert payload["target_e2e_latency_ms"] == TARGET_E2E_LATENCY_MS
    assert payload["acceptable_e2e_latency_ms"] == ACCEPTABLE_E2E_LATENCY_MS
    assert payload["turn_count"] == 3
    assert payload["order"]["items"] == ["wings"]
    assert payload["runtime_profile"]["voice_engine"] == "openai_realtime"
    assert payload["assistant_turn_metrics"]["e2e_latency"] == 0.71


def test_supported_voice_engines_cover_pipeline_and_realtime_modes() -> None:
    assert SUPPORTED_VOICE_ENGINES == {
        VOICE_ENGINE_PIPELINE,
        VOICE_ENGINE_OPENAI_REALTIME,
        VOICE_ENGINE_OPENAI_REALTIME_TEXT,
        VOICE_ENGINE_GEMINI_LIVE,
        VOICE_ENGINE_GEMINI_LIVE_TEXT,
    }
