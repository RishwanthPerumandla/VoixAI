import logging
import os
import asyncio
import importlib
import importlib.util
import json
import time
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AgentStateChangedEvent,
    AgentServer,
    AgentSession,
    ConversationItemAddedEvent,
    JobContext,
    JobProcess,
    UserStateChangedEvent,
    cli,
    inference,
    room_io,
)
from livekit.agents.llm import ChatMessage
from livekit.plugins import ai_coustics, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from call_recorder import finalize_call, open_call
from channels import CHANNEL_REGISTRY, DEFAULT_CHANNEL_ID, get_channel_definition
from scenarios import DEFAULT_SCENARIO_ID, SCENARIO_REGISTRY, get_scenario_definition
from scenarios.wingstop import (
    MockOrder,
    OrderState,
    PriceQuote,
    audit_assistant_response,
    build_initial_greeting,
)

logger = logging.getLogger("agent")
ROOT_DIR = Path(__file__).resolve().parents[3]
SESSION_CONFIG_DIR = ROOT_DIR / ".voixai" / "session-configs"

# Support either the starter's `.env.local` convention or a plain `.env`
# so local setup is less brittle during MVP work.
load_dotenv(".env")
load_dotenv(".env.local", override=True)

AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
USER_AWAY_TIMEOUT_SECONDS = float(os.getenv("USER_AWAY_TIMEOUT_SECONDS", "12"))
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.08"))
SCENARIO_ID = os.getenv("SCENARIO_ID", DEFAULT_SCENARIO_ID).strip() or DEFAULT_SCENARIO_ID
CHANNEL_ID = os.getenv("CHANNEL_ID", DEFAULT_CHANNEL_ID).strip() or DEFAULT_CHANNEL_ID
VOICE_PROVIDER = os.getenv(
    "VOICE_PROVIDER",
    os.getenv("VOICE_ENGINE", "classic"),
).strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-5.3-chat-latest")
STT_MODEL = os.getenv("STT_MODEL", "deepgram/flux-general")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en").strip() or "en"
TTS_MODEL = os.getenv("TTS_MODEL", "cartesia/sonic-3")
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
OPENAI_REALTIME_VOICE = os.getenv("OPENAI_REALTIME_VOICE", "alloy")
OPENAI_REALTIME_EAGERNESS = os.getenv("OPENAI_REALTIME_EAGERNESS", "medium")
GOOGLE_REALTIME_MODEL = os.getenv("GOOGLE_REALTIME_MODEL", "gemini-3.1-flash-live-preview")
GOOGLE_REALTIME_VOICE = os.getenv("GOOGLE_REALTIME_VOICE", "Puck")
REALTIME_TEMPERATURE = float(os.getenv("REALTIME_TEMPERATURE", "0.6"))
REALTIME_ENABLE_AFFECTIVE_DIALOG = (
    os.getenv("REALTIME_ENABLE_AFFECTIVE_DIALOG", "false").strip().lower() == "true"
)
REALTIME_ENABLE_PROACTIVITY = (
    os.getenv("REALTIME_ENABLE_PROACTIVITY", "false").strip().lower() == "true"
)
TELEMETRY_TOPIC = "voixai.telemetry"
TARGET_E2E_LATENCY_MS = 800
ACCEPTABLE_E2E_LATENCY_MS = 1500

VOICE_PROVIDER_CLASSIC = "classic"
VOICE_PROVIDER_OPENAI_REALTIME = "openai_realtime"
VOICE_PROVIDER_GEMINI_LIVE = "gemini_live"
SUPPORTED_VOICE_PROVIDERS = {
    VOICE_PROVIDER_CLASSIC,
    VOICE_PROVIDER_OPENAI_REALTIME,
    VOICE_PROVIDER_GEMINI_LIVE,
}

VOICE_ENGINE_PIPELINE = "pipeline"
VOICE_ENGINE_OPENAI_REALTIME = "openai_realtime"
VOICE_ENGINE_OPENAI_REALTIME_TEXT = "openai_realtime_text"
VOICE_ENGINE_GEMINI_LIVE = "gemini_live"
VOICE_ENGINE_GEMINI_LIVE_TEXT = "gemini_live_text"
SUPPORTED_VOICE_ENGINES = {
    VOICE_ENGINE_PIPELINE,
    VOICE_ENGINE_OPENAI_REALTIME,
    VOICE_ENGINE_OPENAI_REALTIME_TEXT,
    VOICE_ENGINE_GEMINI_LIVE,
    VOICE_ENGINE_GEMINI_LIVE_TEXT,
}

_OPTIONAL_PLUGIN_IMPORT_ERRORS: dict[str, Exception] = {}
_OPENAI_REALTIME_PLUGIN: Any | None = None
_OPENAI_REALTIME_TURN_DETECTION: Any | None = None
_GOOGLE_REALTIME_PLUGIN: Any | None = None


