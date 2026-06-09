# VoixAI Production Voice Agent Platform Plan

## 1. Product Vision

We are not building one Wingstop demo anymore. We are building a **core voice agent operating system** that can power many client-specific agents.

Example clients:

* Restaurants
* Clinics
* Real estate offices
* Pharmacies
* BPO/contact centers
* Local service businesses
* Internal enterprise assistants
* Receptionist agents
* Lead qualification agents
* Appointment booking agents
* Order-taking agents

The product should have:

1. **Core voice runtime**
2. **Client configuration layer**
3. **Agent behavior/prompt management**
4. **Tool execution framework**
5. **Conversation memory/state**
6. **Testing and simulation**
7. **Analytics and cost metering**
8. **Deployment and monitoring**
9. **Frontend voice UI**
10. **Future telephony support**

We will use:

* `livekit-examples/agent-starter-python` for the backend voice agent runtime. It is the official Python starter for building LiveKit Agents voice AI apps. ([GitHub][2])
* `livekit-examples/agent-starter-react` for the web-based voice UI. It is a Next.js/React starter built with LiveKit Agents UI and LiveKit JavaScript SDK, supporting voice, transcriptions, and avatars. ([GitHub][3])

---

# 2. Core Architecture

## High-Level System

```txt
User Browser / Client App
        |
        | WebRTC audio, transcription UI, controls
        v
LiveKit Room
        |
        | Agent joins as realtime participant
        v
Python LiveKit Agent Runtime
        |
        +--> Turn Detection / VAD / Endpointing
        +--> STT
        +--> Conversation Orchestrator
        +--> LLM / Realtime Model
        +--> Tool Router
        +--> TTS
        +--> Interrupt / Barge-in Handler
        +--> State Manager
        +--> Analytics Emitter
        |
        v
Client Business Systems
        |
        +--> POS / CRM / Booking / Database / APIs
        +--> Knowledge Base / Menu / FAQ / Policies
        +--> Human Handoff / Notifications
```

LiveKit handles real-time audio/video/data transport through WebRTC, and the Agents framework allows the backend agent to participate directly in the room. LiveKit also provides production observability features such as transcripts, traces, logs, audio recordings, and quality metrics in LiveKit Cloud. ([GitHub][4])

---

# 3. Recommended Repository Structure

Use a monorepo:

```txt
voixai-platform/
  apps/
    web/
      # Based on livekit-examples/agent-starter-react
      # Client-facing voice UI, admin UI, demo UI

    agent-runtime/
      # Based on livekit-examples/agent-starter-python
      # LiveKit agent workers, STT/LLM/TTS orchestration

    api/
      # FastAPI backend for clients, configs, analytics, sessions, billing

  packages/
    shared-types/
      # Shared schemas: client config, agent config, tools, analytics events

    prompt-registry/
      # Prompt templates, versioning, client overrides

    evals/
      # Simulation scripts, golden conversations, regression tests

  infra/
    docker/
    terraform/
    helm/
    github-actions/
    monitoring/

  docs/
    architecture.md
    product-plan.md
    client-onboarding.md
    agent-runtime.md
    prompt-management.md
    testing-simulation.md
    analytics-cost-metering.md
    deployment.md
```

---

# 4. Backend Runtime: LiveKit Agent Service

The `apps/agent-runtime` service is the heart of the system.

It should be responsible for:

* Joining LiveKit rooms
* Listening to user audio
* Running STT
* Managing turn detection
* Calling LLM or realtime model
* Executing tools
* Streaming TTS back
* Handling interruptions
* Maintaining session state
* Sending analytics events
* Applying client-specific configuration

## Main runtime modules

```txt
agent-runtime/
  src/
    main.py
    config/
      settings.py
      provider_config.py

    agents/
      base_agent.py
      restaurant_agent.py
      receptionist_agent.py
      appointment_agent.py
      support_agent.py

    pipeline/
      audio_input.py
      stt.py
      turn_detection.py
      llm.py
      tts.py
      interruption.py
      latency_tracker.py

    orchestration/
      conversation_manager.py
      state_machine.py
      policy_engine.py
      tool_router.py
      fallback_manager.py

    tools/
      base_tool.py
      restaurant_menu_tool.py
      order_tool.py
      appointment_tool.py
      crm_tool.py
      human_handoff_tool.py

    prompts/
      prompt_loader.py
      prompt_renderer.py
      prompt_version_client.py

    analytics/
      event_emitter.py
      cost_meter.py
      call_metrics.py

    memory/
      session_memory.py
      client_memory.py
      user_profile_memory.py

    tests/
      unit/
      integration/
      simulations/
```

---

# 5. Real-Time Audio Transport

## Use LiveKit as the audio transport layer

