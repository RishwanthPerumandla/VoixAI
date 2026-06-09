# VoixAI MVP Implementation Plan

## 1. MVP Goal

Build a small working MVP to understand how LiveKit voice agents work.

The MVP should allow a user to:

1. Open a web page.
2. Click “Start Conversation.”
3. Join a LiveKit room.
4. Speak to a Python LiveKit voice agent.
5. Hear the agent respond with voice.
6. See basic connection/session status.
7. Talk to a simple restaurant order-taking assistant.
8. Correct or change an order during the conversation.
9. Receive a mock order summary.

This MVP is not the full production platform. It is a learning and validation version.

---

## 2. What We Are Building

We are building a browser-based restaurant voice agent demo using:

* LiveKit React starter for the frontend.
* LiveKit Python agent starter for the backend voice agent.
* A tiny FastAPI service for health check and LiveKit token generation.
* A simple in-memory restaurant order state.
* A mock menu and mock order total function.

---

## 3. What We Are Not Building Yet

Do not build these in the MVP:

* Admin dashboard
* Database
* Multi-client configuration
* Prompt registry
* Prompt versioning
* Cost metering
* Analytics dashboard
* Simulation engine
* Production deployment
* Telephony
* Real POS integration
* Authentication
* Billing
* Redis
* Complex state machine
* Complex monitoring

These will come after we understand the basic LiveKit voice-agent workflow.

---

## 4. MVP Architecture

```txt
User Browser
   |
   | WebRTC audio
   v
LiveKit Room
   |
   | Agent joins as participant
   v
Python LiveKit Agent
   |
   +--> STT
   +--> LLM
   +--> TTS
   +--> Simple restaurant order memory
   +--> Mock order tool
```

---

## 5. Repository Structure

```txt
voixai-mvp/
  apps/
    web/
      # Based on livekit-examples/agent-starter-react

    agent-runtime/
      # Based on livekit-examples/agent-starter-python

    api/
      # Minimal FastAPI service

  docs/
    MVP_IMPLEMENTATION_PLAN.md
    LOCAL_SETUP.md
    CODEX_RULES.md
    PHASE_STATUS.md
    ENVIRONMENT_VARIABLES.md

  README.md
```

---

# Phase 0 — MVP Repo Setup

## Goal

Create the basic repo structure and preserve both LiveKit starter projects.

## Scope

* `apps/web`
* `apps/agent-runtime`
* `apps/api`
* `docs`
* root config files

## Tasks

1. Create the monorepo folder structure.
2. Add the LiveKit React starter into `apps/web`.
3. Add the LiveKit Python agent starter into `apps/agent-runtime`.
4. Create `apps/api` with a minimal FastAPI app.
5. Add `/health` endpoint in the API.
6. Add root `README.md`.
7. Add `.gitignore`.
8. Add `.env.example` files for:

   * root
   * `apps/web`
   * `apps/agent-runtime`
   * `apps/api`
9. Add documentation files:

   * `docs/MVP_IMPLEMENTATION_PLAN.md`
   * `docs/LOCAL_SETUP.md`
   * `docs/CODEX_RULES.md`
   * `docs/PHASE_STATUS.md`
   * `docs/ENVIRONMENT_VARIABLES.md`
10. Update `docs/PHASE_STATUS.md` and mark Phase 0 complete.

## Do Not Implement

* LiveKit token generation
* Restaurant logic
* Voice connection changes
* Database
* Analytics
* Admin dashboard

## Acceptance Criteria

* `apps/web` exists and the React starter remains runnable.
* `apps/agent-runtime` exists and the Python starter remains runnable.
* `apps/api` starts successfully.
* `GET /health` returns a healthy response.
* Documentation exists.
* Phase 0 status is documented.

---

# Phase 1 — Basic LiveKit Voice Connection

## Goal

Make the browser user and Python agent join the same LiveKit room and have a basic voice conversation.

## Scope

* `apps/web`
* `apps/agent-runtime`
* `apps/api`

## Tasks

