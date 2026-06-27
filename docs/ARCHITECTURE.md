# Architecture (Current State)

Last reviewed: 2026-06-27

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
3. The API mints a participant JWT that carries a `RoomConfiguration`
   dispatching `AGENT_NAME`, with the requested runtime config attached as the
   dispatch **metadata** (the primary, filesystem-free handoff). It also writes
   `.voixai/session-configs/<room>.json` as a single-host fallback
   ([main.py](../apps/api/main.py)).
4. LiveKit dispatches the agent worker into the room.
5. The browser joins the same room.
6. The worker resolves the room-scoped runtime config, validates it, builds the
   correct session type, and starts `WingstopAssistant`
   ([agent.py](../apps/agent-runtime/src/agent.py)).
7. On session start, the runtime starts the shared conversation FSM
   (`GREETING -> IDENTIFY -> ROUTE`), persists `call_sessions.current_node`
   through `apps/api`, and uses the FSM response as the deterministic greeting.
8. During each caller turn, the common session event path routes the transcript
   through the shared intent router/FSM before the provider-specific voice path
   continues. This keeps `classic`, `openai_realtime`, and `gemini_live` behind
   the same intent-and-slots boundary.
9. During the conversation, the agent's order tools call the API's menu
   endpoints (`/api/menu/resolve-selection`, `/validate-order`, `/price-order`)
   over HTTP ([wingstop.py](../apps/agent-runtime/src/scenarios/wingstop.py)).
10. After every order mutation / metric event, the worker publishes a JSON
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

Phase 2 conversation endpoints:
- `GET /api/conversation/sessions/{call_id}` - read the persisted top-level FSM node
- `PATCH /api/conversation/sessions/{call_id}/node` - persist the current top-level FSM node
- `POST /api/conversation/identify` - identify or create a customer by caller phone
- `POST /api/conversation/name` - persist a confirmed caller name

Existing token/menu/order endpoints:
- `GET /health`
- `POST /api/livekit/token` — persist runtime config, mint JWT, dispatch agent
- `GET /api/menu/summary`
- `POST /api/menu/resolve-selection`
- `POST /api/menu/validate-order`
- `POST /api/menu/price-order`
- `POST /api/orders` — idempotent order submission (re-runs the submit gate server-side, persists the order)
- `GET /api/orders/{order_number}` — read back a persisted order

Key files:
- [main.py](../apps/api/main.py) - FastAPI routes and LiveKit token/session dispatch
- [models.py](../apps/api/models.py) - SQLAlchemy Phase 1 schema
- [services.py](../apps/api/services.py) - `CustomerService`, `StoreService`, `OrderService`,
  `ConversationSessionService`, and menu seeding
- [alembic/versions/0001_phase1_persistence.py](../apps/api/alembic/versions/0001_phase1_persistence.py) - first migration

Persistence is now SQLAlchemy-backed. SQLite remains the local/offline test
database when `DATABASE_URL` is unset; Postgres is selected by setting
`DATABASE_URL`. Phase 1 tables include `customers`, `stores`, `menu_items`,
`orders`, `order_items`, and compatibility `sessions`/`calls` tables for the
existing dashboard/session flows. Order submission returns a `WS-####` public
code and stores lifecycle status `confirmed`. Phase 2 also uses
`call_sessions.current_node` to persist the top-level conversation node for
reconnect resume.

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

Phase 2 adds `src/conversation_core/`:

- `router.py` contains the closed-set call intent router.
- `state_machine.py` contains the top-level `StateNode` FSM, identity, and name
  capture.
- `api_repository.py` contains the thin internal API client for persisted
  conversation session state.

The router returns `RouterResult(intent, confidence, slots,
requires_disambiguation)` for the closed enum `place_order`, `modify_order`,
`track_order`, `cancel_order`, `store_info`, `speak_to_human`, and
`smalltalk_or_unknown`. Deterministic grammar/keyword rules win for high-signal
phrases. A constrained classifier hook can be supplied for lower-signal
transcripts, but the offline tests run with no API key.

`ConversationStateMachine` declares `StateNode` objects for `GREETING`,
`IDENTIFY`, `ROUTE`, `ORDER`, `TRACK`, `STORE_INFO`, `CANCEL`, `ESCALATE`, and
`WRAPUP`. Destination nodes are stubs until later phases. `GREETING` fires on
session start; `IDENTIFY` resolves the caller by `runtime_config.caller_id`,
`runtime_config.caller_phone`, or participant identity; and the
`capture_customer_name` / `confirm_customer_name` tools provide confirmed name
capture with spelling fallback.

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

