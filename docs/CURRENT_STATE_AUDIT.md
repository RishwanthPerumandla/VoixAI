# Current State Audit

Last reviewed: 2026-06-27

This audit was produced for Phase 0 of the VoixAI hardening program. It checks
the root README, all files in `docs/`, and the current `apps/agent-runtime`
voice paths against the code in `apps/api`, `apps/agent-runtime`, and
`packages/ordering`.

Phase 1 update (2026-06-27): `apps/api` now has a SQLAlchemy/Alembic
persistence foundation with SQLite test/dev fallback and Postgres selected by
`DATABASE_URL`. Confirmed orders persist as `WS-####` public codes with
`customers`, `stores`, `menu_items`, `orders`, and `order_items` tables behind
`CustomerService`, `StoreService`, and `OrderService`.

Phase 2 update (2026-06-27): `apps/agent-runtime` now has a shared
`conversation_core` layer with the closed-set intent router and top-level
`GREETING -> IDENTIFY -> ROUTE -> ORDER/TRACK/STORE_INFO/CANCEL/ESCALATE`
state machine. The runtime starts this layer before the provider greeting and
routes caller turns from the common session event path used by `classic`,
`openai_realtime`, and `gemini_live`. `apps/api` exposes the thin conversation
session endpoints needed to persist `call_sessions.current_node`, identify
callers by phone, and persist confirmed names on the customer record. ORDER,
TRACK, STORE_INFO, CANCEL, and ESCALATE are intentionally stubs until the
later scoped phases.

## Executive Summary

VoixAI is already a working LiveKit-centered voice demo with three selectable
worker-side voice paths, a shared deterministic ordering package, SQLAlchemy
order/customer/menu persistence, a shared call-level router/FSM foundation,
best-effort dashboard telemetry, and a 193-scenario offline reliability suite.

It is not yet the target production-style system in the new brief. The
call-level conversation core now exists, but most destination nodes are still
Phase 2 stubs and the hard ORDER sub-FSM is not implemented yet. The current
Wingstop order-taking flow is still mainly one LiveKit agent prompt with tools,
plus a deterministic ordering reducer/state machine underneath. That ordering
core is valuable and should be preserved, but Phase 3 still needs to move the
configurable item collection flow behind explicit ORDER nodes.

## Real System Shape Today

### Apps

- `apps/web` is the Next.js customer voice UI. It selects a runtime preset,
  starts a fresh room, renders live telemetry, transcript, order summary, and
  dashboard/observability screens.
- `apps/api` is a FastAPI service. It mints LiveKit tokens, attaches
  `runtime_config` as LiveKit agent dispatch metadata, writes a local fallback
  session-config file, exposes menu/validation/pricing/order endpoints, persists
  orders/calls in SQLite, and exposes aggregate analytics/observability endpoints.
- `apps/agent-runtime` is the Python LiveKit worker. It resolves runtime config,
  builds one of the three voice paths, starts `WingstopAssistant`, publishes
  session snapshots on `voixai.telemetry`, and opens/finalizes call records
  best-effort through `apps/api`.
- `packages/ordering` is the deterministic ordering domain. It owns catalog
  loading, menu resolution, validation, pricing, order models, reducer intents,
  replay, and the order lifecycle state machine.

### Voice Paths

The three voice paths are selected through the same `runtime_config`/env surface:

- `classic`: LiveKit pipeline session with Deepgram-style STT model config,
  OpenAI-compatible text LLM through `inference.LLM`, Cartesia-style TTS model
  config, VAD, turn detection, interruption settings, and classic stage metrics.
- `openai_realtime`: LiveKit OpenAI realtime plugin model. The browser still only
  joins LiveKit. Missing plugin/key paths fall back to `classic`.
- `gemini_live`: LiveKit Google realtime plugin model. The browser still only
  joins LiveKit. Gemini 3.1 uses native `generate_reply(...)` for startup speech.
  Missing plugin/key paths fall back to `classic`.

All three paths run the same `WingstopAssistant` tool surface and publish the
same session snapshot shape. Realtime sessions do not emit the classic per-stage
STT/LLM/TTS metrics.

## Real Call Flow Today

1. The web app chooses a runtime preset from `apps/web/lib/runtime-config.ts`.
2. The browser posts `room_name`, `participant_name`, and `runtime_config` to
   `POST /api/livekit/token`.
3. The API serializes `runtime_config` into `RoomAgentDispatch.metadata`, writes
   `.voixai/session-configs/<room>.json` as a local fallback, best-effort upserts
   a SQLite `sessions` row, mints a LiveKit participant JWT, and dispatches the
   configured agent.
4. The browser joins the room with the token.
5. The worker receives the job, prefers `ctx.job.metadata` for runtime config,
   falls back to the room config file if metadata is absent, validates provider
   requirements, and connects to the room.