LiveKit gives us:

* Browser-based real-time audio
* WebRTC streaming
* Rooms and participants
* Agent participant joining
* Future telephony path
* Frontend SDKs
* Cloud or self-hosted deployment options

The user enters a room from the React app. The Python agent joins the same room as a participant. Audio flows in real time between the user and agent.

## Room strategy

Each conversation should create one LiveKit room:

```txt
room_name = client_id + session_id
```

Example:

```txt
wingstop_demo_sess_01HF3
ascent_reception_sess_02GK8
```

Room metadata:

```json
{
  "client_id": "wingstop-demo",
  "agent_id": "restaurant-order-agent",
  "environment": "staging",
  "session_id": "sess_abc123",
  "channel": "web",
  "language": "en-US"
}
```

---

# 6. Duplex Model Strategy

We should support two runtime modes.

## Mode A: Cascaded STT → LLM → TTS pipeline

This should be the default production path.

```txt
User speech
  -> STT streaming transcript
  -> turn detection
  -> LLM response stream
  -> TTS stream
  -> LiveKit audio output
```

Recent research and production practice still commonly favor cascaded streaming pipelines for complex voice agents, where STT, LLM, and TTS stream outputs to each other instead of waiting for full completion. A 2026 enterprise voice-agent tutorial found that the “realtime” behavior comes from streaming and pipelining across components, not from any single model. ([arXiv][5])

Recommended providers:

```txt
STT:
  - Deepgram
  - AssemblyAI
  - OpenAI
  - Google STT
  - Whisper self-hosted for lower-cost async/non-critical use

LLM:
  - OpenAI GPT-4.1 / GPT-4o / Realtime variants
  - Anthropic Claude
  - Gemini
  - Groq / Cerebras for low latency
  - OpenRouter for provider switching
  - Self-hosted vLLM later for cost control

TTS:
  - ElevenLabs
  - Cartesia
  - Rime
  - PlayHT
  - OpenAI TTS
  - Azure Neural Voice
```

## Mode B: Native realtime speech model

Use this for experiments or premium accounts where model capability is strong enough.

```txt
User speech
  -> realtime speech-to-speech model
  -> audio response
```

This can reduce architectural complexity, but tool reliability, observability, and business logic control may be harder than cascaded pipelines. LiveKit itself discusses pipeline versus realtime approaches as an architectural decision for voice agents. ([LiveKit][6])

## Recommendation

Start with **cascaded pipeline** for production because it gives us better control over:

* Tool calls
* Business validation
* Cost metering
* Fallbacks
* Prompt versioning
* Multi-client customization
* Logging
* Simulation testing

Then add realtime model mode later.

---

# 7. Turn Detection

Turn detection decides when the user has finished speaking and when the agent should respond.

LiveKit’s turns documentation specifically covers user-side detection and interruption handling, and LiveKit emphasizes that turn detection and interruption management are essential to strong voice AI experiences. ([LiveKit Docs][7])

## Turn detection layers

Use a layered approach:

```txt
1. Audio-level VAD
2. Speech endpointing
3. Semantic endpointing
4. Conversation context rules
5. Tool-state-aware turn logic
```

## Example logic

The agent should not respond immediately after every pause.

Bad:

```txt
User: I want a large...
Agent: Sure, a large what?
```

Better:

```txt
User: I want a large...
short pause
User: ...lemon pepper wings.
Agent: Got it — large lemon pepper wings.
```

## Production turn detection policy

```json
{
  "min_user_speech_ms": 300,
  "soft_pause_ms": 450,
  "hard_pause_ms": 1200,
  "allow_semantic_endpointing": true,
  "detect_filler_words": true,
  "wait_on_incomplete_entities": true,
  "barge_in_enabled": true
}
```

## Semantic endpoint examples

Do not respond yet:

```txt
"I want to order..."
"Can you check if..."
"My phone number is..."
"The address is..."
```

Safe to respond:

```txt
"That’s all."
"Yes, that works."
"No, make it mild."
"I want a 10-piece combo with fries and a Coke."
```

---

# 8. Interruption Handling / Barge-In

This is one of the biggest factors that makes the agent feel human.

LiveKit notes that barge-in detection is part of the real-time audio pipeline and works with client-side echo cancellation; devices without good echo cancellation may need fallbacks like push-to-talk. ([LiveKit][8])

## Required behavior

When the user interrupts:

1. Stop current TTS audio immediately
2. Mark the assistant’s previous response as interrupted
3. Listen to the user
4. Update state
5. Continue naturally without repeating everything

Example:

```txt
Agent: Your total is twenty-three dollars and—
User: Actually make that boneless.
Agent: Sure — switching that to boneless. Your updated total is...
```

## Interruption states

