# Architecture

## Overview

VoixAI is a three-app system built around a LiveKit room:

- `apps/web`: customer-facing Next.js voice-ordering UI
- `apps/api`: FastAPI token and room-runtime-config service
- `apps/agent-runtime`: Python LiveKit voice agent runtime

The browser never talks directly to OpenAI or Google realtime APIs. It always joins a LiveKit room using a token minted by `apps/api`, and the Python runtime handles the actual classic or realtime voice path.

## End-to-End Flow

1. The user opens `apps/web`.
2. The frontend chooses an initial runtime preset from:
   - `NEXT_PUBLIC_DEFAULT_VOICE_MODE`
   - or server-side `VOICE_PROVIDER` / `VOICE_ENGINE`
3. The user starts a voice order.
4. The frontend sends `room_name`, `participant_name`, and `runtime_config` to `POST /api/livekit/token`.
5. `apps/api`:
   - persists the requested room-scoped runtime config under `.voixai/session-configs`
   - mints a LiveKit participant token
   - dispatches the configured agent name into the room
6. The browser joins the LiveKit room.
7. `apps/agent-runtime` receives the room job and resolves the final runtime config for that room.
8. The runtime starts one of:
   - classic pipeline session
   - OpenAI Realtime session
   - Gemini Live session
9. The runtime publishes structured telemetry snapshots back into the room.
10. The frontend consumes that telemetry and renders:
    - assistant stage
    - transcript
    - order summary
    - confirmation screen

## Runtime Mode Resolution

The final session mode is not determined only by worker startup env.

Current precedence:

1. frontend-selected `runtime_config`
2. room-scoped config written by `apps/api`
3. worker env defaults

The most trustworthy session-level runtime log is:

- `Voice runtime profile selected`

Worker startup logs like `Voice provider: openai_realtime` are useful, but they reflect default runtime availability and prewarm behavior rather than the exact mode chosen for a specific browser session.

## Apps

### `apps/web`

Primary responsibilities:

- landing and mode selection
- session start/end
- transcript and live voice UI
- order summary and confirmation UI
- hidden developer details

Key files:

- `apps/web/components/app/app.tsx`
- `apps/web/components/app/view-controller.tsx`
- `apps/web/components/app/session-layout.tsx`
- `apps/web/components/app/voice-visualizer.tsx`
- `apps/web/lib/runtime-config.ts`
- `apps/web/hooks/useSessionTelemetry.ts`
- `apps/web/hooks/useVoicePresenceState.ts`

Important behavior:

- each new order uses a fresh room suffix
- this prevents stale room config from breaking restart behavior across modes

### `apps/api`

Primary responsibilities:

- `GET /health`
- `POST /api/livekit/token`
- room-config persistence
- agent dispatch token minting

Key file:

- `apps/api/main.py`

Important behavior:

- writes requested runtime config into `.voixai/session-configs/<room>.json`
- does not talk to OpenAI or Google directly

### `apps/agent-runtime`

Primary responsibilities:

- runtime config resolution and validation
- classic/OpenAI/Gemini session construction
- order-state tools
- telemetry publishing
- session event handling

Key file:

- `apps/agent-runtime/src/agent.py`

Important behavior:

- supports `classic`, `openai_realtime`, and `gemini_live`
- publishes telemetry on `voixai.telemetry`
- uses a realtime-safe away-prompt path for Gemini/OpenAI sessions

## Voice Modes

### Classic

Pipeline:

- Deepgram STT
- OpenAI text LLM
- Cartesia TTS

Observability:

- emits classic stage metrics

### OpenAI Realtime

Pipeline:

- LiveKit OpenAI realtime plugin

Observability:

- does not emit separate classic STT/LLM/TTS stage metrics

### Gemini Live

Pipeline:

- LiveKit Google realtime plugin

Observability:

- does not emit separate classic STT/LLM/TTS stage metrics

Important note:

- Gemini 3.1 has limited mid-session update support, so some instruction/context/tool updates may not apply until the next session

## Telemetry Contract

The runtime publishes structured session snapshots that include:

- order state
- mock order state
- runtime profile
- turn count
- user turn metrics when available
- assistant turn metrics when available

The frontend uses those snapshots to power the product UI instead of relying only on freeform transcript parsing.

## Current Limitations

- order state is in memory only
- room-scoped runtime config is file-based local persistence
- integration coverage is still lighter than unit/build coverage
- the runtime logic is still concentrated in a single large Python module

## Source of Truth

If you need the fastest trustworthy implementation references:

- architecture and current flow: this file
- runtime behavior: `apps/agent-runtime/src/agent.py`
- API behavior: `apps/api/main.py`
- frontend runtime payloads: `apps/web/lib/runtime-config.ts`
- frontend session orchestration: `apps/web/components/app/app.tsx`
