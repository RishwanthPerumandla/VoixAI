```markdown
# VoixAI v2.0 - Autonomous AI Voice Agent Specification

## 1. Project Overview

**Goal:** Build an autonomous, full-duplex AI voice agent for Wingstop that handles open-ended conversations, not scripted flows.

**Key Difference from v1.0:**
- v1.0: Hardcoded state machine with template responses
- v2.0: Autonomous agent with reasoning, tool use, and dynamic generation

**Core Capabilities:**
- Natural, open-ended conversation (no fixed states)
- Tool-augmented reasoning (menu search, pricing, orders, tickets)
- Real-time upsell optimization
- Issue resolution with ticket creation
- Graceful handling of interruptions, changes, questions

---

## 2. Architecture

### 2.1 High-Level Flow

```
Audio Input → VAD → Streaming ASR → Agent Core → Streaming TTS → Audio Output
                    ↓                    ↑
               [Interrupt Detector]  [Tool Calls]
                    ↓                    ↑
               [Prosody Analysis]    [Memory/Context]
```

### 2.2 Agent Core (ReAct Loop)

```
┌─────────────────────────────────────────┐
│           AGENT ORCHESTRATOR            │
│                                         │
│  1. UNDERSTAND: Intent + Entities +     │
│     Sentiment + Urgency                 │
│                                         │
│  2. REASON: What should I do?           │
│     - Retrieve context                  │
│     - Plan actions                      │
│     - Check policies                    │
│                                         │
│  3. ACT: Execute tools                  │
│     - search_menu, calculate_price      │
│     - create_order, create_ticket       │
│     - escalate_to_human                 │
│                                         │
│  4. GENERATE: Natural response          │
│     - Grounded in tool results          │
│     - Varied, not templated             │
│     - Prosody-appropriate               │
│                                         │
│  5. SPEAK: Stream audio                 │
│     - Interruptible                     │
│     - Backchannels while listening      │
│                                         │
└─────────────────────────────────────────┘
```

### 2.3 Component Stack

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| **ASR** | Whisper `base.en` (local) | Streaming transcription |
| **VAD** | Silero VAD | Speech detection, interruption |
| **LLM** | Groq `llama-3.3-70b-versatile` | Reasoning, generation |
| **TTS** | Kokoro ONNX | Fast synthesis |
| **Memory** | SQLite (session) + JSON (working) | Context, history |
| **Tools** | Python functions | Business logic |

---

## 3. File Structure

```
voixai-v2/
├── .env
├── requirements.txt
├── config.yaml
├── main.py                      # FastAPI + WebSocket entry
├── core/
│   ├── __init__.py
│   ├── agent.py                 # ReAct orchestrator
│   ├── understanding.py         # Intent + entity extraction
│   ├── reasoning.py             # Planning + tool selection
│   ├── action.py                # Tool execution
│   ├── generation.py            # Response synthesis
│   ├── memory.py                # Short + long-term storage
│   ├── tools.py                 # Tool definitions
│   ├── stt_engine.py            # Streaming Whisper
│   ├── tts_engine.py            # Kokoro synthesis
│   ├── audio_stream.py          # VAD + buffering
│   └── interrupt_handler.py     # Barge-in detection
├── models/
│   └── kokoro-v1.0.onnx         # TTS model
├── static/
│   └── index.html               # Web UI
├── data/
│   ├── menu.json                # Wingstop menu
│   ├── policies.json            # Business rules
│   └── orders.db                # SQLite database
└── tests/
    └── test_agent.py
```

---

## 4. Configuration (config.yaml)

```yaml
app:
  name: "VoixAI v2.0"
  version: "2.0.0"

audio:
  sample_rate: 16000
  chunk_duration_ms: 30
  vad_threshold: 0.5
  vad_silence_ms: 600
  interruption_threshold: 0.7

asr:
  model: "base.en"              # tiny.en (fast) | base.en (balanced) | small.en (accurate)
  compute_type: "int8"
  language: "en"
  streaming: true

llm:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
  temperature: 0.3
  max_tokens: 150
  timeout_seconds: 2.0