6. If a realtime provider is selected, the worker probes data publishing and can
   fall back to `classic` on publisher connection failure.
7. The worker builds the provider model/session, starts `WingstopAssistant`,
   starts the shared conversation FSM, persists `call_sessions.current_node`,
   deterministically greets as `Hello, Wingstop Dallas.`, identifies the caller
   by `caller_id`/phone when present, and publishes a startup snapshot.
8. Customer turns are handled by the shared router/FSM first, then by the
   LiveKit session and assistant prompt. The model calls tools such as
   `capture_customer_name`, `confirm_customer_name`, `set_customer_details`,
   `add_menu_item`,
   `update_last_item`, `price_order`, `review_order_for_confirmation`, and
   `create_mock_order`.
9. Tool calls mutate the shared `OrderState` through `packages/ordering` reducer
   and validation logic. Pricing and validation run in-process against the same
   shared domain used by the API. Final submission posts to `POST /api/orders`.
10. `POST /api/orders` re-runs `OrderStateMachine.authorize_submit()`, derives an
    idempotency key when needed, persists an order row in SQLite, and returns a
    `MOCK-...` order number.
11. The runtime records a rolling transcript in memory, opens a call row at
    session start, and finalizes it on shutdown with transcript JSON, duration,
    outcome, sentiment estimate, order number, and guardrail count.
12. The frontend gets live state from ephemeral LiveKit data-channel snapshots.
    It can also query API dashboard endpoints for persisted calls/orders/analytics.

## What Already Exists And Should Be Preserved

- LiveKit remains the only browser media transport. Provider keys stay server-side.
- `runtime_config` already supports `classic`, `openai_realtime`, and
  `gemini_live` through one contract.
- The primary runtime-config handoff is dispatch metadata, which is multi-host
  friendlier than the older shared-file-only path.
- `packages/ordering` is the single deterministic source for menu, validation,
  pricing, reducer behavior, order state, and submit authorization.
- The menu is catalog-driven from `apps/api/data/wingstop_demo_catalog.json`.
- The order submit gate is deterministic and rerun server-side before persistence.
- Order submission is idempotent in SQLite.
- The reliability suite is offline and key-free, with 193 scenarios in the latest
  report.
- Live telemetry snapshots drive the current UI and include order/price/mock-order
  state, runtime profile, conversation node/last intent, latency fields, and
  guardrail violations.
- The API already has useful dashboard primitives: calls, orders, analytics
  overview, and observability health.

## What Is Broken Or Missing Against The Brief

### Conversation Core

- Phase 2 added the closed-set call intent router in
  `apps/agent-runtime/src/conversation_core/router.py`. It supports the required
  intents: `place_order`, `modify_order`, `track_order`, `cancel_order`,
  `store_info`, `speak_to_human`, and `smalltalk_or_unknown`.
- Phase 2 added the explicit top-level FSM in
  `apps/agent-runtime/src/conversation_core/state_machine.py` with
  `StateNode` declarations for `GREETING`, `IDENTIFY`, `ROUTE`, `ORDER`,
  `TRACK`, `STORE_INFO`, `CANCEL`, `ESCALATE`, and `WRAPUP`.
- `call_sessions.current_node` is persisted through `apps/api` conversation
  endpoints so a simulated reconnect can resume from the last node.
- Greeting is deterministic on session start and now branches through
  identification. Returning callers with a known name hear a personalized
  greeting and last-order summary; new callers continue to the route prompt.
- Name capture now has explicit capture/confirm tools, spelling fallback, and
  persistence to the customer record. Filled names are not re-asked.
- Remaining gap: ORDER/TRACK/STORE_INFO/CANCEL/ESCALATE are Phase 2 stubs. Their
  real behavior belongs to Phases 3, 4, and 6.

### Order Flow

- The deterministic ordering core is strong, but the ORDER sub-FSM from the brief
  does not exist as explicit nodes (`SELECT_ITEM`, `CONFIGURE_ITEM`, `ADD_SIDES`,
  `ADD_DRINKS`, `REVIEW`, `CONFIRM`, `PLACE`).
- Slot filling is largely prompt/tool driven. Validation and placement are
  deterministic, but the agent can still decide which tool to call next.
- Live repricing is mostly provided in tool responses after mutations, but the
  brief's state-machine-driven "ask only missing required options" behavior is
  not formalized as a node contract.
- The persisted order number is still `MOCK-...`, not the requested `WS-4821`
  style public code.
- If the backend is unreachable during placement, the runtime can fall back to a
  local non-persisted mock order for demo continuity. That is useful for demos,
  but it violates the target guarantee that confirmed orders persist.

### Backend And Data Model

