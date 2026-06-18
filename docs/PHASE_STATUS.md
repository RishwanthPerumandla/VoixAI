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

## Phase 7

Status: Complete

Completed work:

- Added a `VOICE_PROVIDER` switch in `apps/agent-runtime` with `classic` as the default and `openai_realtime` as the optional low-latency mode.
- Kept the existing Deepgram STT, OpenAI text LLM, and Cartesia TTS pipeline intact for classic mode.
- Wired the optional OpenAI Realtime path through the LiveKit OpenAI plugin inside the Python worker, without changing the browser or API token architecture.
- Added startup validation so classic mode requires the LiveKit env values and realtime mode additionally requires `OPENAI_API_KEY`.
- Added startup logs that clearly show which provider is active and explain that classic per-stage latency metrics are not emitted in realtime mode.
- Updated env examples and setup docs for the new worker-side provider switch.

Validation notes:

- `apps/agent-runtime/.venv` installs `livekit-agents` with the OpenAI plugin support needed for both the classic OpenAI usage and the OpenAI Realtime path.
- Unit coverage was refreshed around provider normalization and provider-to-engine mapping in `apps/agent-runtime/tests/test_order_state.py`.
- Full live-room verification still requires valid LiveKit and OpenAI credentials plus the API, web app, and worker running together.

Known limitations:

- The browser still connects only through LiveKit in this phase; no browser-direct OpenAI WebRTC path or ephemeral OpenAI session endpoint was added.
- Classic latency logs remain the source of truth for STT, LLM, and TTS stage timings. Realtime mode currently logs the active provider but not equivalent per-stage metrics.
- The in-session order tools remain available in both modes, but realtime behavior still depends on tool-calling quality during live conversation.

## Phase 8

Status: Complete

Completed work:

- Replaced the old string-based Wingstop order memory with a structured order state and structured line items.
- Added a realistic `Voix Wings Demo` wing-restaurant menu with combos, classic wings, boneless wings, tenders, sandwiches, group packs, fries, sides, dips, drinks, desserts, flavors, and modifier groups.
- Added stronger menu validation for invalid items, flavor limits, combo requirements, and classic-only piece preferences like `All Flats`.
- Added a priced quote layer with subtotal, tax, total, line-item breakdowns, and ETA.
- Added a stricter bilingual restaurant instruction layer for English and Spanish ordering.
- Added a confirmation gate so mock order creation only succeeds when the order has valid items, required selections, a shown total, a readback recap, an order type, and explicit user confirmation.
- Added assistant-turn guardrail auditing for price mismatches and order-placement hallucination checks.
- Refreshed focused runtime tests around menu validation, pricing, structured snapshots, guardrail auditing, and provider behavior.

Validation notes:

- Focused runtime coverage passes in `apps/agent-runtime/tests/test_order_state.py`.
- Structured order snapshots now include line items, quote details, and guardrail violations.
- The web UI continues to consume telemetry while showing quote totals before final mock order creation.

Known limitations:

- The current menu and pricing are still demo data, not an official Wingstop or POS-backed source of truth.
- Assistant response auditing runs immediately after assistant generation and telemetry publication; it is not yet a full pre-speech rewrite or hard-block layer inside LiveKit.
- Order state is still session-scoped and in memory only.

## Phase 9

Status: Complete

Completed work:

- Moved Wingstop menu resolution, order validation, and pricing behind backend-backed API endpoints instead of relying only on prompt-embedded menu data.
- Updated the agent runtime tools to call the backend menu endpoints for item resolution, validation, and pricing.
- Added more voice-friendly combo aliases and explicit missing-requirement feedback so incomplete combos immediately surface missing drink or side selections.
- Added auto-return behavior in the confirmation UI after a completed mock order.
- Pinned the LiveKit Google realtime plugin to the `charan632-dev/agents` fork for the current Gemini Live fix path.
- Added a Gemini 3.1-specific fallback so the runtime attaches TTS for forced startup speech and avoids unsupported `generate_reply(...)` calls on the initial greeting and idle away prompt.

Validation notes:

- Focused runtime coverage passes in `apps/agent-runtime/tests/test_order_state.py`, including Gemini 3.1 greeting-path coverage and backend-backed order-state behavior.
- The API-side menu resolve and pricing behavior was exercised directly in the API environment for combo requirement and total checks.
- The agent runtime editable install was refreshed so the local worker venv now pulls the forked Google plugin from GitHub.

Known limitations:

- Wingstop menu and pricing are still demo data even though they now flow through backend endpoints.
- Full end-to-end live-room verification for Gemini 3.1 still depends on restarting the worker and testing a fresh room/session with valid LiveKit and Google credentials.
- Order submission remains mock order creation, not a real POS order placement flow.
