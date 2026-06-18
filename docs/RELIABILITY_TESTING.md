# Reliability Testing

VoixAI ships a deterministic Wingstop reliability suite so we can prove the ordering backend behaves safely across messy customer flows without relying on Gemini Live, LiveKit, rooms, microphones, or API keys.

## What It Tests

The suite exercises the same shared order domain used by the runtime for:

- menu matching
- reducer/state transitions
- validation
- pricing and repricing
- confirmation-gated placement
- handoff/escalation behavior
- session restart and stale-state protection

The current deterministic corpus includes `191` scenarios across:

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
- `apps/agent-runtime/tests/reliability/generate_scenarios.js`: corpus generator
- `apps/agent-runtime/tests/reliability/test_reliability_suite.py`: pytest entrypoint
- `apps/agent-runtime/tests/reliability/reports/reliability_report.json`: latest JSON summary

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

## Report Output

The run writes:

- `apps/agent-runtime/tests/reliability/reports/reliability_report.json`

Current example:

```json
{
  "total_scenarios": 191,
  "passed": 191,
  "failed": 0,
  "pass_rate": 100.0
}
```

It also prints a terminal summary like:

```text
VoixAI Wingstop Reliability Suite
Total scenarios: 191
Passed: 191
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