1. Configure LiveKit environment variables:

   * `LIVEKIT_URL`
   * `LIVEKIT_API_KEY`
   * `LIVEKIT_API_SECRET`
2. Add a token generation endpoint in `apps/api`.

Endpoint:

```txt
POST /api/livekit/token
```

Request:

```json
{
  "room_name": "voixai-mvp-demo",
  "participant_name": "web-user"
}
```

Response:

```json
{
  "livekit_url": "wss://...",
  "token": "...",
  "room_name": "voixai-mvp-demo"
}
```

3. Update the React app so the user can:

   * click “Start Conversation”
   * request a token from the API
   * join the LiveKit room
   * leave the room
4. Update the Python agent so it can join the same room.
5. Keep the agent as a simple friendly assistant.
6. Show basic UI states:

   * disconnected
   * connecting
   * connected
   * agent joined
   * error
7. Update `docs/LOCAL_SETUP.md`.
8. Update `docs/PHASE_STATUS.md`.

## Do Not Implement

* Restaurant ordering
* Menu logic
* Order memory
* Mock tools
* Analytics
* Database

## Acceptance Criteria

* User can open the web app.
* User can click “Start Conversation.”
* Browser joins LiveKit room.
* Python agent joins the same room.
* User can speak.
* Agent responds with voice.
* User can end the session.
* Setup instructions are updated.

---

# Phase 2 — Restaurant Agent Personality

## Goal

Turn the generic assistant into a simple restaurant order-taking assistant.

## Scope

* `apps/agent-runtime`
* optionally `apps/web` for text labels

## Tasks

1. Add a restaurant-specific system prompt.
2. The agent should behave like a friendly restaurant order taker.
3. The agent should use short, natural responses.
4. Add a small static menu inside the agent for now.
5. The agent should ask:

   * pickup or delivery
   * what the customer wants
   * flavor
   * drink
   * pickup time
6. Update UI copy from generic assistant to restaurant demo.
7. Update docs.

## Example Behavior

```txt
User: Hi, I want wings.

Agent: Sure — pickup or delivery?

User: Pickup.

Agent: Got it. What would you like?
```

## Do Not Implement

* Order state object
* Tool calls
* Pricing
* Database
* Multi-client config

## Acceptance Criteria

* Agent no longer sounds like a generic chatbot.
* Agent behaves like a restaurant ordering assistant.
* User can have a basic restaurant-style conversation.
* Responses are short and voice-friendly.

---

# Phase 3 — Simple In-Memory Order State

## Goal

Add simple memory so the agent can remember the order during the session.

## Scope

* `apps/agent-runtime`

## Tasks

1. Create a simple `OrderState` model.

Example:

```python
class OrderState:
    pickup_or_delivery: str | None
    items: list[dict]
    drink: str | None
    pickup_time: str | None
    confirmed: bool
```

2. Track basic order details:

   * pickup or delivery
   * item name
   * size or quantity
   * flavor
   * classic or boneless
   * drink
   * pickup time
3. Add simple update logic when the user changes something.
4. The agent should handle corrections.

Example:

```txt
User: I want 10 lemon pepper wings.

Agent: Got it — 10 lemon pepper wings.

User: Actually make that boneless.

Agent: Sure — switching it to boneless.
```

5. Add a debug log of the current order state after each turn.
6. Update docs.

## Do Not Implement

* Complex state machine
* Database persistence
* Tool router
* Admin UI
* Analytics

## Acceptance Criteria

* Agent remembers order details during the session.
* Agent can update the order after corrections.
* Agent can summarize the current order.
* Order state is reset for a new session.

---

# Phase 4 — Mock Menu and Mock Order Total

## Goal

Add simple mock tool-like functions to understand business action flow.

## Scope

* `apps/agent-runtime`

## Tasks

1. Create a mock menu file or Python object.

Example:

```python
MENU = {
    "10_piece_wings": {
        "name": "10 piece wings",
        "price": 11.99
    },
    "fries": {
        "name": "Fries",
        "price": 3.49
    },
    "drink": {
        "name": "Drink",
        "price": 2.49
    }
}
```

