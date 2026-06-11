import agent as agent_module
import pytest
from types import SimpleNamespace

from agent import (
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
    OrderState,
    RuntimeConfig,
    build_confirmation_summary,
    calculate_order_total,
    create_mock_order,
    SessionState,
    SUPPORTED_VOICE_ENGINES,
    TARGET_E2E_LATENCY_MS,
    _normalize_voice_provider,
    _runtime_profile_payload,
    _snapshot_payload,
    _preload_optional_realtime_plugins,
    _validate_runtime_config,
    _voice_engine_for_provider,
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
