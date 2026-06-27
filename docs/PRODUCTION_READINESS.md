# VoixAI — Production Readiness & Target Architecture

Last reviewed: 2026-06-27

This is the bridge document between **where the code is today**
([ARCHITECTURE.md](./ARCHITECTURE.md)) and **the long-term platform vision**
([direction.md](./direction.md)). It is the answer to two questions:

1. What is actually wrong / risky right now, ranked?
2. What does the "proper version" look like, and in what order do we build it?

It is written to be defensible in an engineering interview: every fault points
at real code, and every fix is concrete.

---

## 1. The One-Paragraph Verdict

The MVP works and demos well: real LiveKit transport, three swappable voice
paths with graceful fallback, structured order state, tool-backed menu lookup,
and a clean telemetry-driven UI. But it is **not production-reliable** for a
real restaurant, because the three things that must be trustworthy in an
ordering system — *the menu/pricing source of truth, the "is this order
actually placeable" decision, and the placed order itself* — are respectively
(a) a Python file borrowed across process boundaries, (b) steered by prompt
instructions and boolean flags instead of a deterministic state machine, and
(c) a random number that is never stored. The roadmap below fixes those three
first, then adds the platform/observability layers.

---

## 2. What's Already Good (don't regress these)

- **Transport boundary is correct.** Browser → LiveKit → Python worker; no
  provider keys in the browser. ([app.tsx](../apps/web/components/app/app.tsx))
- **Menu/pricing is already reached through tools + HTTP**, not pasted into the
  prompt. The agent calls `/api/menu/*` for resolution, validation, and pricing.
- **Provider abstraction with fallback.** Classic/OpenAI/Gemini selectable per
  room, with missing-dependency fallback to classic and a recorded
  `fallback_reason`. ([agent.py:571-634](../apps/agent-runtime/src/agent.py))
- **Structured telemetry contract** drives the UI instead of scraping the
  transcript. ([useSessionTelemetry.ts](../apps/web/hooks/useSessionTelemetry.ts))
- **Scenario/channel registries** already exist, so multi-scenario is a real
  seam, not a rewrite. ([scenarios/base.py](../apps/agent-runtime/src/scenarios/base.py))

The job is not a rewrite. It is hardening the spine and extracting the domain.

---

## 3. Core Problems (detailed)

### 3.1 [CRITICAL] The menu/order domain is not a real backend service

**Evidence.** `apps/api/main.py` does not contain menu/pricing logic. It
*imports the runtime file* `apps/agent-runtime/src/scenarios/wingstop.py` at
startup by fabricating fake `livekit.agents`, `channels`, and `scenarios.base`
modules in `sys.modules` so the runtime file is importable outside a worker
([main.py:38-103](../apps/api/main.py)). The agent tools then HTTP-call the API
([wingstop.py:1319-1400](../apps/agent-runtime/src/scenarios/wingstop.py)), and
on any HTTP failure fall back to the **same** local functions
(`validate_order`, `build_price_quote`).

**Why it's wrong.**
- There is no independent source of truth. "Backend validation" and "runtime
  validation" are literally the same code reached two ways.
- The menu (~40 items, prices, modifier rules) is hard-coded as Python literals
  inside the agent scenario file. A menu change requires a code deploy of the
  *agent worker*.
- The import hack is brittle (depends on stub shapes matching the runtime's
  imports) and silently couples API deploys to runtime internals.
- It blocks everything the platform vision needs: per-client menus, DB-backed
  pricing, POS integration, admin editing.

**Fix.** Extract an ordering/menu **domain** that both apps consume. See §5.1.

### 3.2 [CRITICAL] Order placement is prompt-sequenced, not state-machined

**Evidence.** `create_mock_order` is gated by `_missing_confirmation_reasons`,
which checks booleans (`confirmed`, `total_shown`, `recap_readback`,
`pos_validation_passed`, `order_type`, pickup name)
([wingstop.py:1571-1585, 2096-2130](../apps/agent-runtime/src/scenarios/wingstop.py)).
Those booleans are set as side effects of *other* tools, and the only thing that
makes the LLM call them in the right order is the prompt's "Tool discipline"
section ([wingstop.py:1117-1148](../apps/agent-runtime/src/scenarios/wingstop.py)).
The `audit_assistant_response` guardrail is **regex on the assistant's text** and
only flags violations into telemetry — it never blocks speech
([wingstop.py:1681-1707](../apps/agent-runtime/src/scenarios/wingstop.py)).