2. Add a function:

```python
calculate_order_total(order_state)
```

3. Add a function:

```python
create_mock_order(order_state)
```

4. The agent should not create the mock order until the user confirms.
5. The agent should recap before confirmation.

Example:

```txt
Agent: Your order is 10 boneless lemon pepper wings with a Coke for pickup in 20 minutes. Your demo total is $14.48. Should I place this mock order?
```

6. After confirmation, generate a mock order ID.

Example:

```txt
Agent: Perfect — your mock order is confirmed. Your demo order number is VX-1042.
```

7. Update docs.

## Do Not Implement

* Real POS integration
* Payment
* Database
* Tool router abstraction
* External APIs

## Acceptance Criteria

* Agent can calculate a mock total.
* Agent asks for confirmation before creating mock order.
* Agent creates a mock order ID only after confirmation.
* User can complete a full demo order.

---

# Phase 5 — Basic Interruption and Correction Testing

## Goal

Manually test how LiveKit handles interruptions and corrections.

## Scope

* `apps/agent-runtime`
* `apps/web`
* docs

## Tasks

1. Test user interruption while the agent is speaking.
2. Observe whether the agent stops speaking naturally.
3. Add basic frontend indicator:

   * listening
   * speaking
   * connected
4. Add simple debug logs for:

   * user started speaking
   * agent speaking
   * possible interruption
5. Add correction scenarios to docs.

Manual test:

```txt
Agent: Your order is 10 classic lemon pepper wings with a Coke and—
User: Actually make it boneless.

Expected:
Agent stops or recovers naturally and updates the order.
```

6. Document what works and what needs improvement later.

## Do Not Implement

* Full custom barge-in framework
* Advanced endpointing
* Analytics dashboard
* Production monitoring

## Acceptance Criteria

* We understand current interruption behavior.
* Corrections do not break the session.
* Agent can update the order after interruption.
* Known issues are documented.

---

# Phase 6 — MVP Demo Polish

## Goal

Make the MVP good enough to show internally or to a potential client as a concept demo.

## Scope

* `apps/web`
* `apps/agent-runtime`
* docs

## Tasks

1. Polish the restaurant demo page.
2. Add title: “VoixAI Restaurant Voice Agent Demo.”
3. Add short description.
4. Add Start/End conversation buttons.
5. Add connection status.
6. Add simple transcript panel if available.
7. Add current order summary panel if easy.
8. Add demo instructions.
9. Add fallback text for errors.
10. Add final demo script.

## Demo Script

```txt
User: Hi, I want to order wings.
Agent: Sure — pickup or delivery?

User: Pickup.
Agent: Got it. What would you like?

User: Ten lemon pepper wings.
Agent: Classic or boneless?

User: Classic.
Agent: Got it. Would you like a drink with that?

User: Coke.
Agent: Perfect. What pickup time should I use?

User: Twenty minutes.
Agent: Your order is 10 classic lemon pepper wings with a Coke for pickup in 20 minutes. Your demo total is $14.48. Should I place this mock order?

User: Actually make it boneless.
Agent: Sure — switching that to boneless. Your updated demo total is $14.48. Should I place this mock order?

User: Yes.
Agent: Perfect — your mock order is confirmed. Your demo order number is VX-1042.
```

## Do Not Implement

* Admin dashboard
* Real client onboarding
* Production deployment
* Billing
* Telephony

## Acceptance Criteria

* MVP is demoable.
* Voice conversation works.
* Restaurant ordering flow works.
* Mock order confirmation works.
* Documentation explains how to run and demo it.

---

# MVP Completion Criteria

The MVP is complete when:

```txt
1. Web app starts.
2. Python agent starts.
3. API starts.
4. User joins a LiveKit room from browser.
5. Agent joins the room.
6. User can speak.
7. Agent responds with voice.
8. Agent behaves like a restaurant order assistant.
9. Agent remembers basic order details.
10. User can correct the order.
11. Agent gives a mock total.
12. Agent creates a mock order only after confirmation.
13. Basic interruption behavior is tested.
14. Demo script works end to end.
```

