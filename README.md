# VoixAI

VoixAI is a voice AI system built around a LiveKit room, a Python voice agent, and a customer-facing Next.js frontend.

The project currently supports three voice paths:

- `classic`: Deepgram STT + OpenAI text LLM + Cartesia TTS
- `openai_realtime`: native OpenAI speech-to-speech through the LiveKit realtime plugin
- `gemini_live`: native Gemini Live speech-to-speech through the LiveKit Google plugin

The current live use case is:

- `Wingstop inbound ordering`

## Repo Structure

```text
VoixAI/
  apps/
    web/              Next.js customer-facing voice UI
    api/              FastAPI token + session-config service
    agent-runtime/    Python LiveKit voice agent runtime
  docker/
  docs/
  packages/
  scripts/
```

## Architecture

The current end-to-end flow is:

1. The browser selects a voice mode in `apps/web`.
2. The frontend posts `runtime_config` to `POST /api/livekit/token`.
3. `apps/api` writes room-scoped config into `.voixai/session-configs/<room>.json`.
4. The API returns a LiveKit participant token and dispatches the configured agent.
5. The browser joins the LiveKit room.
6. `apps/agent-runtime` loads the room config and starts the correct voice session type.
7. The runtime publishes structured telemetry back into the room.
8. The frontend renders transcript, voice state, order summary, and confirmation UI from that session state.

## Key Current Behaviors

- The current Wingstop scenario uses a structured demo menu, structured order state, backend-backed validation/pricing, and confirmation-gated mock order creation.
- Menu resolution, validation, and pricing come from shared deterministic ordering logic instead of prompt-only menu text.
- Restarting an order uses a fresh room so stale runtime config does not leak across sessions.
- Gemini/OpenAI realtime idle prompts are handled safely in the runtime.

## Reliability Test Suite

VoixAI includes a deterministic scenario suite for the Wingstop ordering flow. It covers happy paths, messy corrections, cancellations, invalid modifiers, ambiguous phrasing, bilingual turns, pricing/repricing, confirmation gates, and stale-state behavior without requiring Gemini Live, LiveKit rooms, audio, or API keys.

The suite now includes both generated seed cases and grouped transcript-derived regressions from real failed ordering calls.

Run it with:

```powershell
cd apps/agent-runtime
.venv\Scripts\python.exe -m pytest tests/reliability -q
```

The suite writes a JSON report to `apps/agent-runtime/tests/reliability/reports/reliability_report.json` and is documented in [docs/RELIABILITY_TESTING.md](./docs/RELIABILITY_TESTING.md).

## Quick Start

See:

- [docs/LOCAL_SETUP.md](./docs/LOCAL_SETUP.md)
- [docs/ENVIRONMENT_VARIABLES.md](./docs/ENVIRONMENT_VARIABLES.md)

Short version:

1. Copy `.env.example` to `.env`.
2. Add at least one provider key.
3. Run `docker compose up --build`.
4. Open `http://localhost:3000`.

## Important Docs

- [docs/README.md](./docs/README.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- [docs/RELIABILITY_TESTING.md](./docs/RELIABILITY_TESTING.md)
- [docs/LOCAL_SETUP.md](./docs/LOCAL_SETUP.md)
- [docs/ENVIRONMENT_VARIABLES.md](./docs/ENVIRONMENT_VARIABLES.md)
- [docs/MOCK_MENU.md](./docs/MOCK_MENU.md)
- [docs/PRODUCTION_READINESS.md](./docs/PRODUCTION_READINESS.md)
- [docs/direction.md](./docs/direction.md)
