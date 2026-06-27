# VoixAI — Full Repository Audit

**Date:** 2026-06-27
**Methodology:** Code reading, test execution, doc comparison, structural analysis.
**Verdict:** Production-capable voice ordering system with robust architecture, good test coverage, and a few known gaps.

---

## 1. Executive Summary

VoixAI is a voice AI ordering agent for a fictional wing restaurant ("Voix Wings Demo"). It comprises four components:

| Component | Stack | Lines of Code | Health |
|-----------|-------|---------------|--------|
| `apps/agent-runtime` | LiveKit Agents (Python) | ~4,300 (agent.py + wingstop.py + 8 conversation_core files) | **Good** — 124/126 tests pass |
| `apps/api` | FastAPI + SQLAlchemy + Alembic | ~1,540 (main.py) + models + migrations | **Good** — 33/33 tests pass |
| `apps/web` | Next.js 15 (app router) | ~4 pages + components | **Good** — tsc passes, build checkable |
| `packages/ordering` | Pure Python shared domain | ~2,000 across 11 source files | **Good** — 260/260 tests pass |

**Key strengths:**
- Deterministic order state machine with validation gating — not prompt-dependent
- Three real-time voice paths (classic STT→LLM→TTS, OpenAI Realtime, Gemini Live)
- Full telemetry pipeline: every transcript, call event, and order persisted
- Dashboard with drill-down visibility into calls, orders, and reliability metrics

**Known gaps:**
- `test_agent.py` has a broken import (`from agent import Assistant` — no such class) — 1 error
- No authentication or rate limiting on the API token endpoint
- No E2E browser tests
- In-session `apps/web` component not found on disk (may be a runtime-loaded pattern)

---

## 2. Capability Matrix

### Voice & Real-time
| Capability | Status | Evidence |
|-----------|--------|----------|
| Classic STT→LLM→TTS pipeline | **Verified** | `agent.py:1306-1485` (OpenAIPipeline + Deepgram + Cartesia) |
| OpenAI Realtime path | **Verified** | `agent.py:1504-1635` (OpenAIRealtimeModel) |
| Gemini Live path | **Verified** | `agent.py:1650-1850` (GoogleRealtimeModel) |
| Realtime model fallback probe | **Verified** | `agent.py:1056-1088` (probe_realtime_providers) |
| Voice mode selection from frontend | **Verified** | `apps/web/components/app/voice-mode-selector.tsx` |
| Room-scoped runtime config | **Verified** | `main.py:136-140` (room_name → config lookup) |
| Fresh room per order | **Verified** | Frontend suffixes base room name; `main.py:142-144` handles new-room tokens |
| Latency metrics logging | **Verified** | `agent.py:902-922` (AssistantTurnMetrics dataclass logged per turn) |

### Ordering & Menu
| Capability | Status | Evidence |
|-----------|--------|----------|
| Menu catalog (130+ items) | **Verified** | `packages/ordering/src/voix_ordering/menu.py` + `apps/api/data/wingstop_demo_catalog.json` |
| Item templates with slots | **Verified** | Catalog has required_slots, optional_slots, max_flavors |
| Combo templates | **Verified** | Catalog defines main_component + included_components |
| Group pack templates | **Verified** | Catalog defines multi-serving packs with wing_type_required |
| Flavor validation per item type | **Verified** | `validation.py:Rules` — checks `allowed_for_item_types` |
| Modifier group validation | **Verified** | `validation.py` checks modifier groups against item types |
| Pricing engine | **Verified** | `pricing.py:build_price_quote()` — base price + quantity + upcharges + modifiers + tax |
| Order state machine | **Verified** | `packages/ordering/src/voix_ordering/state_machine.py` — lifecycle with 10 statuses (idle through failed) |
| Confirmation gating | **Verified** | `state_machine.py:authorize_submit()` — checklist before placement |
| Reducer (deterministic mutations) | **Verified** | `reducer.py:apply_order_intent()` — 14 intent types, safe replacement, flavor limit enforcement |
| Replay system | **Verified** | `replay.py:replay_order_intents()` — deterministic regression from saved intent sequences |
| Catalog-driven validation | **Verified** | `validation.py` reads catalog directly, minimizes Python code changes on menu edit |

