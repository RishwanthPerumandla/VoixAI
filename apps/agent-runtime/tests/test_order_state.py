import agent as agent_module
import pytest
from decimal import Decimal
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
    _normalize_voice_provider,
    _preload_optional_realtime_plugins,
    _runtime_config_from_metadata,
    _needs_tts_fallback_for_forced_speech,
    _resolve_runtime_config,
    _runtime_profile_payload,
    _supports_generate_reply,
    _snapshot_payload,
    _trigger_initial_greeting,
    _trigger_away_prompt,
    _validate_runtime_config,
    _voice_engine_for_provider,
)
from channels import get_channel_definition
from scenarios.wingstop import (
    MENU_ITEMS,
    MODIFIER_OPTIONS,
    MockOrder,
    OrderLineItem,
    OrderState,
    audit_assistant_response,
    build_confirmation_summary,
    build_initial_greeting,
    build_price_quote,
    calculate_order_total,
    create_mock_order,
    detect_order_correction,
    serialize_order_state,
    summarize_order_state,
    validate_order,
    _missing_confirmation_reasons,
)


def test_initial_greeting_is_bilingual_and_requests_service_type() -> None:
    greeting = build_initial_greeting(get_channel_definition("web"))

    assert "Welcome to Voix Wings Demo" in greeting
    assert "Bienvenido" in greeting
    assert "pickup or delivery" in greeting
    assert "English or Spanish" not in greeting
    assert "Would you like English or Spanish" not in greeting


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
        "Welcome to Voix Wings Demo.",
    )

    assert calls == [
        (
            "say",
            ("Welcome to Voix Wings Demo.",),
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
        "Welcome to Voix Wings Demo.",
    )

    assert calls == [
        (
            "generate_reply",
            (),
            {
                "instructions": "Greet the customer first. Use this exact greeting content naturally and only once: Welcome to Voix Wings Demo."
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
        "Welcome to Voix Wings Demo.",
    )

    # Gemini 3.1 now greets once in its own voice via generate_reply, so there is
    # no separate TTS say() greeting and no duplicate.
    assert calls == [
        (
            "generate_reply",
            (),
            {
                "instructions": "Greet the customer first. Use this exact greeting content naturally and only once: Welcome to Voix Wings Demo."
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
