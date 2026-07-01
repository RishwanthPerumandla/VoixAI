# VoixAI — Engineering Build Brief (for Claude Code / Codex)

> **You are working on VoixAI**, a production-style voice-AI platform built around a LiveKit
> room, a Python LiveKit voice agent (`apps/agent-runtime`), a FastAPI token/session service
> (`apps/api`), and a Next.js customer-facing UI (`apps/web`). The live use case is **Wingstop
> inbound phone ordering**. This brief defines a hardening + feature program plus a public
> landing page. Read it fully before writing code.

---

## 0. Rules of engagement (read first, follow always)

1. **Audit before you rewrite.** Start by reading `README.md`, everything in `docs/`, and the
   three voice paths in `apps/agent-runtime`. Produce a short `docs/CURRENT_STATE_AUDIT.md`
   describing what actually exists, what is broken, and the real call flow today. Do not assume
   the README is accurate — verify against code.
2. **Keep the reliability suite green at all times.** After every change run:
   ```powershell
   cd apps/agent-runtime
   .venv\Scripts\python.exe -m pytest tests/reliability -q
   ```
   A change that reds the suite is not done. When you add behavior, add scenarios.
3. **Do not break the three existing voice paths** (`classic`, `openai_realtime`,
   `gemini_live`). They must keep working through the same `runtime_config` contract. New
   behavior (router, state machine, persistence, analytics) must sit *behind* a shared layer
   that all three paths call, not be wired into one path only.
4. **Deterministic core, LLM at the edges.** Menu resolution, validation, pricing, order state
   transitions, and tracking must be deterministic and unit-testable **without** LiveKit, audio,
   or API keys (same philosophy as the current reliability suite). The LLM/voice layer only
   produces *intents* and *slots*; it never owns truth.
5. **Small, reviewable phases.** Work phase by phase (Section 11). One coherent PR per phase,
   conventional-commit messages, no giant mixed diffs. Update the relevant `docs/*.md` in the
   same PR. Never delete a doc without replacing it.
6. **Ask before destructive or irreversible moves** (dropping tables/migrations, deleting voice
   paths, swapping a provider SDK). Otherwise proceed autonomously.
7. **Secrets via env only.** Nothing real in the repo. Extend `.env.example` and
   `docs/ENVIRONMENT_VARIABLES.md` for every new variable.

---

## 1. Mission & why this project exists

VoixAI is a personal engineering showcase. The goal is to prove I can ship a **reliable, scalable,
observable agentic voice system** — not a toy demo. Wingstop inbound ordering was chosen on
purpose because it is a genuinely hard conversational domain:

- A large menu where most items are **configurable**: wing **count**, **flavor(s)** (often split
  across one order: "half lemon pepper, half hot"), **wet vs dry**, **well-done**, bone-in vs
  boneless, **combos**, **sides**, **dips/extra dips**, **drinks**.
- Messy real speech: corrections, cancellations mid-order, ambiguous phrasing, bilingual turns,
  re-pricing as the order changes, and customers who get frustrated.
- Multiple inbound reasons on the same line: new order, **track an existing order**, store
  questions, cancellation, "let me talk to a person."

Everything below should reinforce three claims a visitor/recruiter can verify: **(a) it is
reliable** (deterministic core + test suite + graceful degradation), **(b) it scales**
(stateless workers, idempotency, provider fallback), and **(c) it is genuinely agentic** (intent
routing + a real state machine + escalation, not a single mega-prompt).

There are two tracks. They can be executed by **separate agent sessions**:

- **Track A — System** (Sections 3–9): conversation core, backend + DB, identity & tracking,
  observability, frustration escalation, reliability/scale.
- **Track B — Landing page** (Section 10): a modern, professional public site.

---

## 2. What is broken / missing today (target outcomes)

| # | Symptom today | Target outcome |
|---|---------------|----------------|
| 1 | Greeting unreliable / doesn't fire cleanly | Deterministic greeting on session start, branded, branches on new vs returning caller |
| 2 | Name capture broken | Robust name slot-filling with confirmation + spelling fallback; persisted to customer record |
| 3 | Order taking unreliable | Slot-filling sub-FSM that handles count/flavor/wet-dry/well-done/combo/sides/drinks/dips with read-back and confirmation gate |
| 4 | No returning-customer / tracking flow | Caller identified by phone; "track my order" returns real status + ETA from DB |
| 5 | Weak/absent backend + DB | Postgres-backed services with migrations; deterministic ordering core is source of truth |
| 6 | No intent router | Routing layer that classifies each inbound call and dispatches to the right state-machine node |
| 7 | No transcripts/recordings/analytics persisted | Per-call transcript turns, call recordings via egress, order value + call analytics in DB and queryable |
| 8 | No human handoff | Frustration/repetition detection → escalate to manager (warm transfer or flagged handoff) |