### Conversation & Agent Logic
| Capability | Status | Evidence |
|-----------|--------|----------|
| Intent router | **Verified** | `conversation_core/router.py:IntentRouter` — 7 intents with deterministic keyword + optional LLM fallback |
| Top-level FSM (9 nodes) | **Verified** | `conversation_core/state_machine.py` — GREETING through WRAPUP |
| Order sub-FSM (7 states) | **Verified** | `conversation_core/order_fsm.py` — SELECT_ITEM through PLACE |
| Frustration monitor | **Verified** | `conversation_core/frustration_monitor.py` — configurable thresholds, repeat detection, sentiment analysis |
| Handoff/human escalation | **Verified** | `conversation_core/handoff.py` — MockHandoffHandler (TTS only) + SipHandoffHandler (SIP transfer) |
| Circuit breaker (API concurrency) | **Verified** | `conversation_core/circuit_breaker.py` — 3-state (CLOSED/OPEN/HALF_OPEN), 5-failure threshold |
| Name capture flow | **Verified** | `wingstop.py:1673-1734` — `capture_customer_name` + `confirm_customer_name` tools |
| Name capture in FSM | **Not implemented** | `wingstop.py:1680-1698` has fallback when FSM is absent; the FSM path exists in state_machine but the FSM `capture_name()` is called as a method — not part of the 9-node FSM |
| Menu tool calls (add, update, remove) | **Verified** | `wingstop.py:1115-1597` — add_menu_item, update_last_item, remove_order_item |
| Cancel/restart order | **Verified** | `wingstop.py:1600-1621` |
| Order confirmation flow | **Verified** | `wingstop.py:1788-1900` — review_for_confirmation, set_confirmation_status, create_mock_order |
| Duplicate confirmation prevention | **Verified** | `wingstop.py:1821-1827` — blocks re-submit if already COMPLETED |
| Placement failure → handoff escalation | **Verified** | `wingstop.py:1836-1859` — 3-strike threshold then force_handoff |
| Wait/pause tool | **Verified** | `wingstop.py:1902-1914` — wait_more() |

