# VoixAI Agent Runtime

This app is the Python voice agent runtime for VoixAI.

It joins the same LiveKit room as the browser client, selects the correct voice mode for that room, runs the ordering conversation, and publishes session telemetry back to the frontend.

## What It Does

- loads env defaults and room-scoped runtime config
- supports `classic`, `openai_realtime`, and `gemini_live`
- maintains structured in-memory order state for the current session
- resolves menu items and validates order changes against backend-backed menu tools
- produces priced order quotes before confirmation through the backend pricing path
- exposes order tools to the agent
- publishes transcript/order/latency snapshots on the telemetry topic

## Main File

- [src/agent.py](./src/agent.py)

This file currently contains most of the runtime logic, including:

- runtime config resolution
- provider validation
- classic and realtime session construction
- order-state tools
- telemetry publishing
- session event handling

## Voice Modes

### `classic`

Uses:

- Deepgram STT
- OpenAI text LLM
- Cartesia TTS

This path emits per-stage latency metrics in logs and session telemetry.

### `openai_realtime`

Uses the LiveKit OpenAI realtime plugin.

This path does not emit classic STT/LLM/TTS stage metrics because the realtime model handles the combined voice stack.

### `gemini_live`

Uses the LiveKit Google realtime plugin.

Current default model:

- `gemini-3.1-flash-live-preview`

Important note:

- Gemini 3.1 has limited mid-session update support, so instructions/context/tool changes may not apply until the next session.
- The runtime avoids `generate_reply(...)` for Gemini 3.1 greeting and away-prompt turns because that model path is not compatible with forced `generate_reply` calls.
- Gemini 3.1 sessions attach a small TTS fallback so those forced greeting and away-prompt turns can still use `say(...)` safely.
- The Google realtime plugin is pinned from `charan632-dev/agents` instead of the stock PyPI plugin while this Gemini Live fix path is in use.

## Runtime Config Resolution

Runtime config comes from two places:

1. env defaults
2. room-scoped config written by `apps/api`

The final runtime profile is resolved when a room job starts. That means worker startup logs alone are not enough to tell you what mode a specific user session is actually using. The authoritative session-level log is:

- `Voice runtime profile selected`

## Telemetry

The runtime publishes structured session snapshots to the room on:

- `voixai.telemetry`

These snapshots include:

- order state
- price quote state
- mock order state
- runtime profile
- turn count
- classic latency metrics when available
- assistant guardrail violations when detected

The frontend consumes those snapshots to drive:

- transcript UI
- order summary
- confirmation screen
- developer details

## Environment

Primary env variables:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `AGENT_NAME`
- `VOICE_PROVIDER`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`

Mode-specific settings:

- `OPENAI_REALTIME_MODEL`
- `OPENAI_REALTIME_VOICE`
- `OPENAI_REALTIME_EAGERNESS`
- `GOOGLE_REALTIME_MODEL`
- `GOOGLE_REALTIME_VOICE`
- `REALTIME_TEMPERATURE`
- `REALTIME_ENABLE_AFFECTIVE_DIALOG`
- `REALTIME_ENABLE_PROACTIVITY`

See:

- [../../docs/ENVIRONMENT_VARIABLES.md](../../docs/ENVIRONMENT_VARIABLES.md)

## Local Run

```powershell
cd apps/agent-runtime
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -e ../../packages/ordering
python src/agent.py download-files
python src/agent.py dev
```

> Menu, pricing, validation, order state, and the order state machine live in
> the shared `packages/ordering` package (the single source of truth, also used
> by `apps/api`). `src/scenarios/wingstop.py` is now just the agent prompt,
> tools, and telemetry over that domain.

## Testing

Current focused runtime tests live in:

- [tests/test_order_state.py](./tests/test_order_state.py)

Typical command:

```powershell
apps\agent-runtime\.venv\Scripts\python.exe -m pytest apps\agent-runtime\tests\test_order_state.py -q
```

## Current Notes

- away prompts now use a realtime-safe path for Gemini/OpenAI sessions
- Gemini 3.1 greeting-first behavior relies on a TTS-backed fallback path for forced startup speech
- fresh room-per-order behavior is handled by the frontend, not by this runtime
- order state is in memory only and resets when the session ends
- the current restaurant is `Voix Wings Demo`, not an official Wingstop menu
- pricing and menu availability are still demo data and should be replaced by a real POS-backed source in production
