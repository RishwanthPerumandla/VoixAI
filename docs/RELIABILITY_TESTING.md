# Reliability Testing

VoixAI ships a deterministic Wingstop reliability suite so we can prove the ordering backend behaves safely across messy customer flows without relying on Gemini Live, LiveKit, rooms, microphones, or API keys.

Phase 2 adds a second deterministic layer for the call-level conversation core:
offline router/FSM tests cover fixed transcripts, the one-clarification reroute
path, startup greeting, identify-by-phone, confirmed name capture, and persisted
node resume. These tests are intentionally separate from the larger order
scenario corpus because they exercise `apps/agent-runtime/src/conversation_core`
and the thin `apps/api` conversation endpoints rather than the order reducer.

## What It Tests

The suite exercises the same shared order domain used by the runtime for:

- menu matching
- reducer/state transitions
- validation
- pricing and repricing
- confirmation-gated placement
- handoff/escalation behavior
- session restart and stale-state protection

Conversation-core focused tests exercise:

- high-signal routing for tracking, cancellation, store info, ordering, modify,
  and human handoff phrases
- low-confidence routing that asks exactly one clarification before rerouting
- startup `GREETING -> IDENTIFY -> ROUTE`
- returning-caller and new-caller identification by phone
- name capture with confirmation, spelling fallback, persistence, and no
  re-asking a filled slot
- simulated reconnect resume from persisted `call_sessions.current_node`

The current deterministic corpus includes `201` scenarios across:

- `happy_paths`: `22`
- `corrections`: `31`
- `cancellations`: `20`
- `invalid_modifiers`: `20`
- `flavor_limits`: `15`
- `unknown_items`: `15`
- `ambiguous_phrasing`: `15`
- `bilingual`: `10`
- `confirmation_gate`: `10`
- `pricing_repricing`: `10`
- `session_lifecycle`: `10`
- `split_flavor`: `3` (Phase 7 — multiple flavors on one wing order)
- `mid_order_correction`: `3` (Phase 7 — corrections during ordering)
- `idempotent_confirm`: `2` (Phase 7 — duplicate place protection)

It also includes transcript-derived regressions in `apps/agent-runtime/tests/reliability/scenarios/transcript_regressions.json`, grouped by:

- `checkout_loops`
- `metadata_recovery`
- `handoff_frustration`
- `item_correction_confusion`

## How It Works

The suite lives under `apps/agent-runtime/tests/reliability`.

Key pieces:

- `apps/agent-runtime/tests/reliability/scenario_runner.py`: deterministic text-turn interpreter and runner
- `apps/agent-runtime/tests/reliability/scenarios/generated_wingstop_reliability.json`: the current seed corpus
- `apps/agent-runtime/tests/reliability/scenarios/transcript_regressions.json`: hand-curated regressions derived from real failed calls
- `apps/agent-runtime/tests/reliability/scenarios/phase7_scenarios.json`: Phase 7 scenario groups (split_flavor, mid_order_correction, idempotent_confirm)
- `apps/agent-runtime/tests/reliability/generate_scenarios.js`: corpus generator
- `apps/agent-runtime/tests/reliability/test_reliability_suite.py`: pytest entrypoint
- `apps/agent-runtime/tests/reliability/reports/reliability_report.json`: latest JSON summary
- `apps/agent-runtime/tests/load_test_concurrent_orders.py`: concurrent ordering load test
- `apps/agent-runtime/tests/test_intent_router.py`: Phase 2 fixed-transcript router tests
- `apps/agent-runtime/tests/test_conversation_state_machine.py`: Phase 2 FSM and name-capture tests
- `apps/api/tests/test_conversation_core.py`: Phase 2 conversation persistence endpoint tests

Each scenario defines:

- metadata: `name`, `description`, `tags`
- `initial_state`
- ordered customer `turns`
- per-turn `expected` assertions
- `final_expected` assertions

## Run It

From the repo root:

```powershell
scripts\run_reliability_tests.ps1
```

Or directly:

```powershell
cd apps/agent-runtime
.venv\Scripts\python.exe -m pytest tests/reliability -q
```

Run the Phase 2 focused tests directly:

```powershell
cd apps/agent-runtime
.venv\Scripts\python.exe -m pytest tests\test_intent_router.py tests\test_conversation_state_machine.py -q

cd ..\api
.venv\Scripts\python.exe -m pytest tests\test_conversation_core.py -q
```

## Load Test

A concurrent ordering load test exercises the deterministic core under
simulated multi-session pressure. It uses the same `ReliabilityScenarioRunner`
as the reliability suite — no LiveKit, audio, or API keys needed.

Run it:

```powershell
cd apps/agent-runtime
.venv\Scripts\python.exe -m tests.load_test_concurrent_orders --concurrency 10 --sessions 50
```

The test simulates N concurrent ordering sessions (configurable `--concurrency`
and `--sessions`), each completing a name→item→price→review→confirm→place flow.
It reports throughput (sessions/s), latency percentiles (P50/P95/P99), and
pass/fail counts.

The backend HTTP endpoint is not required for the load test: the circuit breaker
will open after repeated backend failures, and the fallback to local order
creation keeps every session passing.

## Report Output

The run writes:

- `apps/agent-runtime/tests/reliability/reports/reliability_report.json`

Current example (Phase 7):

```json
{
  "total_scenarios": 201,
  "passed": 201,
  "failed": 0,
  "pass_rate": 100.0
}
```

It also prints a terminal summary like:

```text
VoixAI Wingstop Reliability Suite
Total scenarios: 201
Passed: 201
Failed: 0
Pass rate: 100.0%
```

## Adding Scenarios

1. Update `apps/agent-runtime/tests/reliability/generate_scenarios.js`.
2. Regenerate the corpus:

```powershell
node apps/agent-runtime/tests/reliability/generate_scenarios.js
```

3. Re-run the suite.

Prefer deterministic text turns that represent the customer’s intent, and keep expectations tied to reducer/validation/pricing behavior rather than model wording.

For real calls, prefer adding them to `apps/agent-runtime/tests/reliability/scenarios/transcript_regressions.json` in small grouped batches so the source remains visible and easy to review.

## Why This Is Separate From Live Model Evals

These tests are not trying to prove speech recognition or Gemini interpretation is always perfect. They exist to prove that once a turn is interpreted into menu/order actions, VoixAI behaves predictably and safely.

Use live session failures to feed this suite:

1. capture the transcript or reduced turn sequence
2. convert it into a deterministic scenario
3. add expectations for the reducer/validation/pricing outcome
4. keep it as a regression case
