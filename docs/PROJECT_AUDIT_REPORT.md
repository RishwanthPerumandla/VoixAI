# VoixAI Project Audit Report

Last updated: 2026-06-11

## Purpose

This document is a current-state audit of the `VoixAI` repository. It is meant to be the fastest accurate orientation document for the project after the recent voice-mode, session-lifecycle, and UI refactors.

It covers:

- What the project is
- How the system is structured
- What is implemented today
- What documentation is stale
- Known risks and current findings
- Recommended next steps

## Executive Summary

VoixAI is a multi-service voice ordering demo built around a LiveKit room:

- `apps/web` is a Next.js voice-ordering UI
- `apps/api` mints LiveKit tokens and persists per-room runtime config
- `apps/agent-runtime` is the Python voice agent that runs either:
  - the classic STT -> LLM -> TTS pipeline
  - OpenAI Realtime speech-to-speech
  - Gemini Live speech-to-speech

The product direction has moved well beyond the original starter templates. The codebase now supports mode switching, per-session runtime selection, live order summaries, transcript rendering, and customer-facing voice UI. However, the repository documentation has not kept pace with the implementation. The current top-level and app-level READMEs are partially stale, and two app READMEs still largely reflect upstream LiveKit starter templates rather than the real VoixAI product.

## Current Architecture

### Services

#### `apps/web`

Frontend voice-ordering application built with:

- Next.js 15
- React 19
- Tailwind CSS 4
- LiveKit React components
- motion
- Radix UI primitives

Primary responsibilities:

- start/end the browser voice session
- let the user choose voice mode before session start
- request a token from `apps/api`
- join the LiveKit room
- render transcript, voice activity, order summary, and confirmation UI
- consume telemetry snapshots published by the Python agent

Important frontend files:

- `apps/web/components/app/app.tsx`
- `apps/web/components/app/view-controller.tsx`
- `apps/web/components/app/session-layout.tsx`
- `apps/web/components/app/landing-hero.tsx`
- `apps/web/components/app/voice-visualizer.tsx`
- `apps/web/lib/runtime-config.ts`
- `apps/web/hooks/useSessionTelemetry.ts`
- `apps/web/hooks/useVoicePresenceState.ts`

#### `apps/api`

Minimal FastAPI service.

Primary responsibilities:

- `GET /health`
- `POST /api/livekit/token`
- write requested session runtime config to `.voixai/session-configs/<room>.json`
- mint a LiveKit participant token
- dispatch the configured agent into the room

Important backend file:

- `apps/api/main.py`

#### `apps/agent-runtime`

Python LiveKit agent runtime.

Primary responsibilities:

- load env-based defaults
- load room-specific runtime config written by the API
- validate classic/OpenAI/Gemini runtime requirements
- start the correct voice session type
- maintain in-memory order state
- publish structured session telemetry to the room
- expose tool-based ordering behaviors to the agent

Important runtime file:

- `apps/agent-runtime/src/agent.py`

## Voice Modes Supported Today

The code currently supports three customer-facing voice modes:

1. `classic`
2. `openai_realtime`
3. `gemini_live`

### Classic

Uses:

- Deepgram STT
- OpenAI text LLM
- Cartesia TTS

This mode emits classic per-stage latency metrics like:

- transcription delay
- end of turn delay
- llm ttft
- tts ttfb
- e2e latency

### OpenAI Realtime

Uses the LiveKit OpenAI realtime plugin. STT, reasoning, and speech are handled by the realtime model rather than separate pipeline stages.

### Gemini Live

Uses the LiveKit Google realtime plugin. Current model default in the code is:

- `gemini-3.1-flash-live-preview`

The logs also show an important behavior note:

- Gemini 3.1 has limited mid-session update support
- instructions, chat context, and tool updates may not apply until the next session

## End-to-End Request Flow

The current start-order flow is:

1. The user selects a voice mode in `apps/web`
2. The frontend builds `runtime_config` from `apps/web/lib/runtime-config.ts`
3. The frontend posts to `POST /api/livekit/token`
4. The API writes room-specific runtime config into `.voixai/session-configs`
5. The API returns a LiveKit token and dispatches the configured agent name
6. The browser joins the room
7. The Python worker receives the job, loads the room-specific runtime config, resolves the final runtime profile, and starts the correct session type
8. The runtime publishes structured telemetry snapshots back into the room
9. The frontend renders transcript, voice state, order summary, and confirmation from that session state

## Important Recent Behavior Changes

