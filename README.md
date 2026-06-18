# VoixAI

VoixAI is a core voice AI system built around a LiveKit room, a Python voice agent, and a customer-facing Next.js frontend.

The project currently supports three voice paths:

- `classic`: Deepgram STT + OpenAI text LLM + Cartesia TTS
- `openai_realtime`: native OpenAI speech-to-speech through the LiveKit realtime plugin
- `gemini_live`: native Gemini Live speech-to-speech through the LiveKit Google plugin

The current live use case is:

- `Wingstop inbound ordering`

This repo is still an MVP, but it now includes:

- a production-leaning voice AI session UI
- room-scoped runtime mode selection
- session telemetry for transcript and order summary updates
- fresh-room-per-order behavior so restarting an order does not reuse stale runtime config

## Repo Structure

```text
VoixAI/
  apps/
    web/              Next.js customer-facing voice UI
    api/              FastAPI token + session-config service
    agent-runtime/    Python LiveKit voice agent runtime
  docs/
    README.md
    ARCHITECTURE.md
    LOCAL_SETUP.md
    ENVIRONMENT_VARIABLES.md
    MOCK_MENU.md
    PRODUCTION_READINESS.md
    direction.md
  README.md
```

## Architecture

The current end-to-end flow is:

1. The browser selects a voice mode in `apps/web`.
2. The frontend posts `runtime_config` to `POST /api/livekit/token`.
3. `apps/api` writes the room-specific config into `.voixai/session-configs/<room>.json`.
4. The API returns a LiveKit participant token and dispatches the configured agent.
5. The browser joins the LiveKit room.
6. `apps/agent-runtime` receives the job, loads the room-specific runtime config, validates it, and starts the correct voice session type.
7. The runtime publishes structured session telemetry back into the room.
8. The frontend renders transcript, voice state, order summary, and confirmation UI from that session state.

The system should be understood as:

- `VoixAI` = the reusable platform
- `Wingstop inbound ordering` = the current active scenario

## Apps

### `apps/web`

Next.js 15 + React 19 frontend.

Primary responsibilities:

- landing page and voice mode selection
- start and end voice sessions
- transcript rendering
- voice activity visualization
- scenario workspace rendering
- confirmation screen
- hidden developer details panel

### `apps/api`

FastAPI service.

Primary responsibilities:

- `GET /health`
- `POST /api/livekit/token`
- backend menu lookup, order validation, and pricing endpoints for the Wingstop scenario
- persist room-scoped runtime config
- mint browser participant tokens
- dispatch the Python agent into the room

### `apps/agent-runtime`

Python LiveKit agent runtime.

Primary responsibilities:

- load env defaults
- load room-specific runtime config
- choose classic/OpenAI/Gemini runtime path
- maintain the current scenario state
- publish session telemetry
- expose order-management tools to the agent

## Voice Modes

### Classic

Uses:

- Deepgram STT
- OpenAI text model
- Cartesia TTS

This path emits classic per-stage latency metrics.

### OpenAI Realtime

Uses the LiveKit OpenAI realtime plugin. STT, reasoning, and speech are handled by the realtime model rather than separate pipeline stages.

### Gemini Live

Uses the LiveKit Google realtime plugin. Current default model is:

- `gemini-3.1-flash-live-preview`

Current runtime note:

- Gemini 3.1 greets in its own voice via native `generate_reply(...)`. This requires the `charan632-dev/agents` Google plugin fork, which adds forced-`generate_reply` support for Gemini 3.1. The previous TTS `say(...)` fallback was removed because it produced a second voice and a duplicate greeting alongside the model's own.
- The agent runtime dependency is pinned to the `charan632-dev/agents` Google plugin fork — install it into the runtime venv (see docs/LOCAL_SETUP.md) and verify with `pip show`/`direct_url.json`, since a stray stock PyPI install reintroduces the duplicate-greeting bug.

## Key Current Behaviors

- The frontend default voice mode can follow env instead of always booting in classic mode.
- Each new order now starts in a fresh room name, which prevents stale session config from breaking restart behavior.
- Realtime away prompts are handled safely in the runtime so Gemini/OpenAI sessions do not crash on idle prompts.
- Developer-facing metrics and internals are hidden behind a disclosure in the UI instead of shown by default.
- The current product framing is platform-first: VoixAI is the system, and Wingstop inbound ordering is the current live scenario.
- The current Wingstop scenario now uses a structured demo menu, structured order state, confirmation-gated mock order creation, and bilingual English/Spanish ordering behavior.
- Menu resolution, order validation, and pricing for the Wingstop scenario now come from backend-backed tools instead of relying only on prompt-embedded menu text.

## Quick Start

See:

- [docs/LOCAL_SETUP.md](./docs/LOCAL_SETUP.md)
- [docs/ENVIRONMENT_VARIABLES.md](./docs/ENVIRONMENT_VARIABLES.md)

Short version:

1. Copy env files.
2. Start `apps/api`.
3. Start `apps/agent-runtime`.
4. Start `apps/web`.
5. Open `http://localhost:3000`.

## Important Docs

- [docs/README.md](./docs/README.md) — docs index and what each surviving doc is for
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) — accurate current-state system design
- [docs/PRODUCTION_READINESS.md](./docs/PRODUCTION_READINESS.md) — gap analysis, target architecture, and remediation roadmap
- [docs/direction.md](./docs/direction.md) — long-term platform vision
- [docs/LOCAL_SETUP.md](./docs/LOCAL_SETUP.md)
- [docs/ENVIRONMENT_VARIABLES.md](./docs/ENVIRONMENT_VARIABLES.md)
- [docs/MOCK_MENU.md](./docs/MOCK_MENU.md)

## Current Limitations

- Order state is still in memory only.
- Room runtime config is stored in local files under `.voixai/session-configs`.
- There is no persistent database, payment flow, POS integration, or telephony layer yet.
- End-to-end automated coverage is still light across service boundaries.

## Docs Policy

`docs/` is now intentionally small. The live docs are limited to setup, environment,
current architecture, production roadmap, long-term direction, and the active
scenario reference.