---

# Recommended Build Order

```txt
Day 1:
  Phase 0 — Setup
  Phase 1 — Basic LiveKit voice connection

Day 2:
  Phase 2 — Restaurant personality
  Phase 3 — Simple order memory

Day 3:
  Phase 4 — Mock menu and order total
  Phase 5 — Interruption testing

Day 4:
  Phase 6 — Demo polish
```

---

# Codex Execution Rule

Run only one phase at a time.

After each phase:

1. Start the web app.
2. Start the API.
3. Start the agent runtime.
4. Test manually.
5. Fix errors.
6. Update `docs/PHASE_STATUS.md`.
7. Only then move to the next phase.

Do not ask Codex to build multiple future phases in one prompt.

---

# First Codex Prompt

```txt
We are building VoixAI MVP, a small LiveKit voice agent demo to understand how browser-based voice agents work.

Do not build the full production platform.

Implement only MVP Phase 0.

Goal:
Set up the repo structure using the LiveKit React starter, LiveKit Python agent starter, and a tiny FastAPI service.

Create this structure:

voixai-mvp/
  apps/
    web/
    agent-runtime/
    api/
  docs/
    MVP_IMPLEMENTATION_PLAN.md
    LOCAL_SETUP.md
    CODEX_RULES.md
    PHASE_STATUS.md
    ENVIRONMENT_VARIABLES.md
  README.md

Tasks:
1. Put the LiveKit React starter in apps/web.
2. Put the LiveKit Python agent starter in apps/agent-runtime.
3. Create apps/api with a minimal FastAPI app.
4. Add GET /health endpoint.
5. Add .env.example files for root, web, agent-runtime, and api.
6. Add README.md explaining the MVP.
7. Add docs/MVP_IMPLEMENTATION_PLAN.md.
8. Add docs/LOCAL_SETUP.md.
9. Add docs/CODEX_RULES.md.
10. Add docs/ENVIRONMENT_VARIABLES.md.
11. Add docs/PHASE_STATUS.md and mark Phase 0 complete.

Do not implement:
- LiveKit token generation
- restaurant ordering logic
- database
- analytics
- admin dashboard
- production deployment
- telephony
- real POS integration

Acceptance criteria:
- apps/web remains runnable.
- apps/agent-runtime remains runnable.
- apps/api starts successfully.
- GET /health returns OK.
- Docs are created.
- PHASE_STATUS.md is updated.

After implementation, summarize:
- files changed
- commands to run
- known limitations
- next phase
```

---

# Second Codex Prompt

```txt
Implement only MVP Phase 1: Basic LiveKit Voice Connection.

Goal:
The browser user should be able to join a LiveKit room and speak with the Python LiveKit agent.

Tasks:
1. Add LiveKit environment variables:
   - LIVEKIT_URL
   - LIVEKIT_API_KEY
   - LIVEKIT_API_SECRET
2. Add API endpoint:
   POST /api/livekit/token

Request:
{
  "room_name": "voixai-mvp-demo",
  "participant_name": "web-user"
}

Response:
{
  "livekit_url": "...",
  "token": "...",
  "room_name": "voixai-mvp-demo"
}

3. Update the web app so the user can:
   - click Start Conversation
   - request a token from apps/api
   - join the LiveKit room
   - leave the room
   - see connection status
4. Update the Python agent so it joins the same room.
5. Keep agent behavior as a simple friendly assistant.
6. Update docs/LOCAL_SETUP.md.
7. Update docs/PHASE_STATUS.md.

Do not implement:
- restaurant ordering
- menu
- order state
- mock tools
- database
- analytics

Acceptance criteria:
- Browser joins LiveKit room.
- Python agent joins same room.
- User speaks.
- Agent responds with voice.
- User can end session.
```

---

# Third Codex Prompt