def _normalize_voice_provider(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {VOICE_PROVIDER_CLASSIC, VOICE_ENGINE_PIPELINE}:
        return VOICE_PROVIDER_CLASSIC
    if normalized in {VOICE_PROVIDER_OPENAI_REALTIME, VOICE_ENGINE_OPENAI_REALTIME_TEXT}:
        return VOICE_PROVIDER_OPENAI_REALTIME
    if normalized in {VOICE_PROVIDER_GEMINI_LIVE, VOICE_ENGINE_GEMINI_LIVE_TEXT}:
        return VOICE_PROVIDER_GEMINI_LIVE
    return normalized


def _voice_engine_for_provider(provider: str) -> str:
    if provider == VOICE_PROVIDER_OPENAI_REALTIME:
        return VOICE_ENGINE_OPENAI_REALTIME
    if provider == VOICE_PROVIDER_GEMINI_LIVE:
        return VOICE_ENGINE_GEMINI_LIVE
    return VOICE_ENGINE_PIPELINE


@dataclass
class SessionState:
    scenario_id: str = DEFAULT_SCENARIO_ID
    channel_id: str = DEFAULT_CHANNEL_ID
    order: OrderState = field(default_factory=OrderState)
    price_quote: PriceQuote | None = None
    mock_order: MockOrder | None = None
    user_turn_metrics: dict[str, float | None] | None = None
    assistant_turn_metrics: dict[str, float | None] | None = None
    turn_count: int = 0
    waiting_for_customer: bool = False
    runtime_profile: dict[str, object] | None = None
    assistant_guardrail_violations: list[str] = field(default_factory=list)
    room: rtc.Room | None = field(default=None, repr=False, compare=False)
    # Call telemetry (dashboard): a rolling transcript + lifetime guardrail count
    # so the call can be finalized on shutdown.
    call_id: str | None = None
    call_started_at: float | None = None
    transcript: list[dict[str, object]] = field(default_factory=list)
    guardrail_violation_count: int = 0

    async def publish_snapshot(self, *, reason: str) -> None:
        await _publish_session_snapshot(self, reason=reason)


@dataclass
class RuntimeConfig:
    scenario_id: str = SCENARIO_ID
    channel_id: str = CHANNEL_ID
    voice_provider: str = _normalize_voice_provider(VOICE_PROVIDER)
    voice_engine: str = _voice_engine_for_provider(_normalize_voice_provider(VOICE_PROVIDER))
    llm_model: str = LLM_MODEL
    stt_model: str = STT_MODEL
    stt_language: str = STT_LANGUAGE
    tts_model: str = TTS_MODEL
    openai_realtime_model: str = OPENAI_REALTIME_MODEL
    openai_realtime_voice: str = OPENAI_REALTIME_VOICE
    openai_realtime_eagerness: str = OPENAI_REALTIME_EAGERNESS
    google_realtime_model: str = GOOGLE_REALTIME_MODEL
    google_realtime_voice: str = GOOGLE_REALTIME_VOICE
    realtime_temperature: float = REALTIME_TEMPERATURE
    realtime_enable_affective_dialog: bool = REALTIME_ENABLE_AFFECTIVE_DIALOG
    realtime_enable_proactivity: bool = REALTIME_ENABLE_PROACTIVITY
    preset_id: str | None = None
    preset_label: str | None = None
    comparison_label: str | None = None
    requested_voice_provider: str | None = None
    requested_voice_engine: str | None = None
    fallback_reason: str | None = None

def _session_config_path(room_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", room_name).strip("-") or "default-room"
    return SESSION_CONFIG_DIR / f"{safe_name}.json"


def _normalize_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return default


def _normalize_float(value: object, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _runtime_config_from_payload(payload: Mapping[str, object] | None) -> RuntimeConfig:
    if payload is None:
        return RuntimeConfig()

    defaults = RuntimeConfig()
    requested_provider = str(
        payload.get(
            "voice_provider",
            payload.get("voice_engine", defaults.voice_provider),
        )
    ).strip().lower()
    voice_provider = _normalize_voice_provider(requested_provider)
    return RuntimeConfig(
        scenario_id=str(payload.get("scenario_id", defaults.scenario_id)).strip()
        or defaults.scenario_id,
        channel_id=str(payload.get("channel_id", defaults.channel_id)).strip()
        or defaults.channel_id,
        voice_provider=voice_provider,
        voice_engine=_voice_engine_for_provider(voice_provider),
        llm_model=str(payload.get("llm_model", defaults.llm_model)).strip(),
        stt_model=str(payload.get("stt_model", defaults.stt_model)).strip(),
        stt_language=str(payload.get("stt_language", defaults.stt_language)).strip()
        or defaults.stt_language,
        tts_model=str(payload.get("tts_model", defaults.tts_model)).strip(),
        openai_realtime_model=str(
            payload.get("openai_realtime_model", defaults.openai_realtime_model)
        ).strip(),
        openai_realtime_voice=str(
            payload.get("openai_realtime_voice", defaults.openai_realtime_voice)
        ).strip(),
        openai_realtime_eagerness=str(
            payload.get("openai_realtime_eagerness", defaults.openai_realtime_eagerness)
        ).strip(),
        google_realtime_model=str(
            payload.get("google_realtime_model", defaults.google_realtime_model)
        ).strip(),
        google_realtime_voice=str(
            payload.get("google_realtime_voice", defaults.google_realtime_voice)
        ).strip(),
        realtime_temperature=_normalize_float(
            payload.get("realtime_temperature"),
            defaults.realtime_temperature,
        ),
        realtime_enable_affective_dialog=_normalize_bool(
            payload.get("realtime_enable_affective_dialog"),
            defaults.realtime_enable_affective_dialog,
        ),
        realtime_enable_proactivity=_normalize_bool(
            payload.get("realtime_enable_proactivity"),
            defaults.realtime_enable_proactivity,
        ),
        preset_id=str(payload["preset_id"]).strip() if payload.get("preset_id") else None,
        preset_label=str(payload["preset_label"]).strip() if payload.get("preset_label") else None,
        comparison_label=(
            str(payload["comparison_label"]).strip()
            if payload.get("comparison_label")
            else None
        ),
        requested_voice_provider=requested_provider,
        requested_voice_engine=(
            str(payload["voice_engine"]).strip().lower() if payload.get("voice_engine") else None
        ),
    )


def _runtime_config_from_metadata(metadata: str | None) -> RuntimeConfig | None:
    """Parse runtime config from the agent dispatch/job metadata.

    This is the primary handoff path: the config travels with the agent job, so
    it works across hosts without a shared filesystem. Returns ``None`` when no
    usable metadata is present so the caller can fall back to the file.
    """
    if not metadata or not metadata.strip():
        return None

    try:
        payload = json.loads(metadata)
    except Exception:
        logger.warning("Failed to parse job metadata as runtime config JSON")
        return None

    if not isinstance(payload, Mapping):
        logger.warning("Job metadata runtime config was not an object")
        return None

    return _runtime_config_from_payload(payload)


def _load_runtime_config_for_room(room_name: str) -> RuntimeConfig:
    config_path = _session_config_path(room_name)
    if not config_path.exists():
        return RuntimeConfig()

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read runtime config file for room %s", room_name)
        return RuntimeConfig()

    if not isinstance(payload, Mapping):
        logger.warning("Runtime config payload for room %s was not an object", room_name)
        return RuntimeConfig()

    return _runtime_config_from_payload(payload)


def _resolve_runtime_config_for_job(ctx: JobContext) -> RuntimeConfig:
    """Prefer dispatch metadata, fall back to the room-scoped config file."""
    job_metadata = getattr(getattr(ctx, "job", None), "metadata", None)
    metadata_config = _runtime_config_from_metadata(job_metadata)
    if metadata_config is not None:
        logger.info("Loaded runtime config from job metadata")
        return _resolve_runtime_config(metadata_config)

    logger.info("No job metadata runtime config; falling back to room config file")
    return _resolve_runtime_config(_load_runtime_config_for_room(ctx.room.name))


def _runtime_profile_payload(runtime_config: RuntimeConfig) -> dict[str, object]:
    return {
        "scenario_id": runtime_config.scenario_id,
        "channel_id": runtime_config.channel_id,
        "voice_provider": runtime_config.voice_provider,
        "requested_voice_provider": runtime_config.requested_voice_provider,
        "voice_engine": runtime_config.voice_engine,
        "requested_voice_engine": runtime_config.requested_voice_engine,
        "llm_model": runtime_config.llm_model,
        "stt_model": runtime_config.stt_model,
        "tts_model": runtime_config.tts_model,
        "openai_realtime_model": runtime_config.openai_realtime_model,
        "openai_realtime_voice": runtime_config.openai_realtime_voice,
        "openai_realtime_eagerness": runtime_config.openai_realtime_eagerness,
        "google_realtime_model": runtime_config.google_realtime_model,
        "google_realtime_voice": runtime_config.google_realtime_voice,
        "realtime_temperature": runtime_config.realtime_temperature,
        "realtime_enable_affective_dialog": runtime_config.realtime_enable_affective_dialog,
        "realtime_enable_proactivity": runtime_config.realtime_enable_proactivity,
        "preset_id": runtime_config.preset_id,
        "preset_label": runtime_config.preset_label,
        "comparison_label": runtime_config.comparison_label,
        "fallback_reason": runtime_config.fallback_reason,
    }


def _snapshot_payload(session_state: SessionState, *, reason: str) -> dict[str, object]:
    scenario = get_scenario_definition(session_state.scenario_id)
    payload = {
        "type": "session_snapshot",
        "scenario_id": scenario.id,
        "channel_id": session_state.channel_id,
        "reason": reason,
        "timestamp": time.time(),
        "target_e2e_latency_ms": TARGET_E2E_LATENCY_MS,
        "acceptable_e2e_latency_ms": ACCEPTABLE_E2E_LATENCY_MS,
        "turn_count": session_state.turn_count,
        "runtime_profile": session_state.runtime_profile,
        "user_turn_metrics": session_state.user_turn_metrics,
        "assistant_turn_metrics": session_state.assistant_turn_metrics,
    }
    payload.update(scenario.snapshot_builder(session_state))
    return payload


async def _publish_session_snapshot(session_state: SessionState, *, reason: str) -> None:
    if session_state.room is None:
        return

    try:
        await session_state.room.local_participant.publish_data(
            json.dumps(_snapshot_payload(session_state, reason=reason)),
            reliable=True,
            topic=TELEMETRY_TOPIC,
        )
    except Exception:
        logger.exception("Failed to publish session telemetry snapshot")


def _handle_user_state_change(event: UserStateChangedEvent) -> None:
    if event.new_state == "speaking":
        logger.debug("User speech detected")
    elif event.old_state == "speaking" and event.new_state != "speaking":
        logger.debug("User speech ended")
    elif event.new_state == "away":
        logger.debug("User marked away")


def _handle_agent_state_change(event: AgentStateChangedEvent) -> None:
    if event.new_state == "speaking":
        logger.debug("Agent response started")
    elif event.old_state == "speaking" and event.new_state != "speaking":
        logger.debug("Agent response ended")


def _handle_conversation_item(event: ConversationItemAddedEvent) -> None:
    item = event.item
    if not isinstance(item, ChatMessage):
        return

    metrics = item.metrics if isinstance(item.metrics, Mapping) else None

    if item.role == "user":
        logger.debug("User transcript added to conversation")
        if metrics:
            logger.info(
                "User turn latency metrics: transcription_delay=%ss end_of_turn_delay=%ss on_user_turn_completed_delay=%ss",
                _format_metric(metrics.get("transcription_delay")),
                _format_metric(metrics.get("end_of_turn_delay")),
                _format_metric(metrics.get("on_user_turn_completed_delay")),
            )
    elif item.role == "assistant":
        logger.debug("Assistant message added to conversation")
        if metrics:
            logger.info(
                "Assistant turn latency metrics: llm_ttft=%ss tts_ttfb=%ss e2e_latency=%ss started_speaking_at=%ss stopped_speaking_at=%ss",
                _format_metric(metrics.get("llm_node_ttft")),
                _format_metric(metrics.get("tts_node_ttfb")),
                _format_metric(metrics.get("e2e_latency")),
                _format_metric(metrics.get("started_speaking_at")),
                _format_metric(metrics.get("stopped_speaking_at")),
            )


def _format_metric(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"

    return "n/a"


def _metric_value(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _is_realtime_engine(engine: str) -> bool:
    return engine in {
        VOICE_ENGINE_OPENAI_REALTIME,
        VOICE_ENGINE_OPENAI_REALTIME_TEXT,
        VOICE_ENGINE_GEMINI_LIVE,
        VOICE_ENGINE_GEMINI_LIVE_TEXT,
    }


def _is_text_only_realtime_engine(engine: str) -> bool:
    return engine in {
        VOICE_ENGINE_OPENAI_REALTIME_TEXT,
        VOICE_ENGINE_GEMINI_LIVE_TEXT,
    }


def _supports_generate_reply(runtime_config: RuntimeConfig) -> bool:
    # The forked Google realtime plugin (charan632-dev/agents) supports a forced
    # generate_reply() for Gemini 3.1, so every realtime model can greet in its
    # own voice. Previously Gemini 3.1 used a TTS say() fallback, which produced
    # a second voice and a duplicate greeting alongside the model's own.
    return True


def _needs_tts_fallback_for_forced_speech(runtime_config: RuntimeConfig) -> bool:
    # No realtime provider needs a separate TTS voice for forced startup speech
    # anymore; the model speaks the greeting itself via generate_reply().
    return False


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _preload_optional_realtime_plugins() -> None:
    global _OPENAI_REALTIME_PLUGIN, _OPENAI_REALTIME_TURN_DETECTION, _GOOGLE_REALTIME_PLUGIN

    if _has_module("livekit.plugins.openai") and _has_module("openai"):
        try:
            _OPENAI_REALTIME_PLUGIN = importlib.import_module("livekit.plugins.openai")
            realtime_session = importlib.import_module("openai.types.beta.realtime.session")
            _OPENAI_REALTIME_TURN_DETECTION = getattr(realtime_session, "TurnDetection")
        except Exception as exc:
            _OPTIONAL_PLUGIN_IMPORT_ERRORS["openai_realtime"] = exc

    if _has_module("livekit.plugins.google") and _has_module("google.genai"):
        try:
            _GOOGLE_REALTIME_PLUGIN = importlib.import_module("livekit.plugins.google")
        except Exception as exc:
            _OPTIONAL_PLUGIN_IMPORT_ERRORS["gemini_live"] = exc


def _runtime_config_from_env() -> RuntimeConfig:
    requested_provider = VOICE_PROVIDER or VOICE_PROVIDER_CLASSIC
    voice_provider = _normalize_voice_provider(requested_provider)
    preset_id = "classic-pipeline"
    preset_label = "Classic Voice"
    comparison_label = "Deepgram, text reasoning, and Cartesia speech"

    if voice_provider == VOICE_PROVIDER_OPENAI_REALTIME:
        preset_id = "openai-realtime-voice"
        preset_label = "OpenAI Realtime"
        comparison_label = "Native OpenAI speech to speech"
    elif voice_provider == VOICE_PROVIDER_GEMINI_LIVE:
        preset_id = "gemini-live-voice"
        preset_label = "Gemini Live"
        comparison_label = "Native Gemini speech to speech"

    return RuntimeConfig(
        scenario_id=SCENARIO_ID,
        channel_id=CHANNEL_ID,
        voice_provider=voice_provider,
        voice_engine=_voice_engine_for_provider(voice_provider),
        llm_model=LLM_MODEL,
        stt_model=STT_MODEL,
        stt_language=STT_LANGUAGE,
        tts_model=TTS_MODEL,
        openai_realtime_model=OPENAI_REALTIME_MODEL,
        openai_realtime_voice=OPENAI_REALTIME_VOICE,
        openai_realtime_eagerness=OPENAI_REALTIME_EAGERNESS,
        google_realtime_model=GOOGLE_REALTIME_MODEL,
        google_realtime_voice=GOOGLE_REALTIME_VOICE,
        realtime_temperature=REALTIME_TEMPERATURE,
        realtime_enable_affective_dialog=REALTIME_ENABLE_AFFECTIVE_DIALOG,
        realtime_enable_proactivity=REALTIME_ENABLE_PROACTIVITY,
        preset_id=preset_id,
        preset_label=preset_label,
        comparison_label=comparison_label,
        requested_voice_provider=requested_provider,
        requested_voice_engine=os.getenv("VOICE_ENGINE", "").strip().lower() or None,
    )


def _validate_runtime_config(runtime_config: RuntimeConfig) -> None:
    if runtime_config.scenario_id not in SCENARIO_REGISTRY:
        raise RuntimeError(
            f"Unsupported SCENARIO_ID `{runtime_config.scenario_id}`. "
            f"Expected one of: {', '.join(sorted(SCENARIO_REGISTRY))}."
        )
    if runtime_config.channel_id not in CHANNEL_REGISTRY:
        raise RuntimeError(
            f"Unsupported CHANNEL_ID `{runtime_config.channel_id}`. "
            f"Expected one of: {', '.join(sorted(CHANNEL_REGISTRY))}."
        )

    if runtime_config.voice_provider not in SUPPORTED_VOICE_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_VOICE_PROVIDERS))
        raise RuntimeError(
            f"Unsupported VOICE_PROVIDER `{runtime_config.requested_voice_provider or runtime_config.voice_provider}`. "
            f"Supported values: {supported}."
        )

    missing_env: list[str] = []
    for env_name, env_value in (
        ("LIVEKIT_URL", LIVEKIT_URL),
        ("LIVEKIT_API_KEY", LIVEKIT_API_KEY),
        ("LIVEKIT_API_SECRET", LIVEKIT_API_SECRET),
    ):
        if not env_value.strip():
            missing_env.append(env_name)

    if runtime_config.voice_provider == VOICE_PROVIDER_OPENAI_REALTIME:
        if not OPENAI_API_KEY.strip():
            missing_env.append("OPENAI_API_KEY")
        missing_modules: list[str] = []
        if not _has_module("livekit.plugins.openai"):
            missing_modules.append("livekit.plugins.openai")
        if not _has_module("openai"):
            missing_modules.append("openai")
        if missing_modules:
            raise RuntimeError(
                "OpenAI Realtime mode requires the LiveKit OpenAI plugin packages. "
                f"Missing modules: {', '.join(missing_modules)}."
            )
    elif runtime_config.voice_provider == VOICE_PROVIDER_GEMINI_LIVE:
        if not GOOGLE_API_KEY.strip():
            missing_env.append("GOOGLE_API_KEY")
        missing_modules = []
        if not _has_module("livekit.plugins.google"):
            missing_modules.append("livekit.plugins.google")
        if not _has_module("google.genai"):
            missing_modules.append("google.genai")
        if missing_modules:
            raise RuntimeError(
                "Gemini Live mode requires the LiveKit Google plugin packages. "
                f"Missing modules: {', '.join(missing_modules)}."
            )

    if missing_env:
        raise RuntimeError(
            "Missing required environment variables for the agent runtime: "
            + ", ".join(missing_env)
        )


def _log_provider_startup(runtime_config: RuntimeConfig) -> None:
    logger.info("Scenario: %s", runtime_config.scenario_id)
    logger.info("Channel: %s", runtime_config.channel_id)
    logger.info("Voice provider: %s", runtime_config.voice_provider)
    if runtime_config.voice_provider == VOICE_PROVIDER_OPENAI_REALTIME:
        logger.info("OpenAI Realtime model: %s", runtime_config.openai_realtime_model)
        logger.info("OpenAI Realtime voice: %s", runtime_config.openai_realtime_voice)
        logger.info(
            "OpenAI Realtime mode active: STT/LLM/TTS are handled by the realtime model, so classic per-stage latency metrics are not emitted."
        )
    elif runtime_config.voice_provider == VOICE_PROVIDER_GEMINI_LIVE:
        logger.info("Gemini Live model: %s", runtime_config.google_realtime_model)
        logger.info("Gemini Live voice: %s", runtime_config.google_realtime_voice)
        logger.info(
            "Gemini Live mode active: speech recognition, reasoning, and speech synthesis stay on the realtime model."
        )


def _resolve_runtime_config(runtime_config: RuntimeConfig) -> RuntimeConfig:
    resolved = RuntimeConfig(**asdict(runtime_config))
    if resolved.scenario_id not in SCENARIO_REGISTRY:
        logger.warning(
            "Unsupported scenario `%s`. Falling back to `%s`.",
            resolved.scenario_id,
            DEFAULT_SCENARIO_ID,
        )
        resolved.scenario_id = DEFAULT_SCENARIO_ID
    if resolved.channel_id not in CHANNEL_REGISTRY:
        logger.warning(
            "Unsupported channel `%s`. Falling back to `%s`.",
            resolved.channel_id,
            DEFAULT_CHANNEL_ID,
        )
        resolved.channel_id = DEFAULT_CHANNEL_ID
    resolved.requested_voice_provider = runtime_config.voice_provider
    resolved.requested_voice_engine = runtime_config.voice_engine

    if resolved.voice_engine not in SUPPORTED_VOICE_ENGINES:
        resolved.voice_provider = VOICE_PROVIDER_CLASSIC
        resolved.voice_engine = VOICE_ENGINE_PIPELINE
        resolved.fallback_reason = (
            f"Unsupported voice engine `{runtime_config.voice_engine}`. Falling back to the classic pipeline."
        )
        return resolved

    if resolved.voice_engine.startswith("openai_realtime"):
        missing_modules: list[str] = []
        if not _has_module("livekit.plugins.openai"):
            missing_modules.append("livekit.plugins.openai")
        if not _has_module("openai"):
            missing_modules.append("openai")

        if missing_modules:
            resolved.voice_provider = VOICE_PROVIDER_CLASSIC
            resolved.voice_engine = VOICE_ENGINE_PIPELINE
            resolved.fallback_reason = (
                "OpenAI realtime dependencies are missing "
                f"({', '.join(missing_modules)}). Falling back to the classic pipeline."
            )
            if resolved.preset_label:
                resolved.preset_label = f"{resolved.preset_label} (fallback)"
            return resolved

    if resolved.voice_engine.startswith("gemini_live"):
        missing_modules = []
        if not _has_module("livekit.plugins.google"):
            missing_modules.append("livekit.plugins.google")
        if not _has_module("google.genai"):
            missing_modules.append("google.genai")

        if missing_modules:
            resolved.voice_provider = VOICE_PROVIDER_CLASSIC
            resolved.voice_engine = VOICE_ENGINE_PIPELINE
            resolved.fallback_reason = (
                "Google Live dependencies are missing "
                f"({', '.join(missing_modules)}). Falling back to the classic pipeline."
            )
            if resolved.preset_label:
                resolved.preset_label = f"{resolved.preset_label} (fallback)"
            return resolved

    return resolved


def _build_pipeline_llm(runtime_config: RuntimeConfig) -> Any:
    return inference.LLM(model=runtime_config.llm_model)


def _build_openai_realtime_llm(runtime_config: RuntimeConfig, *, text_only: bool) -> Any:
    if _OPENAI_REALTIME_PLUGIN is None or _OPENAI_REALTIME_TURN_DETECTION is None:
        exc = _OPTIONAL_PLUGIN_IMPORT_ERRORS.get("openai_realtime")
        raise RuntimeError(
            "VOICE_ENGINE uses OpenAI Realtime, but the OpenAI plugin is not installed. "
            "Install `livekit-agents[openai]~=1.5` and set OPENAI_API_KEY."
        ) from exc

    kwargs: dict[str, Any] = {
        "model": runtime_config.openai_realtime_model,
        "temperature": runtime_config.realtime_temperature,
        "turn_detection": _OPENAI_REALTIME_TURN_DETECTION(
            type="semantic_vad",
            eagerness=runtime_config.openai_realtime_eagerness,
            create_response=True,
            interrupt_response=True,
        ),
    }

    if text_only:
        kwargs["modalities"] = ["text"]
    else:
        kwargs["voice"] = runtime_config.openai_realtime_voice

    return _OPENAI_REALTIME_PLUGIN.realtime.RealtimeModel(**kwargs)


def _build_gemini_realtime_llm(runtime_config: RuntimeConfig, *, text_only: bool) -> Any:
    if _GOOGLE_REALTIME_PLUGIN is None:
        exc = _OPTIONAL_PLUGIN_IMPORT_ERRORS.get("gemini_live")
        raise RuntimeError(
            "VOICE_ENGINE uses Gemini Live, but the Google plugin is not installed. "
            "Install `livekit-agents[google]~=1.5` and set GOOGLE_API_KEY."
        ) from exc

    kwargs: dict[str, Any] = {
        "model": runtime_config.google_realtime_model,
        "temperature": runtime_config.realtime_temperature,
    }

    is_gemini_31 = runtime_config.google_realtime_model.lower().startswith("gemini-3.1")

    if text_only:
        try:
            from google.genai.types import Modality
        except ImportError as exc:
            raise RuntimeError(
                "Gemini Live text-only mode requires the Google GenAI SDK that ships with "
                "`livekit-agents[google]~=1.5`."
            ) from exc
        kwargs["modalities"] = [Modality.TEXT]
    else:
        kwargs["voice"] = runtime_config.google_realtime_voice

    if not is_gemini_31:
        kwargs["enable_affective_dialog"] = runtime_config.realtime_enable_affective_dialog
        kwargs["proactivity"] = runtime_config.realtime_enable_proactivity
    elif (
        runtime_config.realtime_enable_affective_dialog
        or runtime_config.realtime_enable_proactivity
    ):
        logger.warning(
            "Gemini 3.1 does not support affective dialog or proactivity; those flags were ignored."
        )

    return _GOOGLE_REALTIME_PLUGIN.realtime.RealtimeModel(**kwargs)


def _build_llm_for_engine(runtime_config: RuntimeConfig) -> Any:
    engine = runtime_config.voice_engine
    if engine == VOICE_ENGINE_PIPELINE:
        return _build_pipeline_llm(runtime_config)
    if engine == VOICE_ENGINE_OPENAI_REALTIME:
        return _build_openai_realtime_llm(runtime_config, text_only=False)
    if engine == VOICE_ENGINE_OPENAI_REALTIME_TEXT:
        return _build_openai_realtime_llm(runtime_config, text_only=True)
    if engine == VOICE_ENGINE_GEMINI_LIVE:
        return _build_gemini_realtime_llm(runtime_config, text_only=False)
    if engine == VOICE_ENGINE_GEMINI_LIVE_TEXT:
        return _build_gemini_realtime_llm(runtime_config, text_only=True)

    raise RuntimeError(
        f"Unsupported VOICE_ENGINE `{engine}`. Expected one of: {', '.join(sorted(SUPPORTED_VOICE_ENGINES))}."
    )


def _build_pipeline_session(
    ctx: JobContext,
    runtime_config: RuntimeConfig,
) -> AgentSession[SessionState]:
    return AgentSession(
        stt=inference.STT(
            model=runtime_config.stt_model,
            language=runtime_config.stt_language,
        ),
        tts=inference.TTS(
            model=runtime_config.tts_model,
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            extra_kwargs={"speed": TTS_SPEED},
        ),
        vad=ctx.proc.userdata["vad"],
        turn_handling={
            "turn_detection": MultilingualModel(),
            "endpointing": {
                "min_delay": 0.2,
                "max_delay": 0.7,
            },
            "interruption": {
                "enabled": True,
                "min_duration": 0.2,
                "false_interruption_timeout": 0.6,
                "backchannel_boundary": (0.4, 0.4),
            },
            "preemptive_generation": {
                "enabled": True,
                "preemptive_tts": True,
            },
        },
        user_away_timeout=USER_AWAY_TIMEOUT_SECONDS,
        aec_warmup_duration=0.8,
        userdata=SessionState(),
    )


def _build_realtime_session(
    runtime_config: RuntimeConfig,
    *,
    text_only: bool,
) -> AgentSession[SessionState]:
    kwargs: dict[str, Any] = {
        "user_away_timeout": USER_AWAY_TIMEOUT_SECONDS,
        "aec_warmup_duration": 0.8,
        "userdata": SessionState(),
    }

    if text_only or _needs_tts_fallback_for_forced_speech(runtime_config):
        kwargs["tts"] = inference.TTS(
            model=runtime_config.tts_model,
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            extra_kwargs={"speed": TTS_SPEED},
        )

    return AgentSession(**kwargs)


def _build_session_for_engine(
    ctx: JobContext,
    runtime_config: RuntimeConfig,
) -> AgentSession[SessionState]:
    engine = runtime_config.voice_engine
    if engine == VOICE_ENGINE_PIPELINE:
        return _build_pipeline_session(ctx, runtime_config)
    if engine == VOICE_ENGINE_OPENAI_REALTIME:
        return _build_realtime_session(runtime_config, text_only=False)
    if engine == VOICE_ENGINE_OPENAI_REALTIME_TEXT:
        return _build_realtime_session(runtime_config, text_only=True)
    if engine == VOICE_ENGINE_GEMINI_LIVE:
        return _build_realtime_session(runtime_config, text_only=False)
    if engine == VOICE_ENGINE_GEMINI_LIVE_TEXT:
        return _build_realtime_session(runtime_config, text_only=True)

    raise RuntimeError(
        f"Unsupported VOICE_ENGINE `{engine}`. Expected one of: {', '.join(sorted(SUPPORTED_VOICE_ENGINES))}."
    )


def build_classic_session(
    ctx: JobContext,
    runtime_config: RuntimeConfig,
) -> AgentSession[SessionState]:
    return _build_pipeline_session(ctx, runtime_config)


def build_openai_realtime_session(runtime_config: RuntimeConfig) -> AgentSession[SessionState]:
    return _build_realtime_session(runtime_config, text_only=False)


def _build_llm_for_provider(runtime_config: RuntimeConfig) -> Any:
    if runtime_config.voice_provider == VOICE_PROVIDER_OPENAI_REALTIME:
        return _build_openai_realtime_llm(runtime_config, text_only=False)
    if runtime_config.voice_provider == VOICE_PROVIDER_GEMINI_LIVE:
        return _build_gemini_realtime_llm(runtime_config, text_only=False)
    return _build_pipeline_llm(runtime_config)


def _build_room_options() -> room_io.RoomOptions:
    return room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_S
            ),
        ),
    )