---

## 3. Target architecture

```
 Browser (apps/web)                FastAPI (apps/api)               Postgres
 ┌───────────────────┐  POST       ┌──────────────────────┐        ┌──────────────┐
 │ voice UI + landing │ /token ───▶ │ token + dispatch     │ ─────▶ │ customers    │
 │ live transcript    │ ◀───────── │ session-config writer │        │ orders/items │
 │ order summary      │            │ analytics read API    │ ◀───── │ call_sessions│
 └─────────┬─────────┘            └──────────┬───────────┘        │ transcripts  │
           │ join room                        │ dispatch           │ call_events  │
           ▼                                  ▼                    │ escalations  │
        LiveKit room ◀──── telemetry ──── apps/agent-runtime ──────┴──────────────┘
                                          ┌───────────────────────────────────┐
                                          │ Voice session (classic / oai / gem) │
                                          │   ▼ emits intents + slots           │
                                          │ Router → State Machine              │
                                          │   ▼ calls                           │
                                          │ Ordering Core (menu/validate/price) │  ← deterministic, key-free
                                          │ Persistence + Telemetry + Egress    │
                                          │ Frustration Monitor → Escalation    │
                                          └───────────────────────────────────┘
```

**Layering rule:** voice path → router → state machine → ordering core / persistence. The three
voice paths differ only in how audio→text→intent is produced. Everything from "intent + slots"
downward is shared, deterministic where possible, and independently testable.

Recommended stack additions (use what already exists where possible):
- **DB:** Postgres (prod/dev) via SQLAlchemy 2.x + Alembic migrations. **SQLite** for the
  deterministic test suite so tests stay key-free and fast.
- **Recordings:** LiveKit Egress → S3-compatible storage (MinIO locally), URL stored on the call.
- **Analytics:** event rows in `call_events` + materialized summary endpoints in `apps/api`.

---

## 4. Workstream A — Conversation core: router + state machine

### 4.1 Intent router (the missing layer)

Add a routing layer that runs on each meaningful caller turn and on call start. It classifies into
a **closed set of intents** and returns a confidence + extracted slots. Implementation: a small,
deterministic dispatcher fed by (a) explicit keyword/grammar rules and (b) an LLM classifier
constrained to the enum. Rules win on high-signal phrases ("track my order", "talk to a manager").

Intent enum:
```
place_order | modify_order | track_order | cancel_order |
store_info | speak_to_human | smalltalk_or_unknown
```
Router contract (must be unit-testable with fixed transcripts, no API key):
```python
RouterResult(
    intent: Intent,
    confidence: float,        # 0..1
    slots: dict,              # e.g. {"order_code": "WS-4821", "phone": "..."}
    requires_disambiguation: bool,
)
```

### 4.2 State machine

Implement an explicit FSM (a small library or hand-rolled `StateNode` objects), not branching
prompt logic. Each node declares: `on_enter`, `allowed_intents`, `transitions`, and the
telemetry it emits. Persist current node on the `call_session` so a reconnect resumes correctly.

Top-level nodes:
```
GREETING → IDENTIFY → ROUTE → { ORDER | TRACK | STORE_INFO | CANCEL | ESCALATE } → WRAPUP
```

- **GREETING** — deterministic branded open; immediately attempts caller identification.
- **IDENTIFY** — resolve caller by phone (LiveKit participant identity / caller-ID slot). If found,
  greet by name and surface their last order; else mark as new.
- **ROUTE** — call the router; dispatch. Low confidence → one clarifying question, then re-route.
- **ORDER** (sub-FSM, see 4.3).
- **TRACK** — collect order code or fall back to phone lookup; read back status + ETA from DB.
- **STORE_INFO** — answer hours/location/availability deterministically from the `stores` + menu
  data. Never hallucinate hours.
- **CANCEL** — look up order, confirm identity, confirm cancellation (gate), transition order to
  `cancelled`, read back.
- **ESCALATE** — see Workstream E.
- **WRAPUP** — summary + goodbye; finalize the call session record.

### 4.3 ORDER sub-FSM (the hard part — make this excellent)

