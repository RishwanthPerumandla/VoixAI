# Phase Status

## Phase 0

Status: Complete

Completed work:

- Added `apps/web` from the official LiveKit React starter.
- Added `apps/agent-runtime` from the official LiveKit Python starter.
- Added `apps/api` with a minimal FastAPI app.
- Added `GET /health`.
- Added root and per-app `.env.example` files.
- Added Phase 0 repository documentation.
- Disabled starter token generation in the web app so Phase 0 did not implement Phase 1 behavior.

## Phase 1

Status: Complete

Completed work:

- Added `POST /api/livekit/token` in `apps/api`.
- Added LiveKit token generation with room dispatch for the Python agent.
- Updated `apps/web` to request tokens from `apps/api`.
- Updated `apps/web` to join the fixed MVP room and show basic connection and agent status.
- Updated `apps/agent-runtime` to use the shared agent name from env.
- Updated Phase 1 setup and environment documentation.

Validation notes:

- API health checks still pass locally.
- Token generation can be tested locally once LiveKit credentials are available to `apps/api`.
- Full browser-to-agent voice verification requires the API, web app, and agent runtime to be running together with valid LiveKit credentials.

## Phase 2

Status: Complete

Completed work:

- Updated the Python agent prompt to a restaurant order-taking persona.
- Added a small static menu directly in the Phase 2 prompt.
- Instructed the agent to greet the user, ask pickup or delivery, and then ask what they want to order.
- Updated the web app title and welcome copy to the restaurant demo.

Validation notes:

- The LiveKit connection flow from Phase 1 remains unchanged.
- Restaurant behavior is prompt-driven only in this phase.
- No order state, pricing, or mock order creation was added.

## Phase 3

Status: Complete

Completed work:

- Added a session-scoped in-memory `OrderState` model in the Python agent runtime.
- Tracked pickup or delivery, items, flavor, classic or boneless style, drink, pickup time, and confirmation state.
- Added tool-backed order updates so the agent can remember details and apply simple corrections during one session.
- Added order recap behavior so the agent can summarize the current order when asked.
- Added debug logging after each order-state update.

Validation notes:

- Order memory is in-process only and resets when the agent session ends or the worker restarts.
- Corrections are intentionally simple in this phase and rely on the model using the order tools appropriately.
- No pricing, database persistence, or downstream order submission was added.

## Phase 4

Status: Complete

Completed work:

- Added a mock menu with simple demo pricing in the Python agent runtime.
- Added `calculate_order_total(order_state)` for demo totals.
- Added mock order review and mock order creation tools for the current session.
- Updated the agent instructions so it recaps the order, asks for confirmation, and only creates a mock order after the user says yes.
- Added fake order number generation in the `VX-####` format.

Validation notes:

- Totals are mock values for the MVP and are based only on the small in-memory menu.
- Mock order creation is session-scoped and does not persist after the worker or session ends.
- No payment, database, POS integration, or external API calls were added.

## Phase 5

Status: Complete

Completed work:

- Added simple `Connected`, `Listening`, and `Speaking` indicators to the web session UI.
- Added debug logs in the Python agent runtime for user speech detection, agent response start, agent response end, and detected order corrections.
- Prepared and documented manual correction scenarios for classic-to-boneless, adding fries after recap, and changing the drink.
- Added interruption and correction testing documentation in `docs/INTERRUPTION_TESTING.md`.

Validation notes:

- The UI now exposes enough state to manually observe connection and speaking/listening behavior during a live session.
- Correction logging is based on changes to the in-memory order state and helps verify that updates do not wipe the existing order.
- Full interruption quality still needs live manual testing with the browser, agent runtime, and LiveKit running together.

Known limitations:

- No custom interruption framework or advanced endpointing was added in this phase.
- Interruption handling still depends on the underlying LiveKit and model behavior.
- Manual live-room testing is still required to measure how cleanly barge-in works end to end.

## Phase 6

Status: Complete

Completed work:

- Polished the web demo landing view with a clearer title, description, demo flow, and start call CTA.
- Kept explicit `Start Conversation` and `End Conversation` controls in the demo flow.
- Preserved visible connection and session status in the web UI.
- Added a desktop-friendly demo layer with recent transcript, current order summary, and final mock order panels.
- Improved the mock order confirmation phrasing so the final order number and demo total are easier to surface in the UI.
- Added `docs/DEMO_SCRIPT.md`.
- Updated `docs/LOCAL_SETUP.md` with demo-specific run and usage tips.

Validation notes:

- The current order summary panel depends on the conversation containing a recap with the structured `Current order:` phrasing.
- The final mock order panel depends on the confirmation response including the `VX-####` order number.
- The transcript panel is driven from real session messages and is available in the demo layout.

Known limitations:

- The order and final summary panels are transcript-driven UI helpers, not a direct real-time sync of the Python `OrderState`.
- Full end-to-end demo validation still requires running the API, web app, and agent runtime together with valid LiveKit credentials.
- The mock order remains session-only and is not stored anywhere after the demo ends.
