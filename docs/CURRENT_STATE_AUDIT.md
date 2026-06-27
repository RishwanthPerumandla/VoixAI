# Current State Audit

Last reviewed: 2026-06-27

This audit was produced for Phase 0 of the VoixAI hardening program. It checks
the root README, all files in `docs/`, and the current `apps/agent-runtime`
voice paths against the code in `apps/api`, `apps/agent-runtime`, and
`packages/ordering`.

## Executive Summary

VoixAI is already a working LiveKit-centered voice demo with three selectable
worker-side voice paths, a shared deterministic ordering package, SQLite-backed
order/call persistence, best-effort dashboard telemetry, and a 191-scenario
offline reliability suite.

It is not yet the target production-style system in the new brief. The biggest
missing layer is the call-level conversation core: there is no closed-set intent
router and no top-level FSM for `GREETING -> IDENTIFY -> ROUTE -> ORDER/TRACK/...`.
The current Wingstop flow is still mainly one LiveKit agent prompt with tools,
plus a deterministic ordering reducer/state machine underneath. That ordering
core is valuable and should be preserved, but the call orchestration above it is
not explicit yet.

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
7. The worker builds the provider model/session, starts `WingstopAssistant`, marks
   the order state as `greeting`, triggers the hardcoded greeting
   `Hello, Wingstop Dallas. How can I help you.`, and publishes a startup snapshot.
8. Customer turns are handled by the LiveKit session and the assistant prompt.
   The model calls tools such as `set_customer_details`, `add_menu_item`,
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
- The reliability suite is offline and key-free, with 191 scenarios in the latest
  report.
- Live telemetry snapshots drive the current UI and include order/price/mock-order
  state, runtime profile, latency fields, and guardrail violations.
- The API already has useful dashboard primitives: calls, orders, analytics
  overview, and observability health.

## What Is Broken Or Missing Against The Brief

### Conversation Core

- Missing closed-set call intent router. The shared ordering package has
  `OrderIntent` for order mutations, but not the required call intents:
  `place_order`, `modify_order`, `track_order`, `cancel_order`, `store_info`,
  `speak_to_human`, `smalltalk_or_unknown`.
- Missing top-level call FSM. There is no explicit persisted
  `GREETING -> IDENTIFY -> ROUTE -> ORDER/TRACK/STORE_INFO/CANCEL/ESCALATE -> WRAPUP`
  graph.
- The current explicit state machine is order-lifecycle-only
  (`idle`, `greeting`, `collecting_order`, `pricing_order`,
  `awaiting_confirmation`, `completed`, etc.).
- There is no persisted current call node for reconnect resume.
- Greeting is deterministic on session start, but it is not caller-aware and does
  not branch for returning callers.
- Name capture exists as `set_customer_details`, but there is no confirmation
  flow, spelling fallback, or persisted customer profile.

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

- Persistence is SQLite only. There is no Postgres adapter, SQLAlchemy 2.x model
  layer, Alembic migration setup, or migration/seed command.
- The current SQLite schema has `orders`, `sessions`, and `calls`. It does not
  have the target `customers`, `stores`, `menu_items`, `order_items`,
  `transcript_turns`, `call_events`, or `escalations` tables.
- There is no `CustomerService`, `StoreService`, or full `OrderService` object
  layer. The FastAPI module owns most service behavior directly.
- Order lifecycle is stored as `submitted` only in persisted rows. The target
  lifecycle (`draft`, `confirmed`, `in_kitchen`, `ready`, `completed`,
  `cancelled`) and kitchen ticker do not exist.
- There is no returning-customer lookup by phone and no order rollup fields such
  as `order_count` or `total_spend`.

### Tracking, Cancel, Store Info

- There is a `GET /api/orders/{order_number}` endpoint, but no conversational
  tracking flow and no latest-active-order lookup by phone.
- Cancellation exists only for the in-memory active order before submission.
  There is no persisted order cancellation endpoint or server-owned transition.
- Store info is not backed by a `stores` table. Demo hours are static menu/domain
  data, not persisted store records.

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

- The reliability suite is healthy and broad for ordering, but it does not yet
  cover identification, tracking, persisted cancellation, store-info nodes,
  escalation monitor thresholds, idempotent confirm against the target service
  layer, or provider circuit breakers.
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

Phase 1 should build on the existing SQLite storage and `packages/ordering`
domain rather than replacing them casually. The safest next foundation is:

- introduce SQLAlchemy/Alembic and the target tables behind a service layer,
- preserve the current SQLite test/offline path,
- migrate current order/call behavior into services without changing the
  `runtime_config` contract or the three voice paths,
- add customer/store/order lifecycle primitives needed by Phase 2 routing.

The most important constraint for future phases is to put new call-level routing,
FSM, persistence, analytics, and escalation behind shared modules called by all
three voice paths. The current structure already has one shared assistant/tools
surface, but it does not yet have the explicit router/state-machine boundary the
brief requires.