- Phase 1 added SQLAlchemy 2.x models, Alembic, a first migration, and a seed
  command. SQLite remains the deterministic test/dev path; Postgres is selected
  by `DATABASE_URL`.
- The current schema now includes `customers`, `stores`, `menu_items`, `orders`,
  `order_items`, plus compatibility `sessions` and `calls`. It still does not
  have `transcript_turns`, `call_events`, or `escalations`.
- `CustomerService`, `StoreService`, and `OrderService` now exist. Order
  submission uses them for demo store/menu seed, customer upsert when a phone is
  present, idempotent confirm, order line persistence, and customer rollups.
- Confirmed orders now store the target lifecycle status `confirmed` and return
  `WS-####` public codes. Server-owned kitchen progression
  (`confirmed -> in_kitchen -> ready -> completed`) is still future work.
- Returning-customer conversational lookup by phone is implemented for Phase 2
  identification. Full tracking by latest active order is still Phase 4.

### Tracking, Cancel, Store Info

- There is a `GET /api/orders/{order_number}` endpoint and the Phase 2 router
  can dispatch to a TRACK node, but TRACK is still a stub. Full tracking flow
  and latest-active-order lookup by phone remain Phase 4.
- Cancellation exists only for the in-memory active order before submission, and
  the Phase 2 CANCEL node is a stub. There is no persisted order cancellation
  endpoint or server-owned transition yet.
- Store data is persisted through Phase 1, and the Phase 2 STORE_INFO node is a
  stub. Deterministic store-hours answers remain Phase 4.

### Observability

- Transcripts are persisted as a JSON array on the final `calls` row, not as
  per-turn `transcript_turns` rows.
- There is no persisted granular `call_events` stream for `state_enter`,
  `slot_filled`, `validation_error`, `reprice`, `confirmation`,
  `escalation_trigger`, `provider_error`, or `latency_sample`.
- There is no LiveKit Egress recording integration, no S3/MinIO storage, and no
  `recording_url`.
- Analytics endpoints exist, but they are summaries over call/order rows. They do
  not yet expose the full per-call and aggregate metrics required by the brief,
  especially p50/p95 turn latency and intent distribution from persisted events.

### Escalation

- Hard-trigger handoff exists for phrases like a human request or frustration,
  plus repeated placement-failure handoff.
- There is no `FrustrationMonitor` with configurable thresholds, rolling score,
  repeated-slot correction counting, state-loop detection, low-confidence STT
  streaks, or duration-without-progress logic.
- There is no `escalations` persistence and no pluggable warm transfer using
  `MANAGER_HANDOFF_NUMBER`.

### Reliability And Scale

- The reliability suite is healthy and broad for ordering. Phase 2 added
  separate offline router/FSM tests for routing, identification, name capture,
  and reconnect resume. It still does not cover full tracking, persisted
  cancellation, store-info node behavior, escalation monitor thresholds,
  idempotent confirm against the target service layer, or provider circuit
  breakers.
- There are provider fallbacks for missing dependencies and realtime startup
  probe failure, but no general timeout/retry/jitter/circuit-breaker abstraction.
- Runtime state is still in worker memory for the active order and transcript
  until finalization. In-progress order rehydration is not implemented.
- Shared file fallback for runtime config still exists and is never cleaned up.
- The token endpoint is unauthenticated and not rate limited. CORS is local-dev
  friendly but still allows all methods and headers.
- No load-test script exists for concurrent deterministic sessions.

## Documentation Drift Found

- `docs/PRODUCTION_READINESS.md` still has older "current problem" sections that
  describe pre-M1/M2 behavior as current, then later says M1/M2 and part of M3
  are complete. It needs consolidation.
- `docs/ARCHITECTURE.md` says placed order/session durability is SQLite-backed,
  but its known-debt summary still says "order state and placed orders are
  in-memory only - nothing is persisted."
- `apps/agent-runtime/README.md` says runtime config comes from env defaults and
  room-scoped config written by the API, but the code now prefers dispatch
  metadata and uses the file only as fallback.
- Naming is inconsistent: the prompt/greeting says "Wingstop Dallas", while menu
  docs say the in-call restaurant name is `Voix Wings Demo`.
- Several docs contain mojibake characters from encoding drift. The content is
  still readable, but the files should be normalized during doc cleanup.

## Phase Implications

Phase 1 is complete as a persistence foundation. Phase 2 is complete as a shared
conversation-core foundation without changing the `runtime_config` contract or
the three voice paths.

The most important constraint for future phases is to put new call-level routing,
FSM, persistence, analytics, and escalation behind shared modules called by all
three voice paths. The current structure now has that first shared
router/state-machine boundary; Phase 3 should attach the ORDER sub-FSM to the
existing ORDER node entry point.