```txt
SPEAKING
USER_INTERRUPTED
TTS_CANCELLED
LISTENING
STATE_REPAIRING
RESPONDING
```

## Implementation requirements

The TTS stream should be cancellable.

The LLM stream should be cancellable.

The conversation manager should store:

```json
{
  "assistant_message_id": "msg_123",
  "status": "interrupted",
  "spoken_text_partial": "Your total is twenty-three dollars and",
  "final_text_not_spoken": "..."
}
```

This prevents the agent from assuming the user heard content that was never spoken.

---

# 9. Conversation State

For business agents, a normal chat history is not enough. We need explicit state.

## State categories

```txt
Session state:
  - call/session ID
  - current room
  - current user
  - timestamps
  - active client
  - active agent

Conversation state:
  - current intent
  - previous turns
  - unresolved questions
  - last confirmed fact
  - pending tool call
  - interruption state

Business state:
  - cart/order
  - appointment details
  - customer profile
  - eligibility
  - payment status
  - handoff status

Safety/compliance state:
  - restricted topics
  - consent
  - escalation triggers
  - disallowed claims

Analytics state:
  - latency
  - cost
  - token usage
  - STT seconds
  - TTS characters
  - tool calls
```

## Example restaurant order state

```json
{
  "intent": "place_order",
  "customer": {
    "name": null,
    "phone": "2145550199"
  },
  "order": {
    "items": [
      {
        "name": "10 piece wings",
        "flavor": "lemon pepper",
        "style": "classic",
        "quantity": 1,
        "size": "10-piece"
      }
    ],
    "missing_fields": ["pickup_time", "drink"]
  },
  "confirmation": {
    "items_confirmed": false,
    "price_confirmed": false,
    "final_confirmed": false
  }
}
```

## State machine

Every production client agent should have a state machine.

Example restaurant order flow:

```txt
GREETING
  -> INTENT_DETECTION
  -> MENU_DISCOVERY
  -> ORDER_BUILDING
  -> MODIFIER_COLLECTION
  -> PRICE_CALCULATION
  -> ORDER_RECAP
  -> FINAL_CONFIRMATION
  -> ORDER_SUBMISSION
  -> CLOSING
```

Fallback:

```txt
ANY_STATE
  -> CLARIFICATION
  -> HUMAN_HANDOFF
  -> SAFE_EXIT
```

---

# 10. Tool Execution

Tools are how the agent performs real business actions.

## Tool categories

```txt
Read tools:
  - get_menu
  - check_business_hours
  - check_availability
  - lookup_customer
  - get_order_status
  - search_knowledge_base

Write tools:
  - create_order
  - update_order
  - book_appointment
  - create_lead
  - send_sms
  - create_ticket

Escalation tools:
  - transfer_to_human
  - notify_manager
  - create_callback_request
```

## Tool execution rules

The agent should never call business-changing tools without confirmation.

Example:

```txt
Allowed without confirmation:
  - search menu
  - check hours
  - calculate price
  - check appointment slots

Needs confirmation:
  - place order
  - cancel order
  - book appointment
  - update customer record
  - send payment link
```

## Tool schema example

```json
{
  "name": "create_order",
  "description": "Create a pickup order for the client restaurant.",
  "requires_confirmation": true,
  "input_schema": {
    "customer_phone": "string",
    "items": "array",
    "pickup_time": "string",
    "store_id": "string"
  },
  "success_state": "ORDER_SUBMITTED",
  "failure_state": "ORDER_SUBMISSION_FAILED"
}
```

## Tool router

The tool router should enforce:

* Client permissions
* Required fields
* Confirmation rules
* Retry policy
* Timeout policy
* Audit logs
* Idempotency keys

```txt
LLM suggests tool call
  -> Tool Router validates
  -> Policy Engine approves/blocks
  -> Tool executes
  -> Result normalized
  -> Conversation state updated
  -> Agent explains next step
```

---

# 11. Prompt and Version Management

This is critical for multi-client production.

Do not hardcode prompts inside agent files.

## Prompt registry

```txt
prompt-registry/
  global/
    base_voice_agent.md
    safety.md
    interruption_behavior.md
    tool_calling.md

  verticals/
    restaurant/
      order_agent.md
      menu_explainer.md
      upsell_policy.md

    clinic/
      appointment_agent.md
      compliance_policy.md

  clients/
    wingstop-demo/
      brand_voice.md
      menu_policy.md
      escalation_rules.md
```

## Prompt composition

Final system prompt should be generated dynamically:

```txt
Global voice behavior
+ Vertical-specific behavior
+ Client-specific behavior
+ Active tools
+ Session context
+ Current state
+ Safety rules
```

## Prompt versioning

Each session must store:

```json
{
  "prompt_version": "restaurant-order-agent@v1.4.2",
  "base_prompt_hash": "abc123",
  "client_prompt_hash": "def456",
  "model": "gpt-4.1-mini",
  "tts_voice": "elevenlabs_voice_01"
}
```

This is necessary for debugging. If the agent fails, we must know exactly what prompt and model produced the behavior.

---

# 12. Client Configuration Layer

This is what makes the platform reusable.

## Client config example

```json
{
  "client_id": "wingstop-demo",
  "display_name": "Wingstop Demo Store",
  "vertical": "restaurant",
  "timezone": "America/Chicago",
  "language": "en-US",
  "agent": {
    "type": "restaurant_order_agent",
    "voice": {
      "provider": "elevenlabs",
      "voice_id": "friendly_cashier_v1",
      "speed": 1.02,
      "stability": 0.65
    },
    "llm": {
      "provider": "openai",
      "model": "gpt-4.1-mini",
      "temperature": 0.4
    },
    "stt": {
      "provider": "deepgram",
      "model": "nova-3"
    }
  },
  "business_rules": {
    "allow_order_submission": false,
    "require_final_confirmation": true,
    "max_clarification_attempts": 2,
    "handoff_on_payment_questions": true
  },
  "integrations": {
    "pos": {
      "enabled": false,
      "provider": "mock"
    },
    "crm": {
      "enabled": false
    }
  }
}
```

## Admin UI should allow

* Create client
* Select vertical
* Configure voice
* Configure model
* Upload knowledge base/menu
* Add tools/integrations
* Set fallback behavior
* View sessions
* View costs
* View analytics
* Run simulations
* Compare prompt versions

---

# 13. Human-Like Conversation Design

This is not only a technical problem. It is a behavioral design problem.

## Human-like behaviors

The agent should:

* Acknowledge naturally
* Avoid long robotic explanations
* Use short confirmations
* Pause before complex answers
* Handle corrections gracefully
* Avoid repeating the same phrase
* Use context from previous turns
* Confirm only when necessary
* Sound calm under uncertainty
* Admit when it needs to check something
* Never hallucinate business facts

## Example behavior rules

Bad:

```txt
Thank you for providing that information. I will now process your request.
```

Good:

```txt
Got it — let me check that.
```

Bad:

```txt
I apologize for the confusion.
```

Good:

```txt
You’re right — I’ll fix that.
```

Bad:

```txt
Can you please repeat that?
```

Good:

```txt
I caught the first part, but not the flavor. Was that lemon pepper?
```

---

# 14. Fallback Handling

Fallbacks decide whether the agent feels reliable or broken.

## Fallback types

```txt
Audio fallback:
  - poor microphone
  - background noise
  - echo
  - packet loss

STT fallback:
  - low confidence transcript
  - unknown word
  - repeated misrecognition

LLM fallback:
  - slow response
  - invalid tool call
  - unsafe output
  - hallucinated item

TTS fallback:
  - provider timeout
  - voice generation error

Tool fallback:
  - POS down
  - CRM timeout
  - invalid API response

Conversation fallback:
  - user angry
  - repeated confusion
  - out-of-scope request
```

## Fallback matrix

```txt
Problem: STT confidence low
Action:
  - Ask targeted clarification
  - Do not guess business-critical data

Problem: TTS provider fails
Action:
  - Switch to backup TTS
  - Continue session

Problem: LLM response timeout
Action:
  - Play filler phrase: "One moment, I’m checking that."
  - Retry with backup model

Problem: Tool fails
Action:
  - Explain simply
  - Offer human handoff or callback

Problem: User interrupts repeatedly
Action:
  - Stop speaking faster
  - Use shorter responses
```

---

# 15. Latency Targets

Human-likeness depends heavily on latency.

## Target metrics

```txt
User speech to partial transcript: < 300ms
End of user turn to first assistant audio: < 900ms ideal
End of user turn to first assistant audio: < 1.5s acceptable
Tool-free answer completion: < 2.5s
Tool-based answer first acknowledgement: < 800ms
Barge-in stop time: < 250ms
```

LiveKit’s own material emphasizes real-time voice UX, automatic turn detection, and interruption handling as core capabilities for production voice agents. ([LiveKit][9])

## Techniques

* Stream STT partials
* Start LLM reasoning before final transcript when safe
* Stream LLM tokens into TTS
* Use short first response chunks
* Cache common responses
* Use local filler audio
* Preload TTS voice sessions
* Use smaller/faster LLM for simple turns
* Use larger LLM only for complex reasoning
* Keep tools fast and idempotent

---

# 16. Call Analytics

Every session should be analyzed.