**Why it's wrong.** With a realtime model (especially Gemini 3.1, which has
limited mid-session tool adherence), nothing *structurally* prevents the agent
from claiming an order is placed, quoting a price before pricing ran, or
skipping the recap. The booleans are a state machine in disguise, scattered
across tool bodies, with the transition rules living in English prose.

**Fix.** A real `OrderStateMachine` that owns transitions and is the *only* code
that can authorize submission; tools become guarded transitions; the auditor
becomes a hard pre-submit check. See §5.2.

### 3.3 [HIGH] No persistence — order state and placed orders are ephemeral

**Evidence.** `SessionState.order` lives in worker process memory
([agent.py:131-148](../apps/agent-runtime/src/agent.py)); `create_mock_order`
returns a random `MOCK-#####` and stores nothing
([wingstop.py:1646-1655](../apps/agent-runtime/src/scenarios/wingstop.py)).

**Why it's wrong.** A worker crash or reconnect loses the in-progress order. No
order history, no analytics, no idempotency, no way for a kitchen/POS to ever
see the order. Required for the `sessions`/`tool_calls`/`orders` tables in
direction.md §21.

**Fix.** Postgres-backed sessions/turns/orders + Redis for hot session/runtime
config. See §5.3.

### 3.4 [HIGH] Runtime config handed off via local JSON files

**Evidence.** API writes `.voixai/session-configs/<room>.json`; worker reads it
([main.py:375-392](../apps/api/main.py),
[agent.py:264-279](../apps/agent-runtime/src/agent.py)). Files are never deleted.

**Why it's wrong.** Only works when API and worker share a filesystem (single
host). Breaks on LiveKit Cloud / multi-instance / containers. Stale files cause
"works on my machine" config bugs; the fresh-room-per-order hack exists largely
to dodge this.

**Fix.** Pass config as **dispatch/room metadata** (LiveKit `RoomConfiguration`
already supports agent metadata) or a Redis key keyed by room. Remove the shared
filesystem assumption. See §5.4.

### 3.5 [HIGH] No auth, no rate limiting, permissive CORS on the token endpoint

**Evidence.** `POST /api/livekit/token` is unauthenticated; anyone who can reach
the API can mint a room-join JWT and dispatch an agent (which burns LLM/STT/TTS
spend). CORS allows methods/headers `*`
([main.py:247-254, 375-419](../apps/api/main.py)).

**Why it's wrong.** This is a direct cost/abuse vector and a hard blocker for any
multi-client deployment. direction.md §22 lists signed tokens, client isolation,
rate limiting as required.

**Fix.** Origin allowlist (already partial), per-IP/-client rate limit, a session
"intent" token or app-level auth, and client-scoped room naming. See §5.5.

### 3.6 [MEDIUM] God modules: `agent.py` (~1,070 lines) and `wingstop.py` (~2,150 lines)

**Evidence.** `agent.py` mixes env parsing, config dataclasses, provider
plumbing, session events, metric extraction, and telemetry. `wingstop.py` mixes
menu data, pricing math, validation, prompt text, serialization, and the agent
tools.

**Why it's wrong.** Hard to unit test in isolation, hard to add a second
scenario, high merge-conflict surface, and it hides the domain logic inside the
runtime (feeds 3.1).

**Fix.** Decompose into runtime modules (`config/`, `providers/`, `telemetry/`,
`session/`) and move domain logic into the shared package. See §5.6.

### 3.7 [MEDIUM] Observability/analytics/cost are not persisted

**Evidence.** Latency metrics are logged and pushed in telemetry but never
stored; there is no per-turn cost, no session record, no dashboard
([agent.py:357-396, 979-1033](../apps/agent-runtime/src/agent.py)).

**Why it's wrong.** Can't answer "what did this call cost / how did v1.3 compare
to v1.2 / why did this session fail." direction.md §16-17 require this.

