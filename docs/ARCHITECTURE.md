# Architecture (Current State)

Last reviewed: 2026-06-15

This document describes **what the system actually is today**, including the parts
that are not production-grade yet. For the future/target design and the gap
analysis, see [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md). For the long-term
platform vision, see [direction.md](./direction.md).

> Naming model: **VoixAI** is the platform, **Wingstop inbound ordering** is the
> one active *scenario*, and **web / phone** are *channels*.

## 1. System Overview

VoixAI is a three-app system that lets a browser talk to a Python voice agent
through a LiveKit room.

```text
            ┌─────────────────────────────────────────────────────────────┐
            │                        apps/web (Next.js)                     │
            │  voice mode selection · transcript · order panel · confirm UI │
            └───────────────┬───────────────────────────▲──────────────────┘
                            │ 1. POST /api/livekit/token │ 8. telemetry snapshots
                            │    {room, runtime_config}  │    (LiveKit data channel)
                            ▼                            │
            ┌──────────────────────────────┐             │
            │       apps/api (FastAPI)      │             │
            │  • mint LiveKit JWT           │             │
            │  • dispatch agent into room   │             │
            │  • write room runtime config  │             │
            │    → .voixai/session-configs  │             │
            │  • menu resolve/validate/price│◀───────┐    │
            └───────────────┬──────────────┘        │    │
                            │ 4. dispatch (RoomConfiguration)  │ 6. HTTP menu/order calls
                            ▼                        │    │
                    ┌───────────────┐                │    │
                    │  LiveKit Room │                │    │
                    └───────┬───────┘                │    │
                            │ 5. agent joins         │    │
                            ▼                        │    │
            ┌──────────────────────────────────────┴────┴──────────────────┐
            │              apps/agent-runtime (Python LiveKit Agents)        │
            │  • resolve runtime config for the room                         │
            │  • build classic / OpenAI Realtime / Gemini Live session       │
            │  • WingstopAssistant: order tools + in-memory OrderState       │
            │  • publish telemetry snapshots back to the room                │
            └────────────────────────────────────────────────────────────────┘
```

The browser **never** talks to OpenAI/Google realtime APIs directly. It only
joins a LiveKit room with a token minted by `apps/api`; the Python runtime runs
the actual voice path.

## 2. End-to-End Flow

1. The user opens `apps/web` and picks a voice mode (preset → `RuntimeConfig`).
2. On "start", the web app `POST`s `room_name`, `participant_name`, and
   `runtime_config` to `apps/api` → `POST /api/livekit/token`
   ([app.tsx](../apps/web/components/app/app.tsx), [runtime-config.ts](../apps/web/lib/runtime-config.ts)).
3. The API writes the requested runtime config to
   `.voixai/session-configs/<room>.json` and mints a participant JWT that
   carries a `RoomConfiguration` dispatching `AGENT_NAME`
   ([main.py](../apps/api/main.py)).
4. LiveKit dispatches the agent worker into the room.
5. The browser joins the same room.
6. The worker resolves the room-scoped runtime config, validates it, builds the
   correct session type, and starts `WingstopAssistant`
   ([agent.py](../apps/agent-runtime/src/agent.py)).
7. During the conversation, the agent's order tools call the API's menu
   endpoints (`/api/menu/resolve-selection`, `/validate-order`, `/price-order`)
   over HTTP ([wingstop.py](../apps/agent-runtime/src/scenarios/wingstop.py)).
8. After every order mutation / metric event, the worker publishes a JSON
   `session_snapshot` on the `voixai.telemetry` data topic. The web app renders
   transcript, order summary, confirmation, and the developer panel from those
   snapshots.

Each new order rotates to a **fresh room name** (`<roomName>-<timestamp>`) so a
restart never reuses a stale `session-configs` file
([app.tsx:38-42, 83-85](../apps/web/components/app/app.tsx)).

## 3. Apps

### 3.1 `apps/web` — Next.js 15 / React 19

Responsibilities: landing + mode selection, session start/end, transcript, voice
visualization, scenario workspace (Wingstop order panel), confirmation screen,
hidden developer details.