def _log_runtime_profile(runtime_config: RuntimeConfig) -> None:
    engine = runtime_config.voice_engine
    logger.info(
        "Voice runtime profile selected",
        extra={
            "voice_provider": runtime_config.voice_provider,
            "voice_engine": engine,
            "requested_voice_provider": runtime_config.requested_voice_provider,
            "requested_voice_engine": runtime_config.requested_voice_engine,
            "llm_model": runtime_config.llm_model,
            "stt_model": runtime_config.stt_model if engine == VOICE_ENGINE_PIPELINE else None,
            "tts_model": runtime_config.tts_model
            if engine == VOICE_ENGINE_PIPELINE or _is_text_only_realtime_engine(engine)
            else None,
            "openai_realtime_model": runtime_config.openai_realtime_model
            if engine.startswith("openai_realtime")
            else None,
            "google_realtime_model": runtime_config.google_realtime_model
            if engine.startswith("gemini_live")
            else None,
            "preset_id": runtime_config.preset_id,
            "comparison_label": runtime_config.comparison_label,
            "fallback_reason": runtime_config.fallback_reason,
        },
    )


def _trigger_away_prompt(session: AgentSession[SessionState], runtime_config: RuntimeConfig) -> None:
    if runtime_config.voice_provider == VOICE_PROVIDER_CLASSIC or not _supports_generate_reply(
        runtime_config
    ):
        session.say(
            "Are you still there?",
            allow_interruptions=True,
            add_to_chat_ctx=False,
        )
        return

    session.generate_reply(
        instructions=(
            "The user went silent. Ask only one short question: are you still there?"
        ),
    )