**Fix.** Analytics event emitter → DB/warehouse; cost meter per provider; LiveKit
Cloud insights wired up. See §5.7.

### 3.8 [MEDIUM] Test coverage is unit-only

**Evidence.** Good focused unit tests on order logic; no cross-service
integration, no conversation/eval simulations, no browser E2E.

**Fix.** Contract tests for the menu/order API, a golden-conversation eval
harness (direction.md §18), and a Playwright happy-path. See §5.8.

### 3.9 [LOW] Demo data, mock placement, doc sprawl

- Menu/pricing/tax (8.25%) are demo constants, not POS-backed.
- `create_mock_order` is a placeholder with no idempotency key.
- `docs/` previously had overlapping planning/history files. The active docs set
  should stay limited to: ARCHITECTURE (current), PRODUCTION_READINESS (this),
  direction (vision), LOCAL_SETUP, ENVIRONMENT_VARIABLES, and the active
  scenario reference (`MOCK_MENU.md`).

---

## 4. Fault Register

| # | Sev | Area | Evidence | Fix (§) |
|---|-----|------|----------|---------|
| 3.1 | Critical | Domain not a real service (importlib hack) | main.py:38-103 | 5.1 |
| 3.2 | Critical | Prompt-sequenced placement, no state machine | wingstop.py:1571-1585, 2096-2130 | 5.2 |
| 3.3 | High | No persistence (order/placed order) | agent.py:131-148; wingstop.py:1646-1655 | 5.3 |
| 3.4 | High | Config via shared-filesystem JSON | main.py:375-392; agent.py:264-279 | 5.4 |
| 3.5 | High | Unauthenticated token endpoint | main.py:375-419 | 5.5 |
| 3.6 | Medium | God modules | agent.py / wingstop.py sizes | 5.6 |
| 3.7 | Medium | No persisted analytics/cost | agent.py:357-396 | 5.7 |
| 3.8 | Medium | Unit-only tests | tests/ | 5.8 |
| 3.9 | Low | Demo data / mock order / doc sprawl | wingstop.py menu literals | 5.9 |
| 3.10 | Low | Backend HTTP calls lack circuit breaker | wingstop.py `_backend_request_async` | Phase 7 |

---

## 5. Target Architecture (the "proper version")

```text
                          packages/ordering  (single source of truth)
                          ┌───────────────────────────────────────────┐
                          │  domain/                                    │
                          │    menu.py        (MenuRepository iface)    │
                          │    pricing.py     (pure pricing engine)     │
                          │    validation.py  (pure validators)         │
                          │    order_state.py (OrderState + StateMachine)│
                          │  schemas.py       (pydantic DTOs, shared)   │
                          │  repository/      (InMemory | Postgres)     │
                          └───────────────────────────────────────────┘
                                 ▲                         ▲
              import (in-proc)   │                         │  import (in-proc)
        ┌───────────────────────┴───────┐     ┌───────────┴───────────────────┐
        │  apps/api (FastAPI)            │     │  apps/agent-runtime            │
        │  • HTTP /api/menu/* /orders/*  │     │  • thin tool layer calls       │
        │  • auth, rate limit, persist   │     │    ordering domain directly    │
        │  • LiveKit token + dispatch    │     │    (or API in multi-host)      │
        └────────────────────────────────┘     │  • OrderStateMachine drives    │
                          ▲                     │    the conversation phases     │
                          │ HTTP (cross-host)   └────────────────────────────────┘
                          └─────────────────────────────────┘
```

Key decision: introduce a **`packages/ordering` Python package** that is the
single source of truth for menu, pricing, validation, and order state. Both the
API and the runtime depend on it as a normal package. This deletes the
`sys.modules` stub hack outright. The HTTP `/api/menu/*` endpoints stay (so the
runtime can call across hosts in production), but they become a thin transport
over the shared domain, and the *menu data itself* moves behind a
`MenuRepository` interface with `InMemory` (dev) and `Postgres` (prod)
implementations.

### 5.1 Extract the ordering domain (fixes 3.1)