```
SELECT_ITEM → CONFIGURE_ITEM → (loop back for more items) → ADD_SIDES → ADD_DRINKS
            → REVIEW → CONFIRM(gate) → PLACE
```
`CONFIGURE_ITEM` must drive slot-filling against the menu's option schema, asking only for
**missing required** options and never re-asking a filled slot:
- `count` (e.g. 6/8/10/12/16/24…)
- `bone_in | boneless`
- `flavor(s)` — support **split flavors** with proportions ("half X, half Y")
- `wet | dry`
- `well_done` (bool)
- `combo` (adds a side + drink at combo price) vs à la carte
- `dips` / extra dips
- per-item `notes`

Behavior requirements:
- **Read-back + confirmation gate** before `PLACE`. No order is created without an explicit yes.
- **Live re-pricing** after every mutation; price comes only from the ordering core.
- **Corrections** ("actually make those boneless", "change the Coke to a Sprite") update the right
  slot/line without restarting the order.
- **Invalid modifiers** ("ranch on the fries as a flavor") are rejected gracefully with a valid
  alternative offered — deterministic validation, not the LLM guessing.
- **Cancellation mid-order** unwinds cleanly to ROUTE.
- Confirmed orders persist via the order service and produce a human-readable `public_code`
  (e.g. `WS-4821`) read back to the caller for later tracking.

The ordering core (menu resolution, validation, pricing) already exists as "shared deterministic
ordering logic" — **reuse and extend it; do not move truth into prompts.**

---

## 5. Workstream B — Backend + data model

Add a real persistence layer in `apps/api` (owns the DB; the runtime talks to it via internal
service calls or a thin internal client). Use SQLAlchemy + Alembic. Provide a `make`/script
target to run migrations and seed the menu + a demo store.

### 5.1 Schema (minimum)

```sql
customers(
  id, phone UNIQUE, name, preferred_language,
  order_count, total_spend, created_at, last_seen_at
)

stores(
  id, name, address, phone, timezone,
  hours JSONB,            -- per-day open/close
  is_open_now BOOL        -- derived, do not trust client
)

menu_items(                -- mirror of deterministic core for read/reporting
  id, sku, name, category, base_price, is_available,
  options_schema JSONB     -- required/optional config per item
)

orders(
  id, public_code UNIQUE, customer_id FK, store_id FK,
  status,                  -- enum below
  channel,                 -- 'voice'
  subtotal, tax, total, currency,
  eta_minutes, placed_at, updated_at,
  source_call_id FK
)
-- status: draft → confirmed → in_kitchen → ready → completed
--                          ↘ cancelled

order_items(
  id, order_id FK, menu_item_id FK, name,
  quantity, unit_price, line_total,
  modifiers JSONB,         -- {bone_in, flavors:[{flavor,share}], wet_dry, well_done, combo, dips, notes}
)
```

### 5.2 Services / internal API (FastAPI)

- `OrderService`: create draft, mutate lines, reprice, confirm (idempotent on `public_code`),
  cancel, get-by-code, get-latest-by-phone.
- `CustomerService`: upsert by phone, attach name, roll up `order_count`/`total_spend`.
- `StoreService`: hours, open-now, availability.
- All write paths **idempotent** and safe to retry (the agent may reconnect). Confirming the same
  order twice must not create two orders.

---

## 6. Workstream C — Caller identity, order lifecycle & tracking

- **Identity:** derive caller phone from the LiveKit participant identity / a `caller_id` slot in
  `runtime_config`. Upsert customer on `IDENTIFY`. Returning callers get a personalized greeting and
  "your last order was …".
- **Tracking flow:** accept `public_code` directly, or look up the **most recent active order by
  phone** if the caller can't recite a code. Read back status + ETA in plain language. If multiple
  active orders, disambiguate by time/total.
- **Order lifecycle** transitions are server-owned and validated (no skipping states). A demo
  "kitchen ticker" job can advance `confirmed → in_kitchen → ready → completed` on timers so
  tracking has live-looking data for the demo.

---

## 7. Workstream D — Observability: transcripts, recordings, analytics

This is a core part of the showcase — make the data **persisted and queryable**, then surfaced.

### 7.1 Transcripts
- Persist **per-turn** rows: `transcript_turns(call_id, seq, speaker, text, ts_start, ts_end,
  stt_confidence, state_node, intent)`. Works for all three voice paths (realtime models expose
  transcription events; the classic path uses STT output).
- The frontend already renders a live transcript — additionally persist it so it survives the call.