LiveKit Cloud observability supports transcripts, traces, logs, audio recordings, and unified timelines for agent sessions, and logs can be forwarded to services such as Datadog, CloudWatch, Sentry, and New Relic. ([LiveKit Docs][10])

## Analytics events

```json
{
  "event_type": "turn_completed",
  "session_id": "sess_123",
  "client_id": "wingstop-demo",
  "turn_index": 6,
  "user_transcript": "make that boneless",
  "assistant_text": "Sure — switching that to boneless.",
  "latency_ms": {
    "stt": 180,
    "llm_first_token": 420,
    "tts_first_audio": 260,
    "total_time_to_first_audio": 860
  },
  "cost": {
    "stt_usd": 0.002,
    "llm_usd": 0.004,
    "tts_usd": 0.006,
    "total_usd": 0.012
  }
}
```

## Dashboard metrics

For each client:

```txt
Total calls
Average call duration
Containment rate
Human handoff rate
Successful task completion rate
Order/booking/lead conversion
Average latency
Interruption count
Clarification count
Fallback count
Cost per call
Cost per completed task
Revenue impact
Top failure reasons
Top user intents
Sentiment trend
```

## Quality scoring

Each call should get an automated quality score:

```txt
Task completion: 0–5
Naturalness: 0–5
Latency: 0–5
Tool correctness: 0–5
Policy compliance: 0–5
Escalation quality: 0–5
```

---

# 17. Cost Metering

Cost metering is essential because this becomes a service business.

## Track

```txt
LiveKit usage:
  - room duration
  - participant minutes
  - bandwidth

STT:
  - audio seconds
  - provider cost

LLM:
  - input tokens
  - output tokens
  - cached tokens
  - model used

TTS:
  - characters
  - generated audio seconds
  - voice provider

Tools:
  - API calls
  - paid external services

Infrastructure:
  - worker CPU/RAM
  - GPU usage if self-hosted
  - database usage
```

## Cost report

```json
{
  "client_id": "wingstop-demo",
  "period": "2026-06",
  "sessions": 1200,
  "total_minutes": 5400,
  "avg_cost_per_call": 0.087,
  "avg_cost_per_minute": 0.019,
  "total_ai_cost": 104.40,
  "platform_margin": 0.72
}
```

## Pricing strategy

Offer clients:

```txt
Starter:
  - web voice agent
  - limited monthly minutes
  - basic analytics

Professional:
  - custom prompt
  - knowledge base
  - tools/integrations
  - advanced analytics

Enterprise:
  - custom deployment
  - multi-location
  - SLA
  - human handoff
  - private model/provider options
```

---

# 18. Testing and Simulation

This is where we can become better than simple demos.

## Test types

```txt
Unit tests:
  - state transitions
  - tool validation
  - prompt rendering
  - cost calculation

Integration tests:
  - LiveKit room creation
  - STT provider
  - TTS provider
  - LLM provider
  - tool execution

Conversation simulations:
  - happy path
  - confused user
  - angry user
  - noisy transcript
  - interruptions
  - corrections
  - tool failures

Load tests:
  - 10 concurrent sessions
  - 100 concurrent sessions
  - 1000 concurrent sessions later
```

## Golden conversation tests

Example:

```yaml
name: restaurant_order_happy_path
client_id: wingstop-demo
input_turns:
  - "Hi, I want to order wings."
  - "Ten piece lemon pepper."
  - "Make it a combo with Coke."
  - "Pickup in twenty minutes."
expected_outcomes:
  - intent: place_order
  - item_count: 1
  - final_confirmation_requested: true
  - no_hallucinated_menu_items: true
  - tool_create_order_called: false
```

## Simulation engine

Build a simulator that can run:

```txt
100 synthetic customer conversations
against agent version v1.2
compare with agent version v1.3
show regression report
```

Output:

```txt
Prompt v1.3 improved:
  - task completion +8%
  - clarification count -12%
  - latency unchanged

Prompt v1.3 worsened:
  - upsell attempts too frequent
```

---

# 19. Deployment and Monitoring

## Environments

```txt
local
dev
staging
production
client-sandbox
```

## Local development

```txt
docker compose up
```

Services:

```txt
web
api
agent-runtime
postgres
redis
worker
observability
```

## Production deployment options

### Option A: LiveKit Cloud + our agent workers

Best for speed.

```txt
LiveKit Cloud
Agent Runtime on AWS ECS/EKS/Fargate
API on AWS
Postgres on RDS/Supabase
Redis on ElastiCache/Upstash
Frontend on Vercel/CloudFront
```

### Option B: Fully self-hosted LiveKit

Best for enterprise/control later.

LiveKit supports custom deployments, while LiveKit Cloud can still be used for media transport and observability in hybrid setups. ([LiveKit Docs][11])

