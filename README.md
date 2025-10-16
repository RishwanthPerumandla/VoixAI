# 🎙️ VoixAI — AI Voice Ordering System (MVP Documentation)

---

## 🧩 Project Overview

The **VoixAI Voice Ordering System** aims to automate *call-in pickup orders* using an AI-powered conversational system that sounds human-like, understands natural language, and accurately places customer orders into a structured format.

The MVP (Minimum Viable Product) will:

* Handle real-time voice calls from customers.
* Recognize and transcribe speech to text (STT).
* Understand and parse the order using NLP.
* Confirm the order verbally with a human-like AI voice (TTS).
* Store the order in a local database for review.

The goal is to build and test this system locally (free or near-zero cost), prove functionality, and later integrate with Twilio or similar services for production.

---

## ⚙️ High-Level System Architecture (MVP)

```text
+------------------------------+
|         Phone Caller         |
+--------------+---------------+
               |
               v
+------------------------------+
|     Telephony Layer (Local)  |
|  - Asterisk / SIP.js / WebRTC|
+--------------+---------------+
               |
               v
+------------------------------+
| Speech-to-Text (STT) Engine  |
|  - Whisper (local) or AWS Transcribe |
+--------------+---------------+
               |
               v
+------------------------------+
|  NLU + Order Parser (Core)   |
|  - Intent + Entity Extraction|
|  - Order Slot Filling        |
|  - Menu & Quantity Handling  |
+--------------+---------------+
               |
               v
+------------------------------+
|  Text-to-Speech (TTS) Engine |
|  - ElevenLabs / Coqui / Polly|
+--------------+---------------+
               |
               v
+------------------------------+
| Local Database (SQLite)      |
|  - Stores Orders & Metadata  |
+--------------+---------------+
               |
               v
+------------------------------+
|   Developer Dashboard (CLI)  |
|  - Monitor Orders / Logs     |
+------------------------------+
```

---

## ⚙️ Core Components Breakdown

### 1. Telephony Layer (Local Simulation)

* **Goal:** Simulate or receive calls locally.
* **Tools:**

  * **Option 1 (Local Testing):** Asterisk PBX or SIP.js with WebRTC frontend.
  * **Option 2 (Production):** Twilio Voice, Vonage, or AWS Connect.
* **Functionality:**

  * Capture live audio stream.
  * Forward stream to STT in near real-time.

### 2. Speech-to-Text (STT)

* **Goal:** Convert the caller’s voice into text.
* **Options:**

  * **Local:** OpenAI Whisper (via API or local inference).
  * **Cloud:** AWS Transcribe (cheap pay-per-use).
* **MVP Choice:** Whisper (local model for cost-free development).

### 3. Natural Language Understanding (NLU)

* **Goal:** Understand customer intent and extract structured order details.
* **Approach:**

  * Parse phrases like: *“I’d like 10 lemon pepper wings and a Coke.”*
  * Extract:

    * Item: `lemon pepper wings`
    * Quantity: `10`
    * Drink: `Coke`
* **Tools:** SpaCy, Rasa NLU, or custom regex/LLM parser.
* **MVP Choice:** Lightweight custom parser (regex + rule-based), later extend with Rasa or LLM.

### 4. Text-to-Speech (TTS)

* **Goal:** Reply with a natural, human-like voice.
* **Options:**

  * **Local/Free:** Coqui TTS (open-source).
  * **Cloud:** ElevenLabs (most realistic) or AWS Polly.
* **MVP Choice:** Coqui TTS for local testing, then switch to ElevenLabs for demo.

### 5. Database & Order Storage

* **Goal:** Store all structured orders.
* **Tech:** SQLite for local testing (PostgreSQL later for production).
* **Schema Example:**

  ```sql
  orders (
    id INTEGER PRIMARY KEY,
    customer_name TEXT,
    order_items JSON,
    total_price REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ```

### 6. Developer Dashboard / CLI

* **Goal:** Monitor all interactions and orders.
* **Functionality:**

  * Display recognized text and structured order.
  * Show conversation flow.
  * Allow order confirmation or replay.

---

## 🧰 Tech Stack Summary (MVP Focused)

| Layer                 | Tool/Tech                 | Mode  | Notes                           |
| --------------------- | ------------------------- | ----- | ------------------------------- |
| **Telephony**         | Asterisk / SIP.js / Twilio| Local | For call simulation             |
| **STT**               | Whisper                   | Local | Free, accurate, runs on CPU/GPU |
| **NLU**               | Python (Regex + SpaCy)    | Local | Extract intent/entities         |
| **TTS**               | Coqui TTS                 | Local | Human-like free voice synthesis |
| **DB**                | SQLite                    | Local | Store orders                    |
| **Backend**           | FastAPI                   | Local | API for all modules             |
| **Containerization**  | Docker                    | Local | One-command startup             |
| **Logging/Debugging** | Python logging + Rich CLI | Local | Realtime conversation tracing   |

---

## 🧪 Testing Strategy (MVP)

| Phase       | Type       | Description                                                      |
| ----------- | ---------- | ---------------------------------------------------------------- |
| **Phase 1** | Manual     | Developer manually simulates calls using local microphone input. |
| **Phase 2** | Controlled | Test using pre-recorded voice samples.                           |
| **Phase 3** | Live       | Connect Twilio sandbox for real inbound call test.               |

---

## 💰 Cost Optimization Plan

* Use **local inference (Whisper + Coqui)** instead of paid APIs during MVP.
* Deploy lightweight Docker containers.
* Only use **AWS Polly/Transcribe** or **ElevenLabs** when demoing.
* Keep call simulations local — no telephony cost initially.

---

## 🚀 Future Enhancements

1. **POS Integration:** Connect to restaurant POS or ordering APIs for automatic order injection.
2. **Menu Adaptation System:** Upload JSON menu to auto-train intent parser.
3. **Multi-Restaurant Support:** Generalize for SaaS use (e.g., Pizza Hut, Chipotle).
4. **Payment Processing:** Add Stripe or Square for phone payments.
5. **Analytics Dashboard:** Track total calls, order volume, and performance metrics.

---

## 🧭 Next Steps

1. **Phase 1 Setup (Local MVP):**

   * Implement Whisper + Coqui + FastAPI base.
   * Mock telephony input/output locally.
   * Parse mock menu JSON for order extraction.
2. **Phase 2 Integration:**

   * Integrate Twilio or Asterisk call stream.
   * Enable real-time speech loop (listen → understand → respond).
3. **Phase 3 Demo:**

   * Run live demo call simulation.
   * Record conversation and show stored order in database.

---

**Outcome:**
A fully local, cost-efficient, AI-powered phone ordering prototype demonstrating real-world capability for automating Quick Service Restaurant (QSR) pickup orders.

---

**Author:** Rishwanth Perumandla
**Status:** MVP Planning Complete
**Version:** 1.0