tts:
  model_path: "models/kokoro-v1.0.onnx"
  voice: "af_bella"
  speed: 1.2
  streaming: true

agent:
  max_turns: 50
  working_memory_turns: 5
  confidence_threshold: 0.7
  
  # Response strategies
  strategies:
    discovery: "socratic_questioning"
    confirmation: "mirroring_specific"
    upsell: "social_proof_value"
    recovery: "acknowledge_fix"
    complaint: "empathy_action"

memory:
  session_db: "data/orders.db"
  working_memory_file: "data/working_memory.json"

tools:
  enabled:
    - search_menu
    - calculate_price
    - validate_order
    - create_order
    - modify_order
    - create_ticket
    - escalate_to_human
    - get_order_status
    - suggest_upsell
```

---

## 5. Core Components Specification

### 5.1 Understanding Module (core/understanding.py)

**Purpose:** Extract meaning from user input (text + audio features)

**Inputs:**
- Transcribed text
- Audio features (energy, pitch, pace)
- Conversation history

**Outputs:**
```python
{
    "intent": {
        "primary": "ordering|information|service|conversation|escalation",
        "confidence": 0.95,
        "sub_intent": "new_order|modify_order|cancel|complaint|question"
    },
    "entities": [
        {
            "type": "item|quantity|flavor|modifier|time|preference",
            "value": "lemon_pepper",
            "confidence": 0.92,
            "start": 10,
            "end": 22
        }
    ],
    "sentiment": {
        "polarity": "positive|neutral|negative",
        "urgency": "low|medium|high",
        "frustration": 0.3  # 0-1 scale
    },
    "context_signals": {
        "is_question": true,
        "is_interruption": false,
        "is_hesitation": false,
        "references_previous": ["wings", "combo"]
    }
}
```

**Implementation:**
- Use LLM for intent classification with few-shot examples
- Regex + fuzzy matching for entity extraction
- Audio energy for interruption detection
- Sentiment analysis via lightweight model or LLM

---

### 5.2 Reasoning Module (core/reasoning.py)

**Purpose:** Decide what to do based on understanding + context

**ReAct Pattern:**
```python
class ReActStep:
    thought: str      # Internal reasoning
    action: str       # Tool to call
    action_input: dict  # Parameters
    observation: str  # Tool result
    final_answer: str  # Generated response (if done)