```txt
LiveKit Server on Kubernetes
Ingress / TURN / Redis
Agent workers on Kubernetes
Postgres
Redis
Prometheus/Grafana
Loki
Sentry
```

## Monitoring

Track:

```txt
Agent worker health
Room join failures
STT provider failures
LLM timeout rate
TTS timeout rate
Tool latency
Average time to first audio
Barge-in success rate
Call crash rate
Cost spikes
Client-specific errors
```

## Alerts

```txt
P1:
  - agent runtime down
  - LiveKit connection failures > threshold
  - sessions failing to start

P2:
  - TTS provider failure > 5%
  - LLM latency > 3s p95
  - tool failure > 10%

P3:
  - cost per call above target
  - fallback rate rising
  - prompt regression
```

---

# 20. Frontend React App

Use `agent-starter-react` as the foundation.

## Frontend apps

```txt
apps/web/
  app/
    demo/
      page.tsx

    client/[clientId]/voice/
      page.tsx

    admin/
      clients/
      sessions/
      analytics/
      prompts/
      simulations/
      settings/
```

## Voice UI requirements

The first version should have:

```txt
Start conversation button
Mute/unmute
End session
Live transcript
Agent transcript
Connection status
Speaking/listening indicator
Audio visualization
Session ID
Debug panel in dev mode
```

## Later UI additions

```txt
Avatar
Client branding
Embedded widget
Call summary
Human handoff button
Admin playback
Agent comparison mode
```

---

# 21. Database Design

Use Postgres.

## Core tables

```sql
clients
agents
client_agent_configs
sessions
session_turns
tool_calls
prompt_versions
client_prompt_overrides
knowledge_sources
analytics_events
cost_events
simulations
simulation_results
fallback_events
human_handoffs
```

## Example tables

```sql
clients (
  id uuid primary key,
  name text,
  vertical text,
  timezone text,
  status text,
  created_at timestamp
);

sessions (
  id uuid primary key,
  client_id uuid references clients(id),
  agent_id uuid,
  livekit_room_name text,
  channel text,
  started_at timestamp,
  ended_at timestamp,
  status text,
  total_cost_usd numeric,
  summary text
);

session_turns (
  id uuid primary key,
  session_id uuid references sessions(id),
  turn_index int,
  role text,
  transcript text,
  started_at timestamp,
  ended_at timestamp,
  interrupted boolean,
  latency_ms int
);

tool_calls (
  id uuid primary key,
  session_id uuid references sessions(id),
  tool_name text,
  input_json jsonb,
  output_json jsonb,
  status text,
  latency_ms int,
  created_at timestamp
);
```

---

# 22. Security and Compliance

## Required

```txt
Client isolation
API key encryption
Role-based admin access
Audit logs
PII redaction
Session retention policy
Signed LiveKit tokens
Environment-based secrets
Tool-level permission checks
```

## For healthcare/pharma clients later

```txt
HIPAA-ready architecture
No PHI in logs by default
PII/PHI redaction
BAA-compatible providers
Strict retention settings
Human review workflows
```

---

# 23. Human Handoff

Every production agent needs graceful handoff.

## Handoff triggers

```txt
User asks for human
Repeated misunderstanding
Angry/frustrated user
Payment issue
Compliance-sensitive request
Tool/API failure
High-value lead
Emergency or safety issue
```

## Handoff options

```txt
Create callback request
Send Slack/Teams notification
Send SMS to manager
Transfer to human later via telephony
Create CRM ticket
Email summary
```

## Handoff summary

```json
{
  "customer_name": "John",
  "phone": "2145550199",
  "intent": "place_order",
  "summary": "Customer wanted to place a pickup order but had a payment issue.",
  "current_state": "payment_question",
  "recommended_action": "Call customer back."
}
```

---

# 24. Multi-Client Architecture

## Core idea

One runtime, many agents.

```txt
Core runtime stays same.
Client config changes.
Prompt changes.
Tools change.
Knowledge base changes.
Voice changes.
Analytics separated by client.
```

## Agent templates

```txt
restaurant_order_agent
clinic_receptionist_agent
real_estate_lead_agent
pharma_support_agent
bpo_customer_service_agent
appointment_booking_agent
internal_helpdesk_agent
```

Each template includes:

```txt
Default prompt
Default tools
Default state machine
Default analytics
Default simulation tests
Default fallback rules
```

---

# 25. Phase-by-Phase Build Plan

## Phase 0 — Repo Setup

Goal: set up the monorepo.

Tasks:

```txt
Create voixai-platform repo
Add apps/web from agent-starter-react
Add apps/agent-runtime from agent-starter-python
Add apps/api FastAPI service
Add docker-compose
Add .env.example files
Add shared docs folder
Add basic README
```