- Create `packages/ordering/` with `domain/`, `schemas.py`, `repository/`.
- Move `MENU_ITEMS`, `FLAVOR_OPTIONS`, `MODIFIER_*`, pricing
  (`build_price_quote`, `_price_line_item`, tax), and validators
  (`validate_order`, `_validation_errors_for_line`) out of `wingstop.py`.
- `apps/api/main.py`: delete `_load_wingstop_backend_module`; `from ordering ...`.
- `wingstop.py`: keep only the `WingstopAssistant` tools + prompt; tools call the
  domain (in-proc) or the API (cross-host) behind one `OrderingClient` seam.
- Menu lives behind `MenuRepository`; ship `InMemoryMenuRepository` seeded from
  the current literals so behavior is unchanged on day one.

### 5.2 Real order state machine (fixes 3.2)

Define explicit phases (aligns with direction.md §9):

```text
GREETING → COLLECTING → PRICING → RECAP → AWAITING_CONFIRMATION → SUBMITTING → DONE
                ↑__________________________________|   (any mutation → COLLECTING)
ANY → CLARIFY / HANDOFF / SAFE_EXIT
```

- `OrderStateMachine` owns `state`, allowed transitions, and the
  `can_submit()` decision (replacing the scattered booleans).
- Tools become guarded transitions: `add_menu_item` forces state back to
  `COLLECTING`; `create_order` is *only* callable from `AWAITING_CONFIRMATION`
  and asks the machine, not the prompt.
- `audit_assistant_response` becomes a **hard pre-submit invariant check** and a
  pre-speech guard for price/placement claims, not a post-hoc flag.
- This makes reliability independent of model tool-adherence — the key
  engineering story.

### 5.3 Persistence (fixes 3.3)

- Postgres tables from direction.md §21: `sessions`, `session_turns`,
  `tool_calls`, `orders`. Add `orders` with an **idempotency key** so a retried
  `create_order` never double-submits.
- Redis for hot state: live `OrderState` snapshot keyed by room (so a worker
  reconnect can rehydrate) + runtime config (replaces §5.4 files).
- `create_order` writes a real `orders` row (status `submitted`) and returns its
  id; the `MOCK-` generator becomes a `MockPOSAdapter` behind a `POSClient`
  interface, ready to swap for a real POS.

### 5.4 Config handoff without shared FS (fixes 3.4)

- Put `runtime_config` in LiveKit dispatch/room metadata, or a Redis key
  `voixai:runtime:<room>` with a TTL. Worker reads metadata/Redis, not a file.