```

**Reasoning Triggers:**

| Situation | Thought Pattern | Action |
|-----------|----------------|--------|
| Customer unsure | "They're in discovery mode, need to narrow preferences" | ask_preference("heat_level") |
| Order complete | "Have items, should suggest combo before confirming" | suggest_upsell("combo") |
| Complaint detected | "Negative sentiment, need empathy + ticket" | create_ticket + apologize |
| Mid-order question | "They're asking about nutrition, should answer then continue" | search_menu + resume_order |
| High frustration | "Anger detected, may need escalation" | empathy_response + offer_human |

---

### 5.3 Action Module (core/action.py)

**Tool Definitions:**

#### search_menu
```python
{
    "name": "search_menu",
    "description": "Find menu items matching criteria",
    "parameters": {
        "query": "spicy wings",           # Natural language
        "category": "wings|sides|drinks|desserts|combos",
        "dietary": "vegetarian|gluten_free|keto",
        "max_price": 20.00,
        "limit": 5
    },
    "returns": [
        {
            "name": "Mango Habanero Wings",
            "category": "wings",
            "description": "Sweet mango with habanero kick",
            "price": {"6pc": 10.99, "8pc": 13.99, "10pc": 16.99},
            "heat_level": 3,
            "popular": true,
            "available": true
        }
    ]
}
```

#### calculate_price
```python
{
    "name": "calculate_price",
    "description": "Calculate total with tax, discounts, combos",
    "parameters": {
        "items": [...],
        "apply_combo_discounts": true,
        "tax_rate": 0.08
    },
    "returns": {
        "subtotal": 18.99,
        "tax": 1.52,
        "total": 20.51,
        "savings": 3.00,
        "breakdown": [...]
    }
}
```

#### create_order
```python
{
    "name": "create_order",
    "description": "Finalize order in database",
    "parameters": {
        "customer_name": "Mike",
        "items": [...],
        "payment_method": "at_pickup|card_now",
        "special_instructions": "Extra crispy"
    },
    "returns": {
        "order_id": "WS-2024-001234",
        "estimated_ready": "2024-01-15T18:30:00Z",
        "total": 20.51
    }
}
```

#### create_ticket
```python
{
    "name": "create_ticket",
    "description": "Create support ticket for issues",
    "parameters": {
        "type": "complaint|refund|missing_item|quality_issue",
        "description": "Wings were cold",
        "order_id": "WS-2024-001234",
        "severity": "low|medium|high",
        "auto_resolve": false
    },
    "returns": {
        "ticket_id": "TKT-5678",
        "status": "open",
        "estimated_response": "15 minutes"
    }
}
```

#### escalate_to_human
```python
{
    "name": "escalate_to_human",
    "description": "Transfer to human agent",
    "parameters": {
        "reason": "complex_issue|angry_customer|technical_problem",
        "urgency": "normal|urgent",
        "context_summary": "Customer wants refund for $50 order, claims food poisoning"
    },
    "returns": {
        "queue_position": 2,
        "estimated_wait": "5 minutes",
        "handoff_success": true
    }
}
```

#### suggest_upsell
```python
{
    "name": "suggest_upsell",
    "description": "Generate personalized upsell suggestion",
    "parameters": {
        "current_order": [...],
        "customer_history": [...],
        "conversation_stage": "early|mid|closing"
    },
    "returns": {
        "type": "combo|size_upgrade|side|drink|dessert|loyalty",
        "suggestion": "Make it a combo for $3 more? You get fries and a drink.",
        "value_proposition": "Saves $2.50",
        "target_price": 19.99
    }
}
```

---

### 5.4 Generation Module (core/generation.py)

**Purpose:** Create natural, varied responses grounded in tool results

**Constraints:**
- 5-20 words for simple responses
- 20-40 words for explanations
- Never templated (varied phrasing)
- Match sentiment (empathy for complaints, energy for upsells)

**Response Types:**

| Type | Example | Strategy |
|------|---------|----------|
| **Discovery** | "Spicy or safe?" | Binary choice, reduce cognitive load |
| **Recommendation** | "Lemon Pepper's our #1—tangy, citrusy, why people come here" | Social proof + sensory |
| **Confirmation** | "10 boneless Lemon Pepper, got it" | Mirroring + brevity |
| **Upsell** | "Make it a combo? Saves $3, you get fries + drink" | Value first, then components |
| **Recovery** | "My bad, changing that to 15 now" | Acknowledge + action, no excess apology |
| **Complaint** | "That's frustrating—fixing it right now" | Empathy + immediate action |

**Anti-Patterns (Never Generate):**
- "As an AI assistant..."
- "I apologize for the inconvenience"
- "Please hold while I..."
- Repetitive phrasing across turns

---

### 5.5 Memory Module (core/memory.py)

**Working Memory (Session):**
```python
{
    "session_id": "uuid",
    "customer": {
        "name": "Mike",
        "phone": "...",
        "history_summary": "Regular, likes Lemon Pepper, usually orders 10pc"
    },
    "current_order": {
        "items": [...],
        "stage": "building|confirming|completed",
        "offered_upsells": ["combo"],
        "accepted_upsells": [],
        "pending_modification": null
    },
    "conversation": {
        "turns": [...],  # Last 5 for context
        "topics_discussed": ["flavors", "heat_level"],
        "customer_preferences": {"heat": "mild", "style": "boneless"}
    }
}
```

**Long-Term (SQLite):**
- Customer profiles (preferences, order history)
- Conversation logs (for training, analytics)
- Ticket history (issues, resolutions)

---

### 5.6 Interrupt Handler (core/interrupt_handler.py)

**Dual-Path Audio Processing:**

```
Audio Stream ──┬──▶ [Fast Path] Energy Detection ──▶ Interrupt Signal (50ms)
               │
               └──▶ [Slow Path] ASR ──▶ Understanding ──▶ Response (500ms)