Key files:
- [components/app/app.tsx](../apps/web/components/app/app.tsx) — session orchestration, token source, room rotation
- [components/app/view-controller.tsx](../apps/web/components/app/view-controller.tsx) — landing/session/confirmation routing
- [lib/runtime-config.ts](../apps/web/lib/runtime-config.ts) — presets + the `runtime_config` payload shape
- [lib/scenario-config.ts](../apps/web/lib/scenario-config.ts), [lib/channel-config.ts](../apps/web/lib/channel-config.ts) — scenario/channel metadata
- [hooks/useSessionTelemetry.ts](../apps/web/hooks/useSessionTelemetry.ts) — parses `voixai.telemetry` snapshots
- [components/app/scenarios/wingstop/*](../apps/web/components/app/scenarios/wingstop) — Wingstop-specific panels

### 3.2 `apps/api` — FastAPI

Endpoints:
- `GET /health`
- `POST /api/livekit/token` — persist runtime config, mint JWT, dispatch agent
- `GET /api/menu/summary`
- `POST /api/menu/resolve-selection`
- `POST /api/menu/validate-order`
- `POST /api/menu/price-order`

Key file: [main.py](../apps/api/main.py).

The API imports the menu, pricing, and validation from the shared
`packages/ordering` (`voix_ordering`) package — the single source of truth, also
used by the agent runtime ([main.py](../apps/api/main.py)). The `/api/menu/*`
endpoints are a thin HTTP transport over that domain. (Before M1 the API
side-loaded the runtime's `wingstop.py` via `sys.modules` stubs; that hack is
gone — see [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md) §5.1.)

### 3.3 `apps/agent-runtime` — Python LiveKit Agents

Responsibilities: runtime-config resolution/validation, classic/realtime session
construction, order tools, in-memory order state, telemetry publishing, session
event handling.

Key files:
- [src/agent.py](../apps/agent-runtime/src/agent.py) — ~1,070-line module holding
  config resolution, provider plumbing, session events, telemetry
- [src/scenarios/wingstop.py](../apps/agent-runtime/src/scenarios/wingstop.py) —
  ~2,150-line module holding the **menu data**, pricing, validation, prompt,
  and the `WingstopAssistant` tools
- [src/scenarios/base.py](../apps/agent-runtime/src/scenarios/base.py),
  [src/channels.py](../apps/agent-runtime/src/channels.py) — scenario/channel registries

## 4. Voice Modes

The frontend `voice_engine` maps to one of three provider paths in the worker
([agent.py:112-128, 637-805](../apps/agent-runtime/src/agent.py)):

| Mode | Engine | Stack | Stage metrics |
|------|--------|-------|---------------|
| Classic | `pipeline` | Deepgram STT → text LLM (`openai/gpt-5.3-chat-latest`) → Cartesia TTS | yes (transcription/EOT/TTFT/TTFB/e2e) |
| OpenAI Realtime | `openai_realtime` | LiveKit OpenAI realtime plugin (speech-to-speech) | no per-stage metrics |
| Gemini Live | `gemini_live` | LiveKit Google realtime plugin (`gemini-3.1-flash-live-preview`) | no per-stage metrics |

`_text` variants of the realtime engines exist (text-only modality + TTS
fallback) but are not surfaced in the default UI presets.

Provider/engine resolution has a **graceful-fallback** path: if a realtime
plugin or key is missing, the worker falls back to the classic pipeline and
records `fallback_reason` ([agent.py:571-634](../apps/agent-runtime/src/agent.py)).

**Gemini 3.1 caveats** (handled in code): it does not support forced
`generate_reply(...)` for greeting/away prompts, so those sessions attach a TTS
fallback and use `say(...)`; affective-dialog/proactivity flags are ignored;
mid-session instruction/tool updates may not apply until the next session. The
Google plugin is pinned to the `charan632-dev/agents` fork for this fix path.

## 5. Order-Taking Subsystem (the scenario)

Order **domain** logic (menu, pricing, validation, order state, state machine)
lives in the shared `packages/ordering` (`voix_ordering`) package. The runtime's
[wingstop.py](../apps/agent-runtime/src/scenarios/wingstop.py) is now a thin
layer: the agent prompt, the order tools, the backend HTTP client, and
telemetry/audit. It re-exports domain symbols for backward compatibility.

**Data model** (Python dataclasses, in-memory only):
- `MenuItem`, `FlavorOption`, `ModifierOption`, `ModifierGroup` — the demo menu
  (`Voix Wings Demo`, ~40 items) declared as Python literals
- `OrderState` → `OrderLineItem` — the live cart
- `PriceQuote`, `MockOrder` — pricing output and the fake placed order

**Agent tools** (`WingstopAssistant`, `@function_tool`):
`add_menu_item`, `update_last_item`, `remove_order_item`, `set_order_type`,
`set_customer_details`, `set_confirmation_status`, `get_menu_summary`,
`get_order_summary`, `price_order`, `review_order_for_confirmation`,
`create_mock_order`, `wait_more`.

**Reliability model:** a deterministic `OrderStateMachine`
([state_machine.py](../packages/ordering/src/voix_ordering/state_machine.py))
owns every order transition (`reset_to_collecting`, `mark_priced`,
`mark_reviewed`, `set_confirmed`, `mark_submitted`) and derives the order
`phase` in one place. The `create_mock_order` tool calls
`OrderStateMachine.authorize_submit()`, which **re-validates from scratch and
re-checks the confirmation checklist on every attempt** — so an order can only
be placed when it is genuinely valid and confirmed, regardless of which tools
the model called or in what order. The boolean flags on `OrderState` remain as
the persisted representation the machine reads/writes; the phase is published in
telemetry.

A regex-based post-hoc auditor, `audit_assistant_response`, additionally
inspects each assistant message for price/placement hallucinations and records
`assistant_guardrail_violations` in telemetry (it flags; the state machine is
what structurally blocks).

## 6. Configuration & State

| Concern | Where it lives | Durability |
|---------|----------------|------------|
| Per-room runtime config | `.voixai/session-configs/<room>.json` (written by API, read by worker) | local file, never cleaned up |
| Order state | `SessionState.order` in worker process memory | lost on disconnect/restart |
| Placed order | `MockOrder` (random `MOCK-#####`) | none — never persisted |
| Telemetry | LiveKit data channel `voixai.telemetry` | ephemeral, not stored |
| Secrets | `.env` files loaded in each app | env-only |

## 7. Telemetry Contract

The worker publishes reliable JSON messages on topic `voixai.telemetry`
([agent.py:308-338](../apps/agent-runtime/src/agent.py)). Snapshot shape:

```jsonc
{
  "type": "session_snapshot",
  "scenario_id": "wingstop_inbound_ordering",
  "channel_id": "web",
  "reason": "order_state_updated",       // why the snapshot was sent
  "timestamp": 0.0,
  "turn_count": 0,
  "runtime_profile": { /* provider/model/preset/fallback_reason */ },
  "user_turn_metrics": { /* classic only */ },
  "assistant_turn_metrics": { /* classic only */ },
  // scenario-specific (build_wingstop_snapshot):
  "order": { /* serialize_order_state */ },
  "price_quote": { /* or null */ },
  "mock_order": { /* or null */ },
  "assistant_guardrail_violations": []
}
```

## 8. Tests

- [apps/agent-runtime/tests/test_order_state.py](../apps/agent-runtime/tests/test_order_state.py)
  — menu validation, pricing, confirmation gating, provider mapping, greeting paths
- [apps/agent-runtime/tests/test_agent.py](../apps/agent-runtime/tests/test_agent.py)
- [apps/api/tests/test_main.py](../apps/api/tests/test_main.py) — API handoff
- Frontend: build + `tsc --noEmit` only

No cross-service integration tests, no conversation/eval simulations, no
browser-level E2E.

## 9. Known Architectural Debt (summary)

These are expanded with severity, evidence, and fixes in
[PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md):

1. ~~The API side-loads the runtime's `wingstop.py`~~ — **Fixed (M1).** Menu,
   pricing, validation, and order state now live in the shared
   `packages/ordering` package, imported directly by both apps.
2. ~~Order-placement reliability depends on prompt-sequenced tool calls~~ —
   **Fixed (M2).** `OrderStateMachine.authorize_submit()` is the deterministic
   hard gate; phase is derived in one place and published in telemetry.
3. Order state and placed orders are in-memory only — nothing is persisted.
4. Runtime config is passed through local JSON files (`.voixai/session-configs`),
   which is not multi-instance safe and is never garbage-collected.
5. The token endpoint has no auth, no rate limiting; CORS is permissive.
6. `agent.py` and `wingstop.py` are large multi-responsibility modules.
7. Telemetry/analytics/cost are ephemeral; no persisted session record.
8. Guardrails flag but do not block; menu/pricing is demo data, not POS-backed.

## 10. Source of Truth

| Question | Read |
|----------|------|
| End-to-end flow & current behavior | this file |
| Runtime/provider behavior | `apps/agent-runtime/src/agent.py` |
| Menu/order/pricing logic | `apps/agent-runtime/src/scenarios/wingstop.py` |
| API surface | `apps/api/main.py` |
| Frontend payload shape | `apps/web/lib/runtime-config.ts` |
| Telemetry → UI mapping | `apps/web/hooks/useSessionTelemetry.ts` |
| What to fix for production | `docs/PRODUCTION_READINESS.md` |
| Long-term platform vision | `docs/direction.md` |