- Delete `.voixai/session-configs` and the implicit single-host assumption.
- Keep fresh-room-per-order (it's still good UX hygiene) but it's no longer a
  workaround for stale files.

### 5.5 API security (fixes 3.5)

- Require an app session token (or signed "start intent") on `/api/livekit/token`.
- Per-IP and per-client rate limiting (e.g. slowapi/Redis token bucket).
- Tighten CORS to the configured origins (drop `*` methods/headers).
- Namespace rooms by client (`<client_id>-<session_id>`) for isolation +
  per-client analytics.

### 5.6 Runtime decomposition (fixes 3.6)

`apps/agent-runtime/src/`:
```text
config/     settings.py, runtime_config.py   (env + per-room resolution)
providers/  pipeline.py, openai_realtime.py, gemini_live.py, registry.py
telemetry/  snapshot.py, metrics.py
session/    events.py, lifecycle.py
scenarios/  wingstop/  (tools.py, prompt.py, state_machine.py)
agent.py    (thin entrypoint wiring the above)
```

### 5.7 Analytics & cost (fixes 3.7)

- `AnalyticsEmitter` writes a `turn_completed` event per turn (transcripts +
  latency); `CostMeter` computes STT-seconds/LLM-tokens/TTS-chars → USD per
  provider (direction.md §16-17).
- Persist to `analytics_events` / `cost_events`; wire LiveKit Cloud insights.

### 5.8 Testing & evals (fixes 3.8)

- Contract tests for `/api/menu/*` and `/api/orders/*` against the domain.
- Golden-conversation eval harness (direction.md §18): scripted turns →
  assert state-machine outcomes (no hallucinated items, confirmation required,
  `create_order` not called early). Run on prompt/model changes.
- Playwright happy-path: start → order → confirm → confirmation screen.

### 5.9 Data & docs (fixes 3.9)

- Move menu seed to a `menu.yaml`/DB seed loaded by `MenuRepository`.
- Keep the docs set tight: this doc + ARCHITECTURE + direction are the strategy
  core, while LOCAL_SETUP, ENVIRONMENT_VARIABLES, and MOCK_MENU cover operation
  and the active scenario.

---

## 6. Remediation Roadmap (do in this order)

Each milestone is independently shippable and keeps the demo working.

| M | Goal | Fixes | Outcome | Status |
|---|------|-------|---------|--------|
| **M1** | Extract `packages/ordering`; delete importlib hack | 3.1, 3.6 (partial) | One source of truth; API decoupled from runtime internals | ✅ Done (2026-06-15) |
| **M2** | `OrderStateMachine` + hard pre-submit guard | 3.2 | Placement reliable regardless of model | ✅ Done (2026-06-15) |
| **M3** | Persist sessions/orders (idempotent), rehydrate state, config via metadata/Redis | 3.3, 3.4 | Survives restarts; real order records; multi-instance safe | 🟡 In progress |
| **M4** | Auth + rate limit + CORS + client-scoped rooms | 3.5 | Safe to expose; cost-abuse closed | |
| **M5** | Analytics + cost metering + LiveKit insights | 3.7 | Per-call cost, latency, completion visible | |
| **M6** | Eval harness + integration + E2E in CI | 3.8 | Prompt/model changes are regression-tested | |
| **M7** | Runtime decomposition; menu/POS adapters; client config layer | 3.6, 3.9, vision | Multi-client/multi-scenario platform per direction.md | |
| **--** | Circuit breaker + reliability suite expansion | 3.10 | Backend HTTP resilience; 201 scenarios pass | ✅ Done (2026-06-27) |

**M1 + M2 are complete.** They directly addressed the stated concern
("menu/order taking must live in the backend; stop relying on prompts"):

- M1: `packages/ordering` is now the single source of truth for menu, pricing,
  validation, order state, and the state machine. The API imports it directly;
  the `sys.modules` stub hack is deleted. The agent runtime's
  `scenarios/wingstop.py` is now a thin prompt/tools/telemetry layer over the
  same package.
- M2: `OrderStateMachine` (in `packages/ordering/src/voix_ordering/state_machine.py`)
  owns every order transition, and `authorize_submit()` is a hard gate that
  re-validates and re-checks confirmation on every placement attempt — so an
  order cannot be "placed" unless it is genuinely valid and confirmed,
  regardless of model tool-adherence. Order phase is now published in telemetry.
  The ordering package now also exposes a structured `OrderIntent` schema, a
  reducer for corrections/cancellations/restarts, reducer reliability events,
  replay support, and per-session reliability counters surfaced in the
  developer panel.

Tests: API 4/4, runtime `test_order_state.py` 36/36, domain
`packages/ordering/tests` 7/7. (`tests/test_agent.py` is a pre-existing stale
starter test unrelated to this work.)

**M3 is in progress.** Shipped this iteration:

- A storage **port** (`apps/api/storage.py`) with a SQLite adapter — durable
  with zero external infra (the local demo still needs no Postgres/Redis). A
  Postgres adapter is a drop-in via the same surface, gated on `DATABASE_URL`.
- `POST /api/orders` — **idempotent** order submission (unique idempotency key
  derived from room + canonical order; a retry returns the original order, never
  a duplicate) that **re-runs the submit gate server-side** as defense in depth,
  so the backend — not the model — is the authority on placement.
- `GET /api/orders/{order_number}` — read back a persisted order.
- The runtime `create_mock_order` tool now persists through the backend and
  falls back to a local order only if the backend is unreachable (resilient
  demo).
- Best-effort `sessions` row written on token mint.
- Tests: `apps/api/tests/test_orders.py` (idempotency, server-side gate,
  durability, read-back) — API suite now 10/10.

- **Config via dispatch metadata** — runtime config is now attached to the agent
  dispatch (`RoomAgentDispatch.metadata`) and read by the worker from
  `ctx.job.metadata`, removing the shared-filesystem requirement (3.4). The
  `.voixai/session-configs` file is still written as a single-host fallback, and
  the worker falls back to it if metadata is absent. (Final delivery to the
  worker needs a live LiveKit session to verify; the protos round-trip the field
  and the parse/fallback paths are unit-tested.)

Remaining for M3:

- **In-progress order rehydration** on worker reconnect (hot store).
- **Postgres adapter** behind `DATABASE_URL` for true multi-instance durability.
- Drop the `.voixai/session-configs` file fallback once metadata delivery is
  verified end-to-end against live LiveKit.

**Hardening program Phase 2 (conversation_core) is complete.** Shipped after the original M3 notes:

- Shared call-level `conversation_core` in `apps/agent-runtime` with the
  closed-set intent router and explicit top-level FSM.
- Deterministic startup `GREETING -> IDENTIFY -> ROUTE`, caller identification
  by phone, returning-caller greeting with latest-order summary, and confirmed
  name capture with spelling fallback.
- `call_sessions.current_node` persistence through thin conversation endpoints
  in `apps/api`, with reconnect-resume coverage.
- ORDER/TRACK/STORE_INFO/CANCEL/ESCALATE destination nodes are still stubs by
  design. Phase 3 attaches the real ORDER sub-FSM to the existing ORDER entry
  point; Phase 4 fills tracking, cancel, and store-info behavior.

**Hardening program Phase 7 (provider resilience) is complete.** Shipped after Phase 2:

- `CircuitBreaker` class in `conversation_core/circuit_breaker.py` with
  CLOSED/OPEN/HALF_OPEN states, configurable failure threshold (5),
  recovery timeout (30s jittered), half-open probe retries (3), and
  `call()`/`acall()` methods with fallback support.
- `with_retry()` decorator with exponential backoff + jitter in the same
  module.
- Circuit breaker wired into Wingstop's `_backend_request_async` HTTP layer,
  which covers menu resolution, pricing, and order submission. When the
  backend is unreachable (OPEN state), `_backend_request_async` raises
  `RuntimeError`, and the existing fallback in `create_mock_order` catches
  it to produce a local order — so the demo stays 100% available even when
  `apps/api` is down.
- Reliability suite expanded from 193 → 201 scenarios with 3 new Phase 7
  scenario groups (`split_flavor`, `mid_order_correction`, `idempotent_confirm`)
  in `tests/reliability/scenarios/phase7_scenarios.json`.
- NLU enhancements to the runner: `_is_ready_to_order()` handler routes
  "I'm ready to order" through the price+review flow; order placement
  correctly handles duplicate-confirmation guard.
- Concurrent load test at `tests/load_test_concurrent_orders.py` that
  simulates N sessions through the deterministic core (no LiveKit/audio/keys
  required). Sample: 50 sessions at concurrency 10 → 16.4 sessions/s,
  100% pass rate.

---

## 7. Definition of "Production Ready" (checklist)

- [x] Menu/pricing/validation live in one shared domain; no `sys.modules` hacks.
- [x] Order submission is authorized only by a state machine + invariant check,
      never by prompt sequencing; impossible to "place" an invalid/unconfirmed order.
- [x] Backend HTTP calls (menu, pricing, order submission) go through a
      configurable circuit breaker; backend failures cause graceful fallback to
      local logic, not cascading errors.
- [ ] Sessions, turns, tool calls, and orders persist to Postgres; orders are
      idempotent; in-progress state survives a worker reconnect.
- [ ] No shared-filesystem assumptions; runs on ≥2 worker instances unchanged.
- [ ] Token endpoint is authenticated, rate-limited, origin-scoped; rooms are
      client-isolated.
- [ ] Per-call latency + cost recorded; dashboard or LiveKit insights available.
- [ ] CI runs unit + API contract + golden-conversation eval + one E2E path.
- [ ] Menu is data-driven (DB/seed), and order submission targets a POS adapter
      interface (mock today, real later).
- [ ] Secrets via a secret manager; structured logs with PII redaction.
- [ ] Health checks, graceful shutdown, and alerts on worker/room/provider failure.