### Fresh room per order

The frontend now rotates to a fresh room name after ending an order. This matters because reusing the same room name caused stale room-level runtime config to affect later sessions, which broke OpenAI Realtime and Gemini Live restart behavior.

Relevant files:

- `apps/web/components/app/app.tsx`
- `apps/web/components/app/view-controller.tsx`

### Frontend default voice mode now follows env

The frontend no longer always boots with the classic preset. It now derives its default runtime config from:

- `NEXT_PUBLIC_DEFAULT_VOICE_MODE`
- or server-side `VOICE_PROVIDER` / `VOICE_ENGINE`

Relevant files:

- `apps/web/lib/runtime-config.ts`
- `apps/web/app-config.ts`
- `apps/web/components/app/app.tsx`

### Realtime-safe away prompt

The runtime now avoids calling `session.say()` for realtime sessions where that path can fail. Classic still uses `say()`, while realtime modes use `generate_reply(...)`.

Relevant files:

- `apps/agent-runtime/src/agent.py`
- `apps/agent-runtime/tests/test_order_state.py`

## Current UI State

The main frontend has already moved away from a generic debug dashboard toward a customer-facing voice ordering interface.

Current UX structure:

- landing / start screen
- live session layout
- confirmation screen

Current customer-facing UI components include:

- `LandingHero`
- `AssistantStage`
- `VoiceVisualizer`
- `ConversationTranscript`
- `OrderSummaryPanel`
- `ConfirmationScreen`

Developer/debug information is now hidden behind a collapsible developer panel rather than being part of the default customer-facing surface.

## Audit Findings

### High: documentation drift is significant

Status:

- Core repo documentation was refreshed on 2026-06-11 in:
  - `README.md`
  - `apps/agent-runtime/README.md`
  - `apps/web/README.md`
  - `docs/ENVIRONMENT_VARIABLES.md`
  - `docs/LOCAL_SETUP.md`
- This finding remains useful historically, but the highest-priority drift called out here has now been addressed.

The codebase has outgrown its docs.

Examples:

- `README.md` still describes the project as mostly classic-pipeline-first and does not accurately describe Gemini Live support, fresh-room-per-order behavior, or the newer UI architecture
- `apps/agent-runtime/README.md` is still largely the upstream LiveKit starter README
- `apps/web/README.md` is still largely the upstream React/Agents UI starter README
- `docs/ENVIRONMENT_VARIABLES.md` still says the stable default is `VOICE_PROVIDER=classic`, which is no longer a reliable source-of-truth statement for the actual user experience because the web app can now default from env and runtime presets
- `docs/LOCAL_SETUP.md` is behind the current voice mode and session behavior

Impact:

- onboarding is slower
- behavior is easy to misread
- debugging gets harder because docs and logs appear to contradict each other

### Medium: the repo is in an active refactor state

Status:

- A shared architecture document now exists at `docs/ARCHITECTURE.md`.
- Core repo docs were refreshed on 2026-06-11.
- The working tree may still be dirty while active changes are in progress, but the documentation and architecture handoff risk are lower than before this cleanup pass.

The working tree is currently dirty and includes:

- modified runtime files
- modified web config files
- newly added app components not yet committed

Impact:

- current docs should be treated as “point-in-time working state,” not a stable release snapshot
- handoff risk is higher until the current branch is committed cleanly

### Medium: top-level source of truth is fragmented

Status:

- A maintained cross-app architecture document now exists at `docs/ARCHITECTURE.md`.
- This reduces the need to infer system behavior only from scattered implementation files.

At the moment, the real implementation source of truth is spread across:

- `apps/agent-runtime/src/agent.py`
- `apps/api/main.py`
- `apps/web/components/app/*`
- `apps/web/lib/runtime-config.ts`

There is no single maintained architectural document that accurately reflects all three apps together.

### Medium: end-to-end automated coverage is limited

Status:

- Coverage is still limited compared with a full production system.
- The repo now includes stronger focused coverage around the API runtime-config handoff in `apps/api/tests/test_main.py` in addition to the existing runtime tests and frontend build/type verification.

What is present:

- Python runtime unit tests in `apps/agent-runtime/tests`
- frontend build/type verification

What is missing:

- cross-service integration tests
- browser-level end-to-end tests for start/end/restart across modes
- regression coverage for room lifecycle + runtime mode switching in the web app

### Low: generated/starter artifacts remain in the repo

Status:

- The starter README remnants were replaced with VoixAI-specific docs.
- Remaining generated/noise cleanup should include deleting tracked log artifacts and keeping generated package metadata out of the curated repo view.

There are several starter/template remnants and likely low-signal files, for example:

- starter README content in `apps/web/README.md`
- starter README content in `apps/agent-runtime/README.md`
- `apps/web/web.log`
- `apps/web/web.err`
- egg-info directories under `apps/api`

These are not necessarily breaking, but they make the repo feel less curated.

## What Is Implemented Today

### Product behavior

- customer-facing voice ordering flow
- voice mode selector for Classic Voice, OpenAI Realtime, and Gemini Live
- live session transcript
- structured order summary
- confirmation screen
- text fallback composer
- microphone control and end-order flow

### Runtime behavior

- room-specific runtime config loading
- runtime validation for OpenAI and Google keys
- runtime profile telemetry publishing
- in-memory order mutation tools
- mock pricing and confirmation
- classic and realtime session construction

### Operational behavior

- LiveKit token minting
- explicit agent dispatch by `AGENT_NAME`
- fresh room creation per new order
- session telemetry topic publishing

## Known Risks

### Gemini Live mid-session update limitations

Observed in logs:

- Gemini 3.1 limited mid-session instruction/context/tool update support

This should be treated as a runtime constraint, not just a warning. If product behavior depends on mid-session dynamic updates, Gemini may behave differently than OpenAI Realtime or Classic.

### Room config persistence is file-based

Room runtime config is persisted in:

- `.voixai/session-configs`

This is acceptable for local development, but it is not durable multi-instance infrastructure and can create debugging confusion if stale files are reused.

### Order state is still in memory only

There is still no persistent database-backed order record. All order state is ephemeral and session-scoped.

## Source of Truth Recommendation

For now, these files should be treated as the most trustworthy implementation references:

- runtime behavior: `apps/agent-runtime/src/agent.py`
- API behavior: `apps/api/main.py`
- frontend session behavior: `apps/web/components/app/app.tsx`
- frontend mode selection and payload shape: `apps/web/lib/runtime-config.ts`
- session UI state mapping: `apps/web/components/app/session-status.ts`

## Verification Snapshot

Recent successful checks in the current workspace:

- `corepack pnpm exec next build --no-lint` in `apps/web`
- `corepack pnpm exec tsc --noEmit` in `apps/web`
- `apps\agent-runtime\.venv\Scripts\python.exe -m pytest apps\agent-runtime\tests\test_order_state.py -q`
- `python -m py_compile apps\agent-runtime\src\agent.py`

## Recommended Next Steps

1. Replace the top-level `README.md` with a current product-level overview that covers all three voice modes and the real session flow.
2. Replace `apps/agent-runtime/README.md` with a VoixAI-specific runtime guide instead of the LiveKit starter README.
3. Replace `apps/web/README.md` with a VoixAI-specific frontend guide instead of the starter template README.
4. Update `docs/ENVIRONMENT_VARIABLES.md` and `docs/LOCAL_SETUP.md` so they reflect Gemini Live, env-driven default mode selection, and fresh room-per-order behavior.
5. Add a small integration test plan for:
   - start order in classic
   - end order
   - restart in OpenAI Realtime
   - end order
   - restart in Gemini Live
6. Decide whether `.voixai/session-configs` remains the long-term local dev mechanism or gets replaced by a more explicit runtime-session registry.
7. Clean low-signal starter/template artifacts from the repo once the current refactor is committed.

## Suggested Documentation Ownership

If you want one minimal documentation hierarchy going forward:

- `README.md`
  - product overview
  - current architecture
  - quickstart
- `docs/PROJECT_AUDIT_REPORT.md`
  - current-state audit and risks
- `docs/LOCAL_SETUP.md`
  - exact local run steps
- `docs/ENVIRONMENT_VARIABLES.md`
  - env contract
- `apps/agent-runtime/README.md`
  - runtime-specific behavior
- `apps/web/README.md`
  - frontend-specific behavior

## Bottom Line

The project itself is meaningfully ahead of its documentation.

The implementation now supports:

- classic pipeline ordering
- OpenAI Realtime
- Gemini Live
- room-scoped runtime selection
- fresh session restart behavior
- a much more product-like voice UI

The biggest audit takeaway is not that the code is nonfunctional. It is that the repository needs a documentation consolidation pass so new contributors stop reading starter-template docs and older assumptions instead of the actual VoixAI system.