### 7.2 Recordings
- Enable **LiveKit Egress** (room composite or track) to S3-compatible storage (MinIO in
  `docker/`), store the resulting URL/key on `call_sessions.recording_url`. Make it toggleable via
  env (`ENABLE_RECORDING`) and documented for privacy.

### 7.3 Analytics
- Write granular `call_events(call_id, ts, type, payload)` rows: `state_enter`, `slot_filled`,
  `validation_error`, `reprice`, `confirmation`, `escalation_trigger`, `provider_error`,
  `latency_sample` (capture STT/LLM/TTS turn latency).
- Expose read endpoints in `apps/api` for a dashboard:
  - **Per call:** intent, outcome (`completed | escalated | abandoned`), duration, order value,
    final sentiment, recording + transcript links.
  - **Aggregate:** call volume, **containment rate** (resolved without human), **escalation rate**,
    **order completion rate**, **AOV (average order value)**, abandonment, p50/p95 turn latency,
    intent distribution.
- These metrics double as the numbers the landing page shows.

---

## 8. Workstream E — Frustration / repetition detection → manager escalation

Add a **FrustrationMonitor** that runs over the live call and emits a rolling score. Escalate when
the score crosses a threshold **or** any hard trigger fires.

Hard triggers (immediate):
- Explicit request: "manager", "human", "representative", "real person", profanity directed at the
  agent.

Soft signals (accumulate into a score):
- Same slot corrected ≥ 2 times ("no, *boneless*" repeated).
- Same state node re-entered ≥ 3 times (loop detection — "the order feels repetitive").
- Streak of low-confidence STT / repeated "what?" / "I didn't catch that".
- Negative sentiment over a rolling window.
- Call duration past a threshold with no order progress.

On escalation:
1. Write an `escalations` row (`call_id`, `reason_code`, `frustration_score`, `triggered_at`).
2. Emit `escalation_trigger` analytics event; set `call_session.outcome = 'escalated'`.
3. Hand off: **warm transfer** via LiveKit SIP to a manager number if configured
   (`MANAGER_HANDOFF_NUMBER`), otherwise play a graceful "let me get a team member" message and
   flag the call for human follow-up. Make the mechanism pluggable so the demo works without real
   telephony.

All thresholds live in config and are covered by deterministic tests (feed transcripts that should
and should not escalate).

---

## 9. Workstream F — Reliability & scale (the proof)

- **Stateless workers:** agent-runtime instances hold no cross-call state; everything durable is in
  Postgres / room config. Multiple workers can serve dispatched jobs.
- **Idempotency** on every write path (Section 5.2).
- **Provider resilience:** wrap STT/LLM/TTS and realtime providers with timeouts, retries with
  jitter, and a **circuit breaker**; on failure, degrade gracefully (e.g. classic path falls back to
  a backup TTS; realtime path falls back to classic) and log a `provider_error` event rather than
  dropping the call.
- **Expand the reliability suite:** add scenario groups for the new flows — identification, tracking,
  cancellation, store-info, escalation triggers (positive + negative), split-flavor orders,
  mid-order correction, idempotent confirm. Keep it key-free and offline.
- **Load test:** add a script under `scripts/` that simulates N concurrent ordering sessions against
  the deterministic core + API (no audio) and reports throughput, error rate, and p95 latency.
  Capture the numbers for the landing page.
- Document all of this in `docs/RELIABILITY_TESTING.md` and `docs/PRODUCTION_READINESS.md`.

---

## 10. Track B — Landing page (modern, professional, recruiter-grade)