```

**Interrupt Triggers:**
- Energy spike > 0.7 during TTS playback
- Question intonation detected
- Explicit stop words ("wait", "no", "hold on")

**Response to Interrupt:**
1. Fade out current TTS (100ms)
2. Acknowledge: "Sorry, go ahead" or "Yeah?"
3. Process new input
4. Resume or pivot based on new intent

---

## 6. Conversation Examples (Target Behavior)

### Example 1: Discovery + Order + Upsell

```
T: "Hey! Welcome to Wingstop, I'm Tasha. What's your name?"
C: "I'm Rishi, and I have no idea what to order"

[Intent: greeting + discovery]
[Thought: Customer uncertain, need to guide preferences]
[Action: ask_preference("heat_level")]

T: "No worries Rishi, I got you. You want something spicy, or you play it safe?"
C: "Something in the middle"

[Intent: preference (medium)]
[Thought: Medium heat = Lemon Pepper, Original Hot, Louisiana Rub]
[Action: suggest_items(["lemon_pepper", "original_hot", "louisiana_rub"])]

T: "Perfect. Lemon Pepper's our #1—tangy, citrusy. Original Hot's classic vinegar kick. Louisiana Rub's smoky, no sauce. Which sounds good?"
C: "Lemon Pepper sounds good"

[Intent: selection]
[Thought: Have flavor, need size and style]
[Action: ask_order_details()]

T: "Love it. How many? We do 6, 8, 10, 15, 20, 30"
C: "10"

[Intent: quantity]
[Thought: 10 pieces, need style, then upsell opportunity]
[Action: ask_style()]

T: "10 piece, nice. Bone-in or boneless?"
C: "Boneless"

[Intent: style selected]
[Thought: Have complete item, should suggest combo (saves money)]
[Action: suggest_upsell("combo")]

T: "Boneless, got it. Want to make that a combo? $19.99, you get fries and a drink—saves $3"
C: "Sure, make it a combo"

[Intent: upsell accepted]
[Thought: Combo selected, need drink choice, then confirm]
[Action: ask_drink()]

T: "Love it. What to drink? Coke, Diet Coke, Sprite, Dr Pepper?"
C: "Coke"

[Intent: drink selected]
[Thought: Order complete, confirm before finalize]
[Action: confirm_order()]

T: "Rishi, that's 10 boneless Lemon Pepper combo with Coke. $19.99, ready in 20 minutes. Look right?"
C: "Yeah"

[Intent: confirmation]
[Thought: Order confirmed, create in system, close]
[Action: create_order + goodbye()]

T: "Perfect! Order's in. 20 minutes Rishi, $19.99 at the counter. See you soon!"
```

### Example 2: Mid-Order Modification + Question

```
[Earlier: 10 boneless Lemon Pepper ordered]

T: "Want fries or veggie sticks with that?"
C: "Actually, make that 15 wings instead"

[Intent: modification (quantity change)]
[Thought: Changing 10 to 15, keep flavor and style, recalculate price and upsell]
[Action: modify_order + recalculate_upsell()]

T: "No problem, changing to 15. Even better—15 piece combo is $23.99, still gets you fries and drink. Want that?"
C: "How much is it without the combo?"

[Intent: information_request (pricing)]
[Thought: Customer comparing, should give clear breakdown]
[Action: calculate_price(ala_carte=True)]

T: "15 boneless Lemon Pepper is $23.99, fries $3.99, drink $2.49. $30.47 total vs $23.99 combo. Combo saves $6.50"
C: "Okay, combo then"

[Intent: upsell accepted after question]
[Thought: Resolved objection, proceed]
[Action: confirm_order()]

T: "Smart choice. 15 boneless Lemon Pepper combo. $23.99, 25 minutes. Good?"
```

### Example 3: Complaint + Ticket Creation

```
T: "Hey! Welcome to Wingstop, I'm Tasha. What's your name?"
C: "Mike, and I'm pissed. My order last night was completely wrong"