def _trigger_initial_greeting(
    session: AgentSession[SessionState],
    runtime_config: RuntimeConfig,
    greeting_text: str,
) -> None:
    if runtime_config.voice_provider == VOICE_PROVIDER_CLASSIC or not _supports_generate_reply(
        runtime_config
    ):
        session.say(
            greeting_text,
            allow_interruptions=True,
            add_to_chat_ctx=True,
        )
        return

    session.generate_reply(
        instructions=(
            "Greet the customer first. Use this exact greeting content naturally and only once: "
            f"{greeting_text}"
        ),
    )


server = AgentServer(num_idle_processes=1)

_preload_optional_realtime_plugins()


def prewarm(proc: JobProcess):
    runtime_config = _resolve_runtime_config(_runtime_config_from_env())
    _validate_runtime_config(runtime_config)
    _log_provider_startup(runtime_config)
    proc.userdata["runtime_config"] = runtime_config
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name=AGENT_NAME)
async def my_agent(ctx: JobContext):
    logger.info(
        "Starting agent session registration",
        extra={
            "agent_name": AGENT_NAME,
            "livekit_url": LIVEKIT_URL,
            "room_name": ctx.room.name,
        },
    )

    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    runtime_config = _resolve_runtime_config_for_job(ctx)
    _validate_runtime_config(runtime_config)
    scenario = get_scenario_definition(runtime_config.scenario_id)
    channel = get_channel_definition(runtime_config.channel_id)
    assistant_llm = _build_llm_for_provider(runtime_config)
    if runtime_config.voice_provider in {
        VOICE_PROVIDER_OPENAI_REALTIME,
        VOICE_PROVIDER_GEMINI_LIVE,
    }:
        session = build_openai_realtime_session(runtime_config)
    else:
        session = build_classic_session(ctx, runtime_config)
    _log_runtime_profile(runtime_config)
    session.userdata.scenario_id = scenario.id
    session.userdata.channel_id = channel.id
    session.userdata.room = ctx.room
    session.userdata.runtime_profile = _runtime_profile_payload(runtime_config)

    away_prompt_state = {"sent": False}

    async def _send_away_prompt() -> None:
        if away_prompt_state["sent"]:
            return

        away_prompt_state["sent"] = True
        logger.info("User idle detected; sending away prompt")
        try:
            _trigger_away_prompt(session, runtime_config)
        except RuntimeError:
            logger.exception("Failed to send away prompt")
            away_prompt_state["sent"] = False

    def _on_user_state_changed(event: UserStateChangedEvent) -> None:
        _handle_user_state_change(event)
        if event.new_state in {"speaking", "listening"}:
            away_prompt_state["sent"] = False
            session.userdata.waiting_for_customer = False
        elif event.new_state == "away":
            asyncio.create_task(_send_away_prompt())

    def _on_agent_state_changed(event: AgentStateChangedEvent) -> None:
        _handle_agent_state_change(event)

    def _on_conversation_item(event: ConversationItemAddedEvent) -> None:
        _handle_conversation_item(event)
        item = event.item
        if not isinstance(item, ChatMessage):
            return

        # Capture the turn for the call transcript (dashboard replay). Best-effort:
        # we only record user/assistant text turns.
        turn_text = (getattr(item, "text_content", "") or "").strip()
        if turn_text and item.role in {"user", "assistant"}:
            session.userdata.transcript.append(
                {"role": item.role, "text": turn_text, "ts": time.time()}
            )

        metrics = item.metrics if isinstance(item.metrics, Mapping) else None

        if item.role == "user":
            session.userdata.turn_count += 1
            if runtime_config.voice_provider == VOICE_PROVIDER_CLASSIC:
                session.userdata.user_turn_metrics = {
                    "transcription_delay": _metric_value(metrics.get("transcription_delay")) if metrics else None,
                    "end_of_turn_delay": _metric_value(metrics.get("end_of_turn_delay")) if metrics else None,
                    "on_user_turn_completed_delay": _metric_value(
                        metrics.get("on_user_turn_completed_delay")
                    )
                    if metrics
                    else None,
                }
            else:
                session.userdata.user_turn_metrics = None
            asyncio.create_task(
                _publish_session_snapshot(session.userdata, reason="user_turn_metrics")
            )
        elif item.role == "assistant":
            if runtime_config.voice_provider == VOICE_PROVIDER_CLASSIC:
                session.userdata.assistant_turn_metrics = {
                    "llm_ttft": _metric_value(metrics.get("llm_node_ttft")) if metrics else None,
                    "tts_ttfb": _metric_value(metrics.get("tts_node_ttfb")) if metrics else None,
                    "e2e_latency": _metric_value(metrics.get("e2e_latency")) if metrics else None,
                    "started_speaking_at": _metric_value(metrics.get("started_speaking_at"))
                    if metrics
                    else None,
                    "stopped_speaking_at": _metric_value(metrics.get("stopped_speaking_at"))
                    if metrics
                    else None,
                }
            else:
                session.userdata.assistant_turn_metrics = None
            assistant_text = getattr(item, "text_content", "") or ""
            session.userdata.assistant_guardrail_violations = audit_assistant_response(
                assistant_text,
                session.userdata.order,
                session.userdata.price_quote,
                session.userdata.mock_order,
            )
            if session.userdata.assistant_guardrail_violations:
                session.userdata.guardrail_violation_count += len(
                    session.userdata.assistant_guardrail_violations
                )
                logger.warning(
                    "Assistant response guardrail violations: %s",
                    " | ".join(session.userdata.assistant_guardrail_violations),
                )
            asyncio.create_task(
                _publish_session_snapshot(session.userdata, reason="assistant_turn_metrics")
            )

    session.on("user_state_changed", _on_user_state_changed)
    session.on("agent_state_changed", _on_agent_state_changed)
    session.on("conversation_item_added", _on_conversation_item)

    # --- Call telemetry (dashboard) ---------------------------------------
    # Open a call record now and finalize it on shutdown. All of this is
    # best-effort: a telemetry failure must never affect the live call.
    call_id = f"call-{uuid4().hex[:12]}"
    call_started_at = time.time()
    session.userdata.call_id = call_id
    session.userdata.call_started_at = call_started_at

    asyncio.create_task(
        asyncio.to_thread(
            open_call,
            call_id=call_id,
            room_name=ctx.room.name,
            scenario=scenario.id,
            channel=channel.id,
            voice_provider=runtime_config.voice_provider,
            llm_model=runtime_config.llm_model,
            language=session.userdata.order.language,
            started_at=call_started_at,
        )
    )

    async def _finalize_call_on_shutdown() -> None:
        userdata = session.userdata
        mock_order = userdata.mock_order
        try:
            await asyncio.to_thread(
                finalize_call,
                call_id=call_id,
                started_at=call_started_at,
                transcript=list(userdata.transcript),
                turn_count=userdata.turn_count,
                order_number=getattr(mock_order, "order_number", None) if mock_order else None,
                order_total=getattr(mock_order, "total", None) if mock_order else None,
                guardrail_violations=userdata.guardrail_violation_count,
                language=userdata.order.language,
            )
        except Exception:
            logger.exception("Failed to finalize call telemetry for %s", call_id)

    ctx.add_shutdown_callback(_finalize_call_on_shutdown)

    # Connect the worker to the assigned room before starting the voice session.
    await ctx.connect()

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=scenario.agent_factory(assistant_llm, channel),
        room=ctx.room,
        room_options=_build_room_options(),
    )
    _trigger_initial_greeting(
        session,
        runtime_config,
        build_initial_greeting(channel),
    )
    await _publish_session_snapshot(session.userdata, reason="session_started")

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = anam.AvatarSession(
    #     persona_config=anam.PersonaConfig(
    #         name="...",
    #         avatarId="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/anam
    #     ),
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)