Deliverable:

```txt
Local web app can connect to LiveKit.
Python agent can join a room.
User can speak to basic agent.
```

---

## Phase 1 — Basic LiveKit Voice Agent

Goal: working browser-to-agent voice conversation.

Tasks:

```txt
Configure LiveKit project
Generate room token from API
React app joins room
Python agent joins room
Agent listens and responds
Show transcript in UI
```

Acceptance:

```txt
User clicks Start
User speaks
Agent responds with voice
Transcript appears
Session ends cleanly
```

---

## Phase 2 — Production Pipeline Abstraction

Goal: provider-swappable STT/LLM/TTS.

Tasks:

```txt
Create STTProvider interface
Create LLMProvider interface
Create TTSProvider interface
Add provider config
Add fallback provider support
Add latency tracking per provider
```

Acceptance:

```txt
Can switch STT/LLM/TTS via config without rewriting agent logic.
```

---

## Phase 3 — Turn Detection and Interruption

Goal: natural conversation flow.

Tasks:

```txt
Implement VAD/endpointing config
Implement semantic turn checks
Implement barge-in cancellation
Track interrupted messages
Add UI speaking/listening indicators
```

Acceptance:

```txt
User can interrupt agent.
Agent stops speaking quickly.
Agent continues with corrected context.
```

---

## Phase 4 — Conversation State Machine

Goal: reliable business workflows.

Tasks:

```txt
Create ConversationState object
Create StateMachine abstraction
Build restaurant order state machine
Track missing fields
Track confirmations
Persist turns to database
```

Acceptance:

```txt
Agent can collect order details without losing state.
Agent asks only for missing fields.
```

---

## Phase 5 — Tool Execution Framework

Goal: agent can perform actions.

Tasks:

```txt
Create Tool base class
Create ToolRouter
Add tool permission policy
Add mock restaurant menu tool
Add mock create order tool
Add idempotency keys
Add tool call logs
```

Acceptance:

```txt
Agent can search menu and prepare order.
Agent does not submit order without confirmation.
```

---

## Phase 6 — Client Configuration System

Goal: multi-client readiness.

Tasks:

```txt
Create clients table
Create client_agent_configs table
Add config loader
Add client-specific prompt overrides
Add vertical-specific templates
Add admin seed data
```

Acceptance:

```txt
Same agent runtime can behave differently for two clients.
```

---

## Phase 7 — Prompt Registry and Versioning

Goal: safe prompt iteration.

Tasks:

```txt
Create prompt registry package
Add prompt renderer
Add prompt version hash
Store prompt version per session
Add prompt comparison
Add rollback support
```

Acceptance:

```txt
Every session records exact prompt/model/voice configuration.
```

---

## Phase 8 — Analytics and Cost Metering

Goal: business-grade reporting.

Tasks:

```txt
Emit analytics events per turn
Track STT seconds
Track LLM tokens
Track TTS chars
Track LiveKit session duration
Calculate cost per session
Build analytics dashboard
```

Acceptance:

```txt
Admin can see cost per call, latency, completion rate, and fallback rate.
```

---

## Phase 9 — Testing and Simulation

Goal: avoid regressions.

Tasks:

```txt
Create golden conversation format
Create simulation runner
Add restaurant happy path tests
Add interruption tests
Add noisy transcript tests
Add tool failure tests
Add prompt regression report
```

Acceptance:

```txt
Before deployment, we can compare agent v1 and v2 on simulated calls.
```

---

## Phase 10 — Admin Dashboard

Goal: client and agent management.

Tasks:

```txt
Client list
Client config editor
Prompt version viewer
Session history
Call transcript viewer
Cost dashboard
Simulation runner UI
```

Acceptance:

```txt
Non-engineer can configure and review client agents.
```

---

## Phase 11 — Production Deployment

Goal: deploy stable staging/production.

Tasks:

```txt
Dockerize services
Deploy API
Deploy agent workers
Deploy frontend
Set secrets
Set CI/CD
Set monitoring
Set alerts
Add health checks
```

Acceptance:

```txt
Production environment supports multiple simultaneous web voice sessions.
```

---

## Phase 12 — Client Pilot Package

Goal: sellable MVP.

Tasks:

```txt
Create restaurant demo agent
Create receptionist demo agent
Create lead qualification demo agent
Create sales deck/demo script
Create client onboarding checklist
Create pricing calculator
```

Acceptance:

```txt
We can demo VoixAI to clients as a real platform, not a toy project.
```

---

# 26. First Client Demo: Restaurant Agent

Since we already started with Wingstop-style ordering, use it as the first showcase.

## Demo capabilities