[Intent: greeting + complaint (high negative sentiment)]
[Thought: Angry customer, need empathy immediately, create ticket]
[Action: empathy_response + create_ticket()]

T: "Mike, that's frustrating—getting the wrong order ruins your night. I'm fixing this right now."

[Observation: ticket created]
[Action: ask_details()]

T: "What was supposed to be in your order?"
C: "10 Lemon Pepper, got 10 Atomic. Couldn't eat them, too hot"

[Intent: complaint_details]
[Thought: Clear mistake, high heat intolerance, should offer refund + remake]
[Action: validate_order_history + offer_resolution()]

T: "That's our mistake, Mike. I'm refunding that order and putting a credit for a free 10-piece on your account. Use it anytime."
C: "I don't want to come back, just want my money back"

[Intent: rejection_of_credit (still angry)]
[Thought: Customer retention failed, escalate to human for full refund + service recovery]
[Action: escalate_to_human(urgency="high")]

T: "I understand, Mike. Getting my manager to approve full refund and add you to our priority list. Two minutes."
```

---

## 7. Database Schema (data/orders.db)

```sql
-- Customers
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    phone TEXT UNIQUE,
    name TEXT,
    preferences JSON,  -- {"heat": "mild", "favorite": "lemon_pepper"}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    items JSON,  -- [{"flavor": "lemon_pepper", "size": 10, ...}]
    total REAL,
    status TEXT,  -- building|confirmed|preparing|ready|completed|cancelled
    special_instructions TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    turns JSON,  -- Full conversation log
    intent_distribution JSON,  -- Analytics
    sentiment_trajectory JSON,
    upsell_success BOOLEAN,
    created_at TIMESTAMP
);

-- Tickets
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    type TEXT,  -- complaint|refund|missing_item|quality_issue
    description TEXT,
    order_id INTEGER,
    severity TEXT,  -- low|medium|high
    status TEXT,  -- open|in_progress|resolved|escalated
    resolution TEXT,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP
);
```

---

## 8. Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Conversation** | Completion rate | >90% |
| | Avg turns per order | <8 |
| | Human escalation rate | <3% |
| **Business** | Upsell conversion | >35% |
| | Avg ticket vs baseline | +$4 |
| | Issue resolution (no human) | >70% |
| **Technical** | First-byte latency | <500ms |
| | Turn-switch latency | <300ms |
| | Intent accuracy | >95% |
| **Experience** | Sentiment improvement | +0.5 points |
| | Customer satisfaction | >4.5/5 |

---

## 9. Implementation Phases for Kimi Code

### Phase 1: Core Agent Loop (Days 1-2)
- ReAct orchestrator
- Tool definitions (stubs)
- Basic memory
- Single-turn responses

### Phase 2: Understanding + Tools (Days 3-4)
- Intent classification
- Entity extraction
- Tool implementations (menu, pricing)
- Context management

### Phase 3: Generation + Memory (Days 5-6)
- Dynamic response generation
- Working memory (5 turns)
- Long-term memory (SQLite)
- Conversation continuity

### Phase 4: Interrupts + Polish (Days 7-8)
- Dual-path audio processing
- Interrupt handling
- Prosody-appropriate responses
- Error recovery

### Phase 5: Integration + Testing (Days 9-10)
- WebSocket streaming
- Web UI
- Load testing
- Conversation examples validated

---

## 10. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| ASR model | Whisper base.en | Balance of speed/accuracy for limited vocabulary |
| LLM | Groq 70B | Fast enough for real-time, capable reasoning |
| TTS | Kokoro | Local, fast, natural enough |
| Memory | SQLite + JSON | Simple, persistent, queryable |
| Interrupts | Energy + ASR | Fast detection + accurate understanding |
| Tools | Python functions | Flexible, testable, extensible |

---

## 11. Anti-Requirements (What NOT to Build)

- **No phone integration yet** (Web only for v2.0)
- **No payment processing** (cash/card at pickup)
- **No multi-language** (English only)
- **No voice cloning** (Kokoro voice only)
- **No real-time learning** (batch analysis post-hoc)

---