```txt
Implement only MVP Phase 2: Restaurant Agent Personality.

Goal:
Make the voice agent behave like a simple restaurant order-taking assistant.

Tasks:
1. Add a restaurant-specific system prompt.
2. Agent should greet the user like a restaurant employee.
3. Agent should ask whether the order is pickup or delivery.
4. Agent should ask what the user wants to order.
5. Agent should keep responses short and natural.
6. Add a small static menu in the prompt.
7. Update UI title to “VoixAI Restaurant Voice Agent Demo.”
8. Update docs/PHASE_STATUS.md.

Do not implement:
- order state object
- pricing
- mock order creation
- database
- analytics
- admin dashboard

Acceptance criteria:
- Agent sounds like a restaurant order taker.
- User can have a basic voice ordering conversation.
- Responses are concise and voice-friendly.
```

---

# Fourth Codex Prompt

```txt
Implement only MVP Phase 3: Simple In-Memory Order State.

Goal:
The restaurant agent should remember basic order details during the current session.

Tasks:
1. Create an OrderState model in the Python agent runtime.
2. Track:
   - pickup_or_delivery
   - items
   - flavor
   - classic_or_boneless
   - drink
   - pickup_time
   - confirmed
3. Update the agent logic so it can summarize the current order.
4. Handle simple corrections.
5. Add debug logs showing current order state after each update.
6. Update docs/PHASE_STATUS.md.

Do not implement:
- database persistence
- complex state machine
- pricing
- tool router
- admin dashboard

Acceptance criteria:
- Agent remembers order details in one session.
- Agent handles simple corrections.
- Agent can recap the order.
```

---

# Fifth Codex Prompt

```txt
Implement only MVP Phase 4: Mock Menu and Mock Order Total.

Goal:
Add simple mock business logic so the agent can calculate a demo total and create a mock order after confirmation.

Tasks:
1. Add a mock menu.
2. Add calculate_order_total(order_state).
3. Add create_mock_order(order_state).
4. The agent should recap the order before confirmation.
5. The agent should ask the user to confirm.
6. The agent should only create a mock order after the user says yes.
7. Generate a fake order number like VX-1042.
8. Update docs/PHASE_STATUS.md.

Do not implement:
- real POS integration
- payment
- database
- external APIs

Acceptance criteria:
- Agent calculates a mock total.
- Agent asks for confirmation.
- Agent creates mock order only after confirmation.
- Full restaurant order demo works.
```

---

# Sixth Codex Prompt

```txt
Implement only MVP Phase 5: Basic Interruption and Correction Testing.

Goal:
Test and document how interruption/correction behaves in the MVP.

Tasks:
1. Add simple UI indicators:
   - connected
   - listening
   - speaking
2. Add debug logs for:
   - user speech detected
   - agent response started
   - agent response ended
   - correction detected if possible
3. Test correction scenarios:
   - user changes classic to boneless
   - user adds fries after recap
   - user changes drink
4. Document findings in docs/PHASE_STATUS.md.
5. Add docs/INTERRUPTION_TESTING.md.

Do not implement:
- full custom interruption framework
- advanced endpointing
- analytics dashboard
- production monitoring

Acceptance criteria:
- We can manually test interruption/correction.
- Corrections do not break the order state.
- Known limitations are documented.
```

---

# Seventh Codex Prompt

```txt
Implement only MVP Phase 6: Demo Polish.

Goal:
Make the MVP presentable as a small restaurant voice agent demo.

Tasks:
1. Polish the web page.
2. Add title: “VoixAI Restaurant Voice Agent Demo.”
3. Add short demo description.
4. Add Start Conversation and End Conversation buttons.
5. Add connection status.
6. Add transcript panel if available.
7. Add current order summary panel if available.
8. Add final mock order summary after confirmation.
9. Add docs/DEMO_SCRIPT.md.
10. Update docs/LOCAL_SETUP.md.
11. Update docs/PHASE_STATUS.md.

Do not implement:
- production deployment
- admin dashboard
- database
- telephony
- real POS integration

Acceptance criteria:
- MVP is demoable.
- User can complete a restaurant order by voice.
- User can correct the order.
- Agent can create a mock order.
- Demo script works end to end.
```