**Gemini 3.1 notes:** greeting and away prompts use native `generate_reply(...)`
so the model speaks in its own voice (one greeting, one voice). This requires
the `charan632-dev/agents` Google plugin fork, which adds forced-`generate_reply`
support for Gemini 3.1; the stock PyPI plugin lacks it and reintroduces a
duplicate greeting in a second (Cartesia) voice. Affective-dialog/proactivity
flags are ignored, and mid-session instruction/tool updates may not apply until
the next session.

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
| Per-room runtime config | primary: agent dispatch metadata (`ctx.job.metadata`); fallback: `.voixai/session-configs/<room>.json` | metadata travels with the job (no shared FS); file is a single-host fallback |
| Order state (in progress) | `SessionState.order` in worker process memory | lost on disconnect/restart (rehydration is a remaining M3 item) |
| Placed order | SQLAlchemy `orders` + `order_items` tables via `POST /api/orders`; SQLite by default, Postgres via `DATABASE_URL` | durable + idempotent (Phase 1); local runtime fallback still exists if API unreachable |
| Customer/store/menu mirror | SQLAlchemy `customers`, `stores`, `menu_items` tables | durable (Phase 1) |
| Top-level conversation node | SQLAlchemy `call_sessions.current_node` via `/api/conversation/*`; in-memory fallback if API is unreachable | durable when API is reachable (Phase 2) |
| Session record | SQLAlchemy `sessions` table (best-effort on token mint) | durable (Phase 1 compatibility) |
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
  "conversation": {
    "current_node": "ROUTE",
    "last_intent": "place_order",
    "last_intent_confidence": 0.84,
    "last_router_slots": {},
    "clarification_count": 0
  },
  // scenario-specific (build_wingstop_snapshot):
  "order": { /* serialize_order_state */ },
  "price_quote": { /* or null */ },
  "mock_order": { /* or null */ },
  "assistant_guardrail_violations": []
}
```

## 8. Tests

Phase 2 deterministic conversation-core tests:

- [apps/agent-runtime/tests/test_intent_router.py](../apps/agent-runtime/tests/test_intent_router.py)
  - offline fixed-transcript intent routing
- [apps/agent-runtime/tests/test_conversation_state_machine.py](../apps/agent-runtime/tests/test_conversation_state_machine.py)
  - greeting, identification, clarification, node resume, and name capture
- [apps/api/tests/test_conversation_core.py](../apps/api/tests/test_conversation_core.py)
  - conversation session, identity, and name persistence endpoints

- [apps/agent-runtime/tests/test_order_state.py](../apps/agent-runtime/tests/test_order_state.py)
  — menu validation, pricing, confirmation gating, provider mapping, greeting paths
- [apps/agent-runtime/tests/test_agent.py](../apps/agent-runtime/tests/test_agent.py)
- [apps/api/tests/test_main.py](../apps/api/tests/test_main.py) — API handoff
- Frontend: build + `tsc --noEmit` only

No browser-level E2E. Full order-sub-FSM conversation simulations are still
Phase 3+ work.

## 9. Known Architectural Debt (summary)

These are expanded with severity, evidence, and fixes in
[PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md):

1. ~~The API side-loads the runtime's `wingstop.py`~~ — **Fixed (M1).** Menu,
   pricing, validation, and order state now live in the shared
   `packages/ordering` package, imported directly by both apps.
2. ~~Order-placement reliability depends on prompt-sequenced tool calls~~ —
   **Fixed (M2).** `OrderStateMachine.authorize_submit()` is the deterministic
   hard gate; phase is derived in one place and published in telemetry.
3. ~~Placed orders are in-memory only~~ - **Fixed (Phase 1).** Confirmed
   orders now persist through SQLAlchemy with `WS-####` public codes, line
   items, customer rollups when a phone is present, demo store, and menu mirror.
   In-progress order rehydration is still future work.
4. ~~No shared call-level router/FSM~~ - **Fixed (Phase 2 foundation).** A
   shared intent router and top-level state machine now sit behind all three
   voice paths. ORDER/TRACK/STORE_INFO/CANCEL/ESCALATE are still stubs until
   later phases.
5. Runtime config is passed through local JSON files (`.voixai/session-configs`),
   which is not multi-instance safe and is never garbage-collected.
6. The token endpoint has no auth, no rate limiting; CORS is permissive.
7. `agent.py` and `wingstop.py` are large multi-responsibility modules.
8. Telemetry/analytics/cost are ephemeral; no persisted per-turn event stream.
9. Guardrails flag but do not block; menu/pricing is demo data, not POS-backed.

## 10. Source of Truth

| Question | Read |
|----------|------|
| End-to-end flow & current behavior | this file |
| Runtime/provider behavior | `apps/agent-runtime/src/agent.py` |
| Call intent routing and top-level FSM | `apps/agent-runtime/src/conversation_core/` |
| Menu/order/pricing logic | `apps/agent-runtime/src/scenarios/wingstop.py` |
| API surface | `apps/api/main.py` |
| Frontend payload shape | `apps/web/lib/runtime-config.ts` |
| Telemetry → UI mapping | `apps/web/hooks/useSessionTelemetry.ts` |
| What to fix for production | `docs/PRODUCTION_READINESS.md` |
| Long-term platform vision | `docs/direction.md` |