Build inside `apps/web` (Next.js + TypeScript + Tailwind + shadcn/ui + Framer Motion, matching the
existing stack). **Before building UI, read `/mnt/skills/public/frontend-design/SKILL.md`** (or the
project's design tokens) and commit to one intentional visual direction — do not ship default
template styling.

**Audience:** engineering recruiters, hiring managers, and technical peers. Tone: confident,
precise, "this is real infrastructure," not marketing fluff.

**Visual direction:** dark, premium, technical. A restrained accent (Wingstop-adjacent warm
red/orange is fine as a single accent, not a theme). Strong type scale, generous spacing, subtle
motion on scroll (Framer Motion), real diagrams over stock art, monospace for technical labels.
Fully responsive, accessible (WCAG AA, keyboard nav, reduced-motion support), fast (good
Lighthouse). No lorem ipsum — every claim is real and ideally backed by live data from the
analytics API.

**Sections (in order):**
1. **Hero** — one-line positioning ("Production-grade voice AI for complex inbound ordering"),
   a sub-line on the Wingstop use case, and a primary CTA: **"Talk to the agent"** that launches the
   existing live voice demo. Secondary CTA: "How it works" / GitHub.
2. **The hard problem** — why complex food ordering (configurable items, split flavors, wet/dry,
   well-done, combos, corrections, mid-order cancels) is a real test of voice AI, vs. trivial
   appointment-booking demos.
3. **Live demo** — embed the actual voice UI (transcript + order summary + confirmation), so a
   visitor can place a real mock order in the browser.
4. **How it works** — the architecture diagram (Section 3), the three voice paths
   (classic / OpenAI realtime / Gemini Live), and the router→state-machine→deterministic-core
   layering. Make the agentic design legible.
5. **Reliability** — the deterministic offline test suite, graceful degradation/fallback,
   confirmation gates, and human escalation. Pull **live numbers** where possible (containment rate,
   completion rate, p95 latency, test count).
6. **Observability / analytics** — show that every call has a transcript, recording, order value,
   and metrics; a small live or screenshot dashboard.
7. **Engineering deep-dive** — concise capability cards: state machine, idempotent order service,
   provider circuit breakers, stateless scaling, load-test results.
8. **Tech stack** — LiveKit, Python, FastAPI, Next.js, Postgres, Deepgram/OpenAI/Cartesia/Gemini.
9. **About** — built by Nithin; links to GitHub/LinkedIn/resume.
10. **Footer** — repo, docs, contact.

**Acceptance:** responsive on mobile/desktop, AA accessible, no placeholder content, the "Talk to
the agent" CTA actually starts a session, and any live stats are wired to the analytics API (with a
sensible static fallback if the API is down).

---

## 11. Phasing / execution order

Run these as discrete PRs (Track A) and one or two PRs for Track B. Each phase ends green.

- **Phase 0 — Audit.** `docs/CURRENT_STATE_AUDIT.md`; confirm the real flow and failures.
- **Phase 1 — Persistence foundation.** Postgres + Alembic + schema + OrderService/CustomerService/
  StoreService (idempotent), menu/store seed, SQLite test wiring.
- **Phase 2 — Conversation core.** Router + top-level FSM; fix GREETING, IDENTIFY, name capture.
- **Phase 3 — Order sub-FSM.** Full configurable-item slot-filling, read-back, confirmation gate,
  persistence, `public_code`.
- **Phase 4 — Tracking / cancel / store-info** nodes against the DB.
- **Phase 5 — Observability.** Transcript persistence, egress recordings, `call_events`, analytics
  read API.
- **Phase 6 — Escalation.** FrustrationMonitor + handoff + tests.
- **Phase 7 — Reliability/scale.** Circuit breakers, fallbacks, expanded reliability suite, load
  test, docs.
- **Phase 8 — Landing page** (can run in parallel from Phase 5 once analytics endpoints exist).

For each phase, deliver: working code, passing + new tests, updated docs, and a short PR summary of
what changed and how it was verified.

---

## 12. Definition of done (program-level)

- [ ] All three voice paths still function via the unchanged `runtime_config` contract.
- [ ] A new caller can place a complex order end-to-end (e.g. *"10 boneless, half lemon pepper half
      hot, dry, well done, combo with fries and a Coke, extra ranch"*), hears an accurate read-back
      and total, confirms, and the order is persisted with a `public_code`.
- [ ] A returning caller is recognized by phone and can **track** that order's status + ETA.
- [ ] Cancellation, store-info, and "talk to a human" all work as distinct routed flows.
- [ ] Frustration/repetition reliably escalates to a manager handoff; calm calls never escalate.
- [ ] Every call has a persisted transcript, a recording (when enabled), an order value, and
      analytics; aggregate metrics are queryable.
- [ ] The deterministic reliability suite is expanded and green, runs offline with no API keys.
- [ ] A load-test script reports throughput/error-rate/p95 for concurrent ordering sessions.
- [ ] The landing page is live, polished, accessible, responsive, and the live demo CTA works.
- [ ] `docs/` reflects the final architecture (`ARCHITECTURE.md`, `RELIABILITY_TESTING.md`,
      `PRODUCTION_READINESS.md`, `ENVIRONMENT_VARIABLES.md`, `MOCK_MENU.md`).

---

## 13. Non-goals / out of scope

- Real Wingstop integration, real POS, or real payment processing (mock only).
- Real PII storage beyond a demo phone + name; document the privacy boundary.
- Replacing or re-architecting the three voice paths' provider SDKs.
- A multi-tenant admin product — this is a single-brand showcase.