# VoixAI Web App

This app is the customer-facing frontend for the VoixAI voice AI system.

It is built with Next.js, React, Tailwind CSS, and LiveKit React components.

## What It Does

- renders the landing screen
- lets the user choose a voice mode before starting
- frames the current live scenario
- requests a token from `apps/api`
- joins the LiveKit room
- renders the live transcript
- renders the voice activity stage
- renders the current scenario workspace and confirmation screen
- shows developer details only behind a disclosure

## Main Frontend Flow

1. User lands on the start screen.
2. User chooses a voice mode if desired.
3. User starts a voice order.
4. The app posts `runtime_config` to `POST /api/livekit/token`.
5. The frontend joins the LiveKit room with the returned token.
6. The Python runtime publishes telemetry snapshots.
7. The frontend renders transcript, voice state, and the active scenario workspace from that session state.

## Important Current Behavior

### Fresh room per new order

Each new order gets a fresh room name derived from the base room name.

This prevents stale room-scoped runtime config from affecting the next session when the user ends an order and starts another one in a different mode.

### Default voice mode can follow env

The frontend no longer always boots in Classic Voice.

The initial mode can come from:

- `NEXT_PUBLIC_DEFAULT_VOICE_MODE`
- or server-side `VOICE_PROVIDER` / `VOICE_ENGINE`

### Realtime voice stage

The live session UI includes:

- a stateful assistant stage
- voice activity visualization
- transcript timeline
- order summary panel
- text fallback composer

### Current scenario

The current live scenario is:

- `Wingstop inbound ordering`

VoixAI should be understood as the reusable system, with this Wingstop flow acting as the first packaged scenario.

## Key Files

- [components/app/app.tsx](./components/app/app.tsx)
- [components/app/view-controller.tsx](./components/app/view-controller.tsx)
- [components/app/session-layout.tsx](./components/app/session-layout.tsx)
- [components/app/landing-hero.tsx](./components/app/landing-hero.tsx)
- [components/app/voice-visualizer.tsx](./components/app/voice-visualizer.tsx)
- [lib/runtime-config.ts](./lib/runtime-config.ts)
- [hooks/useSessionTelemetry.ts](./hooks/useSessionTelemetry.ts)

## Voice Modes

Supported user-facing modes:

- `Classic Voice`
- `OpenAI Realtime`
- `Gemini Live`

These map to runtime payloads built in:

- [lib/runtime-config.ts](./lib/runtime-config.ts)

## Environment

Important env variables:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_LIVEKIT_ROOM_NAME`
- `NEXT_PUBLIC_PARTICIPANT_NAME`
- `NEXT_PUBLIC_AGENT_NAME`
- `NEXT_PUBLIC_DEFAULT_VOICE_MODE`

See:

- [../../docs/ENVIRONMENT_VARIABLES.md](../../docs/ENVIRONMENT_VARIABLES.md)

## Local Run

```powershell
cd apps/web
corepack pnpm install
corepack pnpm dev
```

Open:

- `http://localhost:3000`

## Verification

Useful commands:

```powershell
corepack pnpm exec tsc --noEmit
corepack pnpm exec next build --no-lint
```

## Current Notes

- the local `app/api/token/route.ts` route is intentionally not used in the current setup
- the browser still talks to LiveKit through the API service, not directly to OpenAI or Google
- developer/debug details are intentionally hidden from the default customer-facing UI