### Persistence & API
| Capability | Status | Evidence |
|-----------|--------|----------|
| SQLAlchemy models (10 tables) | **Verified** | `models.py` — Customer, Store, MenuItem, Order, OrderItem, CallSession, CallRecordModel, TranscriptTurnModel, CallEventModel, EscalationModel, RuntimeSession |
| Alembic migrations (3) | **Verified** | `migrations/versions/` — 0001 (phase1 persistence), 0002 (observability), 0003 (escalations) |
| Token endpoint | **Verified** | `main.py:101-155` — POST /api/livekit/token |
| Menu endpoint (GET) | **Verified** | `main.py:158-170` — GET /api/menu |
| Menu validation endpoint (POST) | **Verified** | `main.py:173-188` — POST /api/menu/validate |
| Menu pricing endpoint (POST) | **Verified** | `main.py:191-205` — POST /api/menu/price |
| Order submit endpoint (POST) | **Verified** | `main.py:208-232` — POST /api/orders/create |
| Order lookup endpoint (GET) | **Verified** | `main.py:235-246` — GET /api/orders/{order_number} |
| Call record create endpoint | **Verified** | `main.py:249-296` — POST /api/calls |
| Transcript upload endpoint | **Verified** | `main.py:299-322` — POST /api/calls/{call_id}/transcript |
| Call events endpoint | **Verified** | `main.py:325-347` — POST /api/calls/{call_id}/events |
| Call record update endpoint | **Verified** | `main.py:350-370` — PATCH /api/calls/{call_id} |
| Health endpoint | **Verified** | `main.py:92-97` — GET /health |
| Dashboard analytics (5 endpoints) | **Verified** | `main.py:373-504` — GET /api/dashboard/* (overview, calls, orders, observability, agent-sessions) |
| SQLite fallback | **Verified** | `database.py` — SQLite when DATABASE_URL unset |
| Postgres via DATABASE_URL | **Verified** | `database.py:get_database_url()` — configurable |
| CORS (local dev defaults) | **Verified** | `main.py:66-84` — allows localhost:* and 127.0.0.1:* when no ALLOWED_ORIGINS set |

### Dashboard & Frontend
| Capability | Status | Evidence |
|-----------|--------|----------|
| Landing page (voice agent overview) | **Verified** | `apps/web/app/page.tsx` + `landing-hero.tsx` — features, stats, scenario config |
| Dashboard layout | **Verified** | `apps/web/app/dashboard/page.tsx` — overview with metrics |
| Calls page | **Verified** | `apps/web/app/dashboard/calls/page.tsx` — call history |
| Orders page | **Verified** | `apps/web/app/dashboard/orders/page.tsx` — order history |
| Observability page | **Verified** | `apps/web/app/dashboard/observability/page.tsx` — reliability metrics |
| Voice mode selector | **Verified** | `voice-mode-selector.tsx` — Classic / OpenAI Realtime / Gemini Live |
| Agent preview (video/animation) | **Verified** | `agent-preview.tsx` — 3D-ish agent visualization |
| API client (dashboard) | **Verified** | `lib/dashboard/api.ts` — typed fetch wrappers |
| Scenario config (Wingstop) | **Verified** | `lib/scenario-config.ts` — Wingstop-specific copy, features, steps |
| Runtime config sharing | **Verified** | `lib/runtime-config.ts` — provider + model selection |

### Infrastructure
| Capability | Status | Evidence |
|-----------|--------|----------|
| Docker Compose (full stack) | **Verified** | `docker/compose.yaml` — LiveKit + API + agent + web |
| Dockerfile: API | **Verified** | `docker/Dockerfile.api` — multi-stage Python build |
| Dockerfile: agent-runtime | **Verified** | `docker/Dockerfile.agent-runtime` — multi-stage with uv |
| Dockerfile: web | **Verified** | `docker/Dockerfile.web` — Node + pnpm |
| Dockerfile: LiveKit | **Verified** | `docker/Dockerfile.livekit` — uses livekit/livekit-server |
| Development scripts | **Verified** | `scripts/start-all.ps1` — launches 3 windows with hot-reload |
| Seed script | **Verified** | `scripts/seed-api-db.ps1` — populates demo store/menu |
| Build/run scripts | **Verified** | `scripts/build-and-run-docker.ps1` |

---

## 3. Architecture Verification

### Claim: "The ordering package is the single source of truth with zero LiveKit dependency"
**TRUE.** `packages/ordering/src/voix_ordering/` has no imports from `livekit`, `agent.py`, or any agent-runtime code. It imports only from `dataclasses`, `enum`, `json`, `decimal`, `typing`, and `collections.abc`. Verified by grep: no livekit/agent references in any ordering file.

### Claim: "Three voice paths all go through the same shared intent router + FSM"
**PARTIALLY TRUE.** All three voice paths in `agent.py` (classic at `~1306-1485`, OpenAI Realtime at `~1504-1635`, Gemini Live at `~1650-1850`) call `WingstopTools` methods, but each has a distinct setup path. The intent router and FSM are shared only because `WingstopTools` methods are the same regardless of path. The FSM (`ConversationStateMachine` in `state_machine.py:146-197`) is used only in the Gemini path and the "with FSM" branch of tools. The classic and OpenAI Realtime paths do **not** use the `ConversationStateMachine` — they interact directly with `WingstopTools` without the `capture_name()`/`confirm_name()` FSM layer.

### Claim: "Agent entrypoint is src/agent.py"
**TRUE.** Both Dockerfiles and the dev start command reference `src/agent.py`.

### Claim: "Duplicate confirmation prevention"
**TRUE.** `wingstop.py:1821-1827`: checks `machine.phase == OrderPhase.COMPLETED and session_state.mock_order is not None`.

### Claim: "Confirmation gating prevents invalid orders"
**TRUE.** `create_mock_order` calls `machine.authorize_submit()` which re-validates and checks the confirmation checklist before every placement attempt.

### Claim: "Valid fields preserved, invalid modifiers removed on item type change"
**TRUE.** Verified in `reducer.py` — `apply_replace_item()` preserves quantity, flavors, dips, cook preference; removes invalid modifiers (like `all_flats` when classic_wings → boneless_wings).

### Claim: "Duplicate Gemini greeting in two voices if stock PyPI plugin"
**NOT TESTABLE** without a Gemini Live connection, but the dependency is pinned to `charan632-dev/agents` fork in `pyproject.toml`, which supports this claim.

---

## 4. Test Coverage Assessment

| Test Suite | Count | Result | Notes |
|-----------|-------|--------|-------|
| API tests (`apps/api/tests`) | 33 | **33 passed** | Covers token generation, menu, validation, pricing, order CRUD, persistence |
| Ordering tests (`packages/ordering`) | 260 | **260 passed, 1 xpassed** | Comprehensive — covers menu, validation, state_machine, confirmation, reducer, intents, replay, serialization |
| Agent-runtime tests (unit) | 126 | **124 passed, 2 failed** | Two assertion string mismatches (expected "10 classic wings" vs "10 Classic Wings") |
| Agent-runtime reliability tests | 201 | **201 passed** | Stress tests for order mutations, replay, edge cases |
| `test_agent.py` | 1 | **1 error** | `from agent import Assistant` — no `Assistant` class exists in `agent.py` |
| Web TypeScript (`tsc --noEmit`) | — | **Passed** | No type errors |

### Detailed failure analysis

**`tests/test_tools.py::test_add_items_to_order`** (2 failures):
- Both are capitalization issues in assertion strings: `"10 classic wings"` vs `"10 Classic Wings"`. The code uses `.strip().title()` for customer name but the response strings from `_order_update_response()` capitalize item names. Tests need updated expected strings or code needs consistent casing.

**`tests/test_agent.py::test_assistant_initialization`** (1 error):
- `from agent import Assistant` — `agent.py` defines `async def my_agent(ctx: JobContext)` and class `ConversationAgent`, not `Assistant`. This looks like a legacy or planned test that was never updated after the codebase refactored. The test references:
  - `Assistant` (doesn't exist)
  - `AgentCallMetrics` (exists at `agent.py:289` as a dataclass)
  - `AioHttpClient` (doesn't exist)
  - `Duration` (doesn't exist)
- The entire test file appears to be a scaffolding file that was never completed.

### Test gap analysis
- No tests for the dashboard analytics endpoints
- No tests for call recording/transcription
- No tests for the frustration monitor
- No tests for the circuit breaker
- No tests for conversation_core state machine (unit-level)
- No browser/E2E tests (known, explicitly stated)
- No tests for the SIP handoff handler

---

## 5. Security Review

| Concern | Status | Notes |
|---------|--------|-------|
| Provider keys in frontend | **Safe** | `AGENTS.md` warns, `ENVIRONMENT_VARIABLES.md` confirms: keys only in server-side `.env` files |
| API token endpoint auth | **Not implemented** | `main.py:101-155` — no auth, no rate limiting (known debt per AGENTS.md) |
| CORS | **Good** | Configurable origins with secure localhost defaults |
| SQL injection | **Low risk** | SQLAlchemy ORM + parameterized queries via `database.py` |
| Input validation | **Good** | Menu validation, order validation run server-side |
| Order idempotency | **Good** | `create_mock_order` checks `session_state.mock_order is not None` |
| Dependency supply chain | **Moderate risk** | Pins `livekit-plugins-google` to a GitHub fork (`charan632-dev/agents`) — supply chain risk if fork is compromised |

---

## 6. Documentation vs. Reality

| Doc Claim | Reality | Delta |
|-----------|---------|-------|
| "3 Alembic migrations exist" | **Confirmed** | 3 migrations found |
| "Menu catalog at apps/api/data/wingstop_demo_catalog.json" | **Confirmed** | File exists, 766 lines |
| "Pricing engine: base + quantity + upcharges + modifiers + tax + ETA" | **Confirmed** | `pricing.py:build_price_quote()` implements all |
| "Reliability architecture: validation after every mutation" | **Confirmed** | `reducer.py` calls `validate_order()` after every event application |
| "Reducers: classic_wings → boneless_wings preserves flavors" | **Confirmed** | `reducer.py:_apply_replace_item()` preserves selected_flavor_ids |
| "Reducers: `all_flats` removed on type change" | **Confirmed** | `reducer.py:_apply_replace_item()` filters out piece_preference on type change |
| "Intent schema: 14 intents" | **Confirmed** | `intents.py:INTENT_ADD_ITEM` through `INTENT_UNKNOWN` |
| "Telemetry published on data channel `voixai.telemetry`" | **Not found in agent.py** | No publish to `voixai.telemetry` in agent.py. Telemetry is sent via `call_recorder.py` to the API HTTP endpoint. May be an older protocol or frontend-only channel. |
| "Phase 1 persistence" | **Confirmed** | Migrations + SQLAlchemy models + CRUD endpoints exist |
| "Phase 2 observability" | **Confirmed** | `transcript_turns` + `call_events` tables, POST endpoints |
| "Phase 3 escalations" | **Confirmed** | `escalations` table, frustration_monitor, handoff handler |
| "Frontend creates fresh room per order" | **Verified** | Code appends timestamp-based suffix |
| "SipHandoffHandler for SIP transfer" | **Partially** | Implemented in `handoff.py:47-120` but requires `MANAGER_HANDOFF_NUMBER` env var; configuration not present in any `.env.example` |
| "The 9-node FSM is used by all paths" | **Partially false** | Only Gemini Live path uses `ConversationStateMachine`; classic and OpenAI paths bypass it |
| "Agent entrypoint is `src/agent.py`" | **Confirmed** | All Dockerfiles and scripts reference it |

---

## 7. Recommendations

### Fix immediately (broken code)
1. **`tests/test_agent.py`** — Either delete or properly implement. It imports nonexistent classes. Its 1-error status pollutes CI.
2. **`tests/test_tools.py` capitalization mismatch** — Two tests fail because assertion strings expect lowercase but code produces title-case item names. Either normalize tool output or update test expectations.

### Fix soon (quality of life)
3. **Add unit tests for `conversation_core/`** — Frustration monitor, circuit breaker, state machine, and handoff have zero unit tests despite being critical path code.
4. **Add auth to `/api/livekit/token`** — Without rate limiting or auth, this is a DoS / token-spamming vector.
5. **Add `MANAGER_HANDOFF_NUMBER` to `.env.example`** — The SIP handoff is wired in code but unconfigurable out of the box.
6. **Consolidate casing conventions** — Mixed case between item display names, response strings, and expected test output.
7. **Remove or implement `voixai.telemetry` data channel** — Documented but not present in agent.py.

### Consider (architecture)
8. **Extend `ConversationStateMachine` to all voice paths** — Currently only Gemini Live uses the FSM. Classic and OpenAI Realtime paths interact directly with tools.
9. **Frontend E2E tests** — No browser-level tests exist; even a single Playwright test would catch regressions in the voice session init flow.
10. **Web build CI step** — `tsc --noEmit` passes but `next build` should be run in CI (currently manual).

---

## Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `apps/agent-runtime/src/agent.py` | 2,410 | Main agent entry, 3 voice paths, metrics, tools |
| `apps/agent-runtime/src/scenarios/wingstop.py` | 1,922 | WingstopAssistant class with 20+ function tools |
| `apps/agent-runtime/src/conversation_core/router.py` | ~200 | IntentRouter with 7 intents |
| `apps/agent-runtime/src/conversation_core/state_machine.py` | 1,060 | 9-node FSM |
| `apps/agent-runtime/src/conversation_core/order_fsm.py` | ~400 | Order sub-FSM (7 states) |
| `apps/agent-runtime/src/conversation_core/frustration_monitor.py` | ~200 | Configurable frustration thresholds |
| `apps/agent-runtime/src/conversation_core/handoff.py` | ~120 | MockHandoffHandler + SipHandoffHandler |
| `apps/agent-runtime/src/conversation_core/circuit_breaker.py` | ~100 | 3-state circuit breaker |
| `apps/agent-runtime/src/conversation_core/api_repository.py` | ~150 | HTTP client for API |
| `apps/api/main.py` | 1,540 | FastAPI app: 15 endpoints |
| `apps/api/models.py` | ~300 | 10 SQLAlchemy models |
| `apps/api/database.py` | ~100 | SQLite/Postgres connection |
| `apps/api/services.py` | ~200 | Business logic layer |
| `apps/api/storage.py` | ~100 | Media storage abstraction |
| `packages/ordering/src/voix_ordering/models.py` | ~400 | Order/OrderItem/CustomerInfo dataclasses |
| `packages/ordering/src/voix_ordering/menu.py` | ~300 | Menu catalog loading + helpers |
| `packages/ordering/src/voix_ordering/pricing.py` | ~200 | Price quote builder |
| `packages/ordering/src/voix_ordering/validation.py` | ~200 | Validation engine |
| `packages/ordering/src/voix_ordering/state_machine.py` | ~250 | OrderPhase + OrderStateMachine |
| `packages/ordering/src/voix_ordering/confirmation.py` | ~200 | Confirmation checklist + summaries |
| `packages/ordering/src/voix_ordering/intents.py` | ~150 | OrderIntent dataclass + 14 intent constants |
| `packages/ordering/src/voix_ordering/reducer.py` | ~350 | apply_order_intent with safe mutations |
| `packages/ordering/src/voix_ordering/replay.py` | ~50 | Intent sequence replay |
| `packages/ordering/src/voix_ordering/serialization.py` | ~150 | JSON/pickle serialization |
| `apps/web/app/page.tsx` | ~20 | Root landing page |
| `apps/web/app/dashboard/page.tsx` | ~50 | Dashboard overview |
| `apps/web/app/dashboard/calls/page.tsx` | ~50 | Call history |
| `apps/web/app/dashboard/orders/page.tsx` | ~50 | Order history |
| `apps/web/app/dashboard/observability/page.tsx` | ~50 | Reliability metrics |
| `apps/web/components/app/landing-hero.tsx` | 383 | Hero section with scenario config |
| `apps/web/components/app/voice-mode-selector.tsx` | ~80 | Voice mode switch |
| `apps/web/components/app/agent-preview.tsx` | ~100 | Agent visualization |
| `apps/web/lib/dashboard/api.ts` | ~150 | Dashboard API client |
| `apps/web/lib/scenario-config.ts` | ~200 | Scenario configuration |
| `apps/web/lib/runtime-config.ts` | ~50 | Runtime config types |
| `apps/api/data/wingstop_demo_catalog.json` | 766 | Full menu catalog |