```txt
Greeting
Menu questions
Order taking
Modifiers
Upsell
Pickup time
Order recap
Final confirmation
Mock order submission
Call summary
Analytics dashboard
```

## Demo flow

```txt
User: I want to order wings.
Agent: Sure — pickup or delivery?
User: Pickup.
Agent: Got it. What would you like?
User: Ten piece lemon pepper, classic.
Agent: Nice. Do you want that as a combo with fries and a drink?
User: Yeah, Coke.
Agent: Perfect. Pickup in about 20 minutes?
User: Actually make it boneless.
Agent: Sure — switching that to boneless...
```

This demo should show:

* Low latency
* Natural interruption
* State correction
* Tool call
* Confirmation
* Analytics
* Cost per call

---

# 27. What Makes This Better Than Basic Voice Agent Demos

Most demos only show:

```txt
Mic input -> AI answer -> Voice output
```

Our platform should show:

```txt
Realtime audio
Natural turn-taking
Interruptions
Stateful workflows
Tool execution
Client-specific behavior
Prompt versions
Simulations
Analytics
Cost metering
Fallbacks
Deployment
Monitoring
Multi-client configuration
```

That is what makes it production-grade.

---

# 28. Immediate Next Implementation Order

Do this in order:

```txt
1. Clone both LiveKit starter repos into monorepo.
2. Make basic browser voice conversation work.
3. Add API service for token generation and session creation.
4. Add session persistence.
5. Add provider abstraction for STT/LLM/TTS.
6. Add interruption handling and latency tracking.
7. Add restaurant state machine.
8. Add mock tools.
9. Add client config.
10. Add analytics/cost dashboard.
11. Add simulation tests.
12. Deploy staging.
```

---

# 29. Recommended Tech Stack

```txt
Frontend:
  Next.js
  React
  LiveKit React SDK / Agents UI
  Tailwind CSS
  shadcn/ui
  Recharts

Agent Runtime:
  Python
  LiveKit Agents
  FastAPI-compatible shared modules
  Pydantic
  AsyncIO
  Redis

API:
  FastAPI
  PostgreSQL
  SQLAlchemy / SQLModel
  Alembic
  Redis
  JWT / Clerk / Auth.js later

Infra:
  Docker
  AWS ECS or EKS
  RDS Postgres
  ElastiCache Redis
  CloudWatch
  Sentry
  Grafana later

AI Providers:
  OpenAI
  Anthropic
  Gemini
  Deepgram
  ElevenLabs
  Cartesia/Rime
  OpenRouter
```

---

# 30. Final Architecture Decision

Use **LiveKit as the real-time media layer**, **Python LiveKit Agents as the voice runtime**, and **Next.js React as the client/demo/admin frontend**.

Use a **cascaded streaming STT → LLM → TTS pipeline first**, because it gives the most control for multi-client business workflows, tool execution, analytics, prompt management, and fallback handling.

Build the platform as:

```txt
Voice Agent Runtime
+ Multi-Client Config Platform
+ Prompt/Tool Registry
+ Simulation/Evaluation System
+ Analytics/Cost Metering
+ Admin Dashboard
```

This becomes a real service business: each new client gets a configured agent on top of the same core engine.

[1]: https://docs.livekit.io/agents/?utm_source=chatgpt.com "Introduction | LiveKit Documentation"
[2]: https://github.com/livekit-examples/agent-starter-python?utm_source=chatgpt.com "A complete voice AI starter for LiveKit Agents with Python."
[3]: https://github.com/livekit-examples/agent-starter-react?utm_source=chatgpt.com "livekit-examples/agent-starter-react"
[4]: https://github.com/livekit/livekit?utm_source=chatgpt.com "LiveKit: Real-time video, audio and data for developers"
[5]: https://arxiv.org/abs/2603.05413?utm_source=chatgpt.com "Building Enterprise Realtime Voice Agents from Scratch: A Technical Tutorial"
[6]: https://livekit.com/blog/realtime-vs-cascade?utm_source=chatgpt.com "Pipeline vs. Realtime - Which is the better Voice Agent ..."
[7]: https://docs.livekit.io/agents/logic/turns/?utm_source=chatgpt.com "Turns overview"
[8]: https://livekit.com/blog/turn-detection-voice-agents-vad-endpointing-model-based-detection?utm_source=chatgpt.com "Turn Detection for Voice Agents: VAD, Endpointing, and ..."
[9]: https://livekit.com/?utm_source=chatgpt.com "LiveKit: Build voice, video, and physical AI"
[10]: https://docs.livekit.io/deploy/observability/insights/?utm_source=chatgpt.com "Agent insights in LiveKit Cloud"
[11]: https://docs.livekit.io/deploy/custom/deployments/?utm_source=chatgpt.com "Self-hosted deployments"
