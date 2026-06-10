# Interruption Testing

## Goal

Manually observe how the VoixAI MVP behaves when the user interrupts or corrects the restaurant agent during a live conversation.

## What Changed For Phase 5

- The web session view now shows simple live indicators for `Connected`, `Listening`, and `Speaking`.
- The Python agent now emits debug logs for:
  - user speech detected
  - agent response started
  - agent response ended
  - correction detected when stored order fields change

## Manual Test Setup

Run these services together:

1. `cd apps/api`
2. `python main.py`
3. `cd apps/agent-runtime`
4. `.venv\Scripts\python.exe src\agent.py dev`
5. `cd apps/web`
6. `corepack pnpm dev`

Then open the web app, click `Start Conversation`, and watch:

- the status chips in the UI
- the terminal logs from `apps/agent-runtime`

## Correction Scenarios

### Scenario 1: Change classic to boneless

Suggested flow:

1. User orders wings.
2. User specifies classic.
3. Agent recaps or continues.
4. User says: `Actually, make that boneless.`

What to watch for:

- The agent should stop or recover naturally if speaking.
- A correction log should appear for `classic_or_boneless`.
- The later order recap should use `boneless`, not `classic`.

### Scenario 2: Add fries after recap

Suggested flow:

1. User completes a simple wings order.
2. Agent gives a recap.
3. User says: `Add fries too.`

What to watch for:

- The order state should keep the existing order details.
- A correction log should appear for `items`.
- The next recap should include `fries`.

### Scenario 3: Change drink

Suggested flow:

1. User adds a drink such as soda.
2. Agent continues or recaps.
3. User says: `Actually, change the drink to lemonade.`

What to watch for:

- A correction log should appear for `drink`.
- The next recap should use `lemonade`.
- The mock total should update if the drink price changes.

## Expected Runtime Logs

Common log messages during these tests:

- `User speech detected`
- `User speech ended`
- `Agent response started`
- `Agent response ended`
- `Correction detected in fields: ...`
- `Order state updated (...)`

## Findings For This Phase

- The MVP now has enough UI and logging to support manual interruption and correction testing without adding a custom barge-in framework.
- Order corrections are state-based, so changing wing style, adding fries, or changing the drink should update the stored in-memory order instead of resetting it.
- Live interruption quality still depends on LiveKit turn detection, STT timing, and model behavior.

## Known Limitations

- This phase does not add custom interruption recovery logic beyond what LiveKit already provides.
- Correction detection is based on order-state changes, not deeper natural-language intent classification.
- Manual live-room verification is still required to measure how gracefully the agent stops mid-response in real speech conditions.
- Order state is session-only and resets when the session or worker restarts.
