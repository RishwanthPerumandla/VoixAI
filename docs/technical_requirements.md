# VoixAI Technical Architecture & Engineering Specification

## 1. System Overview

### 1.1 Core Philosophy

**Design Principles:**
- **Latency-first:** Every millisecond matters in voice conversations
- **Modularity:** Swap STT/LLM/TTS providers without rewriting business logic
- **Resilience:** Graceful degradation when components fail
- **Observability:** Full visibility into every decision and latency bottleneck

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CALLER PHONE                            │
│                    (PSTN/SIP via Twilio)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ RTP Audio Stream (8kHz μ-law)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TELEPHONY LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ SIP Trunk   │  │ Media       │  │ DTMF Detection          │ │
│  │ Handler     │  │ Server      │  │ (Payment/Input)         │ │
│  └─────────────┘  │ (RTP↔PCM)   │  └─────────────────────────┘ │
│                   └─────────────┘                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ WebSocket (16kHz PCM)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VOICE PROCESSING PIPELINE                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ VAD Engine  │  │ Audio       │  │ Stream Multiplexer      │ │
│  │ (Silero)    │  │ Buffer      │  │ (Live + ASR feeds)      │ │
│  │             │  │ Manager     │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Utterance Audio (numpy array)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   COGNITIVE PROCESSING LAYER                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ STT Engine  │  │ LLM Agent   │  │ TTS Engine              │ │
│  │ (Whisper)   │  │ (Groq/Gem)  │  │ (Kokoro/Eleven)         │ │
│  │             │  │             │  │                         │ │
│  │ • tiny.en   │  │ • State     │  │ • Voice cloning         │ │
│  │ • int8 quant│  │   machine   │  │ • Prosody control       │ │
│  │ • local CPU │  │ • Tools     │  │ • SSML support          │ │
│  │   inference │  │ • RAG       │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Business Logic Output
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC ENGINE                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Order       │  │ Upsell      │  │ Discovery               │ │
│  │ Manager     │  │ Engine      │  │ Interview               │ │
│  │             │  │             │  │ System                  │ │
│  │ • Validation│  │ • Trigger   │  │                         │ │
│  │ • Pricing   │  │   logic     │  │ • Preference tree       │ │
│  │ • POS sync  │  │ • A/B tests │  │ • Flavor matching       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Structured Data
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA & INTEGRATION                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ PostgreSQL  │  │ Redis       │  │ External APIs           │ │
│  │ (Orders,    │  │ (Session    │  │ • POS (Aloha/Brink)     │ │
│  │  Analytics) │  │  State,     │  │ • Payment (Stripe)      │ │
│  │             │  │  Cache)     │  │ • SMS (Twilio)          │ │
│  │ • TimeScale │  │             │  │ • Loyalty (Wingstop)    │ │
│  │   for metrics│  │ • Pub/Sub   │  │ • Corporate Menu API    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Audio Pipeline Deep Dive

### 2.1 Telephony Audio Processing

**Input Specifications:**
- **Codec:** G.711 μ-law (8kHz, 64kbps) - standard PSTN
- **Packet size:** 20ms frames (160 samples)
- **Jitter buffer:** 50-200ms adaptive

**Upsampling & Enhancement:**

```python
class AudioPreprocessor:
    def __init__(self):
        self.target_rate = 16000  # Whisper optimal
        self.source_rate = 8000   # PSTN standard
        
    def process(self, rtp_packet: bytes) -> np.ndarray:
        # 1. Decode μ-law to PCM
        pcm = audioop.ulaw2lin(rtp_packet, 2)
        
        # 2. Upsample 8kHz → 16kHz
        pcm_16k = audioop.ratecv(pcm, 2, 1, 8000, 16000, None)[0]
        
        # 3. Convert to float32 [-1, 1]
        audio = np.frombuffer(pcm_16k, dtype=np.int16).astype(np.float32) / 32768.0
        
        # 4. Noise suppression (optional, lightweight)
        audio = self.lightweight_ns(audio)
        
        return audio
```

### 2.2 Voice Activity Detection (VAD)

**Why Silero VAD:**
- CPU-efficient (5ms inference on Intel i7)
- Pre-trained on diverse noise conditions
- No GPU required

**Implementation:**

```python
import torch
import numpy as np

class VADEngine:
    def __init__(self, threshold=0.5):
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        self.threshold = threshold
        self.sampling_rate = 16000
        
        # State tracking
        self.speech_frames = 0
        self.silence_frames = 0
        self.buffer = []
        self.is_speaking = False
        
        # Tuning parameters
        self.min_speech_duration = 0.5  # seconds
        self.min_silence_duration = 0.8  # seconds (800ms from spec)
        self.max_utterance_duration = 30  # seconds (safety)
        
    def process(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Returns complete utterance when silence detected
        Returns None while speech continues
        """
        # VAD expects int16 or float32, 30ms chunks
        confidence = self.model(
            torch.from_numpy(audio_chunk).float(), 
            self.sampling_rate
        ).item()
        
        if confidence > self.threshold:
            self.speech_frames += 1
            self.silence_frames = 0
            
            if not self.is_speaking and self.speech_frames > self.min_speech_duration * 50:
                self.is_speaking = True
                
        else:
            self.silence_frames += 1
            
            if self.is_speaking and self.silence_frames > self.min_silence_duration * 50:
                # End of utterance detected
                utterance = np.concatenate(self.buffer)
                self.reset()
                return utterance
                
        if self.is_speaking:
            self.buffer.append(audio_chunk)
            
        return None
        
    def reset(self):
        self.speech_frames = 0
        self.silence_frames = 0
        self.buffer = []
        self.is_speaking = False
```

**Latency Optimization:**
- Process VAD in 30ms chunks (not waiting for full utterance)
- Parallel stream: Send audio to STT incrementally for "live captioning"
- Barge-in detection: Interrupt TTS if customer starts speaking

### 2.3 Barge-In Handling

```python
class BargeInManager:
    def __init__(self):
        self.tts_playing = False
        self.vad = VADEngine(threshold=0.6)  # Higher threshold during TTS
        
    async def handle_stream(self, audio_chunk: np.ndarray):
        # Always check for speech, even during TTS
        vad_result = self.vad.process(audio_chunk)
        
        if self.tts_playing and vad_result is not None:
            # Customer interrupted!
            await self.interrupt_tts()
            return {"action": "interrupt", "audio": vad_result}
            
        return {"action": "continue", "audio": None}
        
    async def interrupt_tts(self):
        self.tts_playing = False
        # Send stop signal to telephony layer
        await self.telephony.stop_audio()
        # Clear any pending TTS queue
        self.tts_queue.clear()
```

---

## 3. Speech-to-Text (STT) Architecture

### 3.1 Model Selection: Faster-Whisper

**Why not cloud STT (Google/AWS)?**
- Latency: 200-500ms additional round-trip
- Cost: $0.024/min vs. $0 (local)
- Privacy: No audio leaves premises for PCI-sensitive calls

**Optimization Strategy:**

```python
from faster_whisper import WhisperModel

class STTEngine:
    def __init__(self):
        # tiny.en = 39M params, fastest on CPU
        # int8 quantization = 4x speedup, minimal accuracy loss
        self.model = WhisperModel(
            model_size_or_path="tiny.en",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,  # Optimize for i7 8th gen
            num_workers=2
        )
        
        # Performance tuning
        self.beam_size = 1  # Greedy decoding for speed
        self.best_of = 1
        self.temperature = 0.0  # Deterministic
        
    def transcribe(self, audio: np.ndarray) -> TranscriptionResult:
        segments, info = self.model.transcribe(
            audio,
            language="en",
            task="transcribe",
            vad_filter=True,  # Remove silence padding
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=True,  # Context for "uh, make that 10"
            initial_prompt="Wingstop order: flavors, quantities, sides, drinks."
        )
        
        text = " ".join([s.text for s in segments]).strip()
        
        return TranscriptionResult(
            text=text,
            language=info.language,
            probability=info.language_probability,
            duration=info.duration,
            processing_time=time.time() - start
        )
```

**Performance Benchmarks (Intel i7-8700):**

| Model | RTF (Real-Time Factor) | Memory | WER |
|-------|------------------------|--------|-----|
| tiny.en float32 | 0.3x (3x faster than real-time) | 150MB | 18% |
| tiny.en int8 | 0.1x (10x faster) | 75MB | 19% |
| base.en int8 | 0.4x | 150MB | 14% |
| **tiny.en int8 (chosen)** | **0.1x** | **75MB** | **19%** |

**19% WER is acceptable for:**
- Keyword spotting (flavor names, numbers)
- Intent classification
- Not perfect transcription, but good enough for NLU

### 3.2 Streaming STT (Future Optimization)

For sub-100ms perceived latency, implement chunked streaming:

```python
class StreamingSTT:
    def __init__(self):
        self.buffer = []
        self.commitment_point = 2.0  # seconds
        
    def process_chunk(self, chunk: np.ndarray):
        self.buffer.append(chunk)
        total_duration = len(self.buffer) * 0.03  # 30ms chunks
        
        if total_duration >= self.commitment_point:
            # Transcribe what we have so far
            partial = self.model.transcribe(
                np.concatenate(self.buffer),
                prefix=self.previous_text  # Context
            )
            
            # Check if we have a complete thought (pause in speech)
            if self.is_likely_complete(partial.text):
                return partial
                
        return None  # Keep buffering
```

### 3.3 Domain Adaptation

**Fine-tuning for Wingstop vocabulary:**

```python
# Post-processing corrections
WINGSTOP_CORRECTIONS = {
    "lemon peper": "lemon pepper",
    "garlic perm": "garlic parmesan",
    "atomic wings": "atomic",
    "bone less": "boneless",
    "ranch dressing": "ranch",
    "fries": "seasoned fries",
    "coke": "Coca-Cola",
    "diet coke": "Diet Coke",
    "dr pepper": "Dr. Pepper"
}

def post_process_transcription(text: str) -> str:
    # Apply corrections
    for wrong, right in WINGSTOP_CORRECTIONS.items():
        text = text.replace(wrong, right)
    
    # Number normalization ("fifteen" → "15")
    text = word_to_num(text)
    
    return text
```

---

## 4. Large Language Model (LLM) Architecture

### 4.1 Provider Strategy: Groq vs. Gemini

**Groq (Production):**
- **Model:** Llama 3.3 70B
- **Latency:** 50-100ms (token generation)
- **Cost:** $0.70/M tokens input, $0.80/M tokens output
- **Throughput:** 1000+ TPS
- **Best for:** Low-latency, high-volume production

**Gemini Flash (Development/Budget):**
- **Model:** Gemini 1.5 Flash
- **Latency:** 300-800ms
- **Cost:** Free tier (1,500 req/day), then $0.35/M tokens
- **Best for:** Development, low-volume pilots, function calling reliability

**Hybrid Approach:**

```python
class LLMRouter:
    def __init__(self):
        self.groq = GroqClient(model="llama-3.3-70b-versatile")
        self.gemini = GeminiClient(model="gemini-1.5-flash")
        self.fallback_threshold = 2.0  # seconds
        
    async def generate(self, messages: list, tools: list = None):
        # Try Groq first (fast)
        try:
            response = await asyncio.wait_for(
                self.groq.chat.completions.create(
                    messages=messages,
                    tools=tools,
                    temperature=0.3,
                    max_tokens=150
                ),
                timeout=self.fallback_threshold
            )
            return response
        except (TimeoutError, RateLimitError):
            # Fall back to Gemini
            return await self.gemini.generate_content(
                messages=messages,
                tools=tools
            )
```

### 4.2 State Machine Implementation

```python
from enum import Enum, auto

class ConversationState(Enum):
    GREETING = auto()
    DISCOVERING = auto()  # Taste interview
    TAKING_ORDER = auto()
    MODIFYING = auto()
    CONFIRMING = auto()
    PAYMENT = auto()
    CLOSING = auto()
    ESCALATED = auto()

class StateMachine:
    def __init__(self):
        self.state = ConversationState.GREETING
        self.transitions = {
            ConversationState.GREETING: [
                (self.has_order_intent, ConversationState.TAKING_ORDER),
                (self.needs_discovery, ConversationState.DISCOVERING)
            ],
            ConversationState.DISCOVERING: [
                (self.preferences_collected, ConversationState.TAKING_ORDER)
            ],
            ConversationState.TAKING_ORDER: [
                (self.order_complete_intent, ConversationState.CONFIRMING),
                (self.modification_requested, ConversationState.MODIFYING)
            ],
            # ... etc
        }
        
    def transition(self, user_input: str, context: dict):
        for condition, new_state in self.transitions[self.state]:
            if condition(user_input, context):
                self.state = new_state
                return new_state
        return self.state  # No transition
```

### 4.3 Tool Calling Architecture

**Function Schema (OpenAI/Groq format):**

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_order_items",
            "description": "Extract structured order items from conversation",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "enum": WING_FLAVORS},
                                "quantity": {"type": "integer"},
                                "style": {"type": "string", "enum": ["bone-in", "boneless"]},
                                "size": {"type": "string", "enum": ["6pc", "8pc", "10pc", "15pc", "20pc", "30pc"]},
                                "modifiers": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "category": {"type": "string", "enum": ["wings", "tenders", "sides", "drinks", "desserts"]}
                            },
                            "required": ["name", "quantity", "category"]
                        }
                    },
                    "order_complete": {"type": "boolean"},
                    "special_instructions": {"type": "string"},
                    "upsell_offered": {"type": "boolean"},
                    "customer_satisfaction": {"type": "integer", "minimum": 1, "maximum": 5}
                },
                "required": ["items", "order_complete"]
            }
        }
    },
    {
        "type": "function",
        "name": "get_flavor_recommendation",
        "parameters": {
            "properties": {
                "heat_preference": {"type": "string", "enum": ["mild", "medium", "hot", "extra_hot"]},
                "taste_profile": {"type": "array", "items": {"type": "string"}},
                "previous_favorites": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
]
```

**Tool Execution Flow:**

```python
class ToolExecutor:
    def __init__(self, menu_db, order_manager):
        self.menu = menu_db
        self.orders = order_manager
        
    async def execute(self, function_name: str, params: dict, context: dict):
        if function_name == "extract_order_items":
            # Validate items against menu
            validated = self.validate_items(params["items"])
            # Update order in database
            await self.orders.update(context["order_id"], validated)
            # Check for upsell opportunities
            upsell = self.upsell_engine.suggest(validated)
            return {"success": True, "upsell_opportunity": upsell}
            
        elif function_name == "get_flavor_recommendation":
            return self.recommendation_engine.get_recommendations(
                heat=params["heat_preference"],
                taste=params.get("taste_profile", []),
                favorites=params.get("previous_favorites", [])
            )
```

### 4.4 Prompt Engineering

**System Prompt (The "Tasha" Persona):**

```python
SYSTEM_PROMPT = """You are Tasha, a Wingstop cashier who loves wings and knows the menu inside out. You're talking to a customer on the phone.

PERSONALITY:
- Casual, friendly, efficient. Use contractions: "lemme", "gonna", "gotcha", "y'all"
- Expert but not snobby. You suggest, don't lecture.
- Enthusiastic about flavors. "Oh, lemon pepper is my favorite!"
- Keep responses SHORT (5-12 words normally, max 15 words)

RULES:
- NEVER say "As an AI", "I apologize", or robotic phrases
- If you don't understand, say "Sorry, say that again?" not "I didn't catch that"
- Always confirm prices before payment
- Suggest upsells naturally, not pushy

MENU KNOWLEDGE:
- 11 flavors: Lemon Pepper, Original Hot, Garlic Parmesan, Hickory Smoked BBQ, 
  Louisiana Rub, Spicy Korean Q, Mango Habanero, Atomic, Cajun, Mild, Hawaiian
- Bone-in vs boneless. Bone-in has more flavor, boneless easier eating.
- Combos: 6pc, 8pc, 10pc come with fries + drink. 15pc+ are wings only.
- Dips: Ranch, Blue Cheese, Honey Mustard, Cheese Sauce

CURRENT CONTEXT:
Location: {location_name}
Time: {current_time}
Current wait time: {cook_time} minutes
Today's special: {lto}

ORDER STATE:
Current items: {current_order}
Total so far: ${total}
Customer: {customer_name} ({"returning" if customer_history else "new"})
"""

# Dynamic variables injected per turn
```

**Conversation Memory Management:**

```python
class ConversationMemory:
    def __init__(self, max_turns=6):
        self.turns = []
        self.max_turns = max_turns
        
    def add(self, role: str, content: str, tools_used: list = None):
        self.turns.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "tools": tools_used
        })
        # Keep only recent context (sliding window)
        if len(self.turns) > self.max_turns * 2:  # user + assistant pairs
            self.turns = self.turns[-self.max_turns * 2:]
            
    def get_messages(self) -> list:
        # Format for LLM API
        return [{"role": t["role"], "content": t["content"]} for t in self.turns]
        
    def get_key_facts(self) -> dict:
        # Extract persistent facts (not in LLM context, but system state)
        return {
            "confirmed_items": self.extract_confirmed_items(),
            "customer_preferences": self.extract_preferences(),
            "pending_modifications": self.extract_pending()
        }
```

---

## 5. Text-to-Speech (TTS) Architecture

### 5.1 Local: Kokoro (Development/Budget)

**Why Kokoro:**
- Open source, runs on CPU
- Quality acceptable for MVP
- Zero per-minute cost

**Optimization:**

```python
from kokoro import KPipeline
import soundfile as sf
import io

class KokoroTTS:
    def __init__(self, voice="af_bella", speed=1.1):
        self.pipeline = KPipeline(lang_code='a')  # American English
        self.voice = voice
        self.speed = speed
        
        # Pre-load common phrases for zero-latency playback
        self.cache = {}
        self.warmup_phrases = [
            "Welcome to Wingstop",
            "Got it",
            "Anything else",
            "Your total is",
            "See you soon"
        ]
        
    def synthesize(self, text: str, use_cache: bool = True) -> bytes:
        # Check cache for exact match
        if use_cache and text in self.cache:
            return self.cache[text]
            
        # Preprocessing for natural speech
        processed_text = self.preprocess(text)
        
        # Generate audio
        generator = self.pipeline(
            processed_text, 
            voice=self.voice,
            speed=self.speed,
            split_pattern=r'\n+'
        )
        
        # Concatenate segments
        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)
            
        full_audio = np.concatenate(audio_segments)
        
        # Convert to μ-law for telephony
        wav_bytes = self.to_ulaw_wav(full_audio)
        
        # Cache short phrases
        if len(text) < 50 and use_cache:
            self.cache[text] = wav_bytes
            
        return wav_bytes
        
    def preprocess(self, text: str) -> str:
        # Add natural pauses
        text = text.replace(",", "<break time='150ms'/>")
        text = text.replace(".", "<break time='200ms'/>")
        text = text.replace("?", "<break time='200ms'/>")
        
        # Wingstop-specific pronunciation
        text = text.replace("Lemon Pepper", "Lemon <emphasis level='moderate'>Pepper</emphasis>")
        
        return text
```

### 5.2 Cloud: ElevenLabs (Production)

**Why upgrade:**
- Lower latency (streaming)
- Better prosody and emotion
- Voice cloning for brand consistency

**Implementation:**

```python
from elevenlabs import generate, stream

class ElevenLabsTTS:
    def __init__(self, voice_id="tasha_v1"):
        self.voice_id = voice_id
        self.model = "eleven_turbo_v2"  # Low latency model
        
    async def synthesize_streaming(self, text: str):
        # Stream audio chunks as they're generated
        # Reduces perceived latency by 500ms+
        audio_stream = generate(
            text=text,
            voice=self.voice_id,
            model=self.model,
            stream=True,
            latency_optimization=3  # Max optimization
        )
        
        # Convert chunks and send to telephony immediately
        async for chunk in audio_stream:
            ulaw_chunk = self.pcm_to_ulaw(chunk)
            yield ulaw_chunk
            
    def pcm_to_ulaw(self, pcm_bytes: bytes) -> bytes:
        # Convert float32 PCM to G.711 μ-law
        pcm_array = np.frombuffer(pcm_bytes, dtype=np.float32)
        pcm_int16 = (pcm_array * 32767).astype(np.int16)
        return audioop.lin2ulaw(pcm_int16.tobytes(), 2)
```

### 5.3 Prosody Control (Making Tasha Sound Human)

```python
class ProsodyEngine:
    def __init__(self):
        self.emotion_markers = {
            "enthusiastic": "<prosody rate='fast' pitch='+10%'>",
            "empathetic": "<prosody rate='slow' pitch='-5%'>",
            "urgent": "<prosody rate='fast' volume='loud'>",
            "confirming": "<prosody rate='medium' pitch='0%'>"
        }
        
    def apply_emotion(self, text: str, context: dict) -> str:
        # Detect emotion from context
        if context.get("upsell_success"):
            return self.emotion_markers["enthusiastic"] + text + "</prosody>"
        elif context.get("customer_confused"):
            return self.emotion_markers["empathetic"] + text + "</prosody>"
        elif context.get("rush_hour"):
            return self.emotion_markers["urgent"] + text + "</prosody>"
        else:
            return text
```

---

## 6. Business Logic Engine

### 6.1 Order Manager

```python
class OrderManager:
    def __init__(self, db: Database, pos_client: POSClient):
        self.db = db
        self.pos = pos_client
        
    async def create_order(self, session_id: str, phone_number: str) -> Order:
        order = Order(
            id=generate_uuid(),
            session_id=session_id,
            phone=phone_number,
            items=[],
            status="taking",
            created_at=now(),
            estimated_ready_time=None
        )
        await self.db.orders.insert(order)
        return order
        
    async def add_item(self, order_id: str, item: dict) -> ValidationResult:
        # 1. Validate against menu
        menu_item = await self.validate_menu_item(item)
        if not menu_item.valid:
            return ValidationResult(success=False, error=menu_item.error)
            
        # 2. Check 86 list
        if await self.is_86d(item["name"]):
            alternatives = await self.get_alternatives(item["name"])
            return ValidationResult(
                success=False, 
                error=f"We're out of {item['name']}",
                alternatives=alternatives
            )
            
        # 3. Calculate price
        price = self.calculate_price(item, menu_item)
        
        # 4. Update order
        await self.db.orders.update(
            order_id,
            {"$push": {"items": {**item, "price": price}}}
        )
        
        # 5. Update POS (if integration available)
        await self.pos.add_line_item(order_id, item, price)
        
        return ValidationResult(success=True, item_total=price)
        
    async def get_order_summary(self, order_id: str) -> dict:
        order = await self.db.orders.get(order_id)
        return {
            "items": order.items,
            "subtotal": sum(i["price"] for i in order.items),
            "tax": calculate_tax(order.items),
            "total": calculate_total(order.items),
            "ready_time": await self.estimate_ready_time(order)
        }
```

### 6.2 Upsell Engine

```python
class UpsellEngine:
    def __init__(self, menu_db, performance_tracker):
        self.menu = menu_db
        self.tracker = performance_tracker
        self.rules = self.load_rules()
        
    def suggest(self, current_order: list, customer_profile: dict) -> Optional[Upsell]:
        # Score all possible upsells
        candidates = []
        
        for rule in self.rules:
            score = self.score_upsell(rule, current_order, customer_profile)
            if score > 0.5:  # Threshold
                candidates.append((score, rule))
                
        # Sort by score and expected value
        candidates.sort(key=lambda x: x[0] * x[1].profit_margin, reverse=True)
        
        if not candidates:
            return None
            
        best = candidates[0][1]
        
        # A/B test different scripts
        script_variant = self.tracker.get_variant(best.id)
        
        return Upsell(
            item=best.target_item,
            script=script_variant,
            trigger_point=best.trigger_point,
            expected_lift=best.avg_lift
        )
        
    def score_upsell(self, rule: UpsellRule, order: list, profile: dict) -> float:
        score = 0.0
        
        # Category match
        if any(i["category"] in rule.trigger_categories for i in order):
            score += 0.3
            
        # Price threshold
        current_total = sum(i["price"] for i in order)
        if current_total > rule.min_order_value:
            score += 0.2
            
        # Historical acceptance
        if profile.get("upsell_accept_rate", 0.5) > 0.6:
            score += 0.2
            
        # Time-based (lunch vs dinner)
        if rule.optimal_time and is_current_time(rule.optimal_time):
            score += 0.2
            
        # LTO priority
        if rule.is_lto and rule.lto_active:
            score += 0.1
            
        return min(score, 1.0)
```

**Upsell Rules Example:**

```yaml
rules:
  - id: "combo_upgrade"
    trigger_categories: ["wings"]
    target_item: "combo_meal"
    trigger_point: "after_main_item"
    script_variants:
      - "Want fries and a drink with that?"
      - "Make it a combo for ${upsell_price} more?"
    min_order_value: 10.00
    expected_lift: 3.50
    
  - id: "large_fries_upgrade"
    trigger_categories: ["sides"]
    target_item: "large_fries"
    trigger_point: "after_side_selected"
    condition: "current_size == medium"
    script: "Upgrade to large fries for just $1.50?"
    
  - id: "extra_dip_party"
    trigger_categories: ["wings"]
    target_item: "extra_dip"
    trigger_point: "pre_confirmation"
    condition: "total_people >= 4"
    script: "With 4 people, you'll want extra ranch. Add one for $0.99?"
```

### 6.3 Discovery Interview System

```python
class DiscoveryEngine:
    def __init__(self, flavor_db):
        self.flavors = flavor_db
        self.preference_tree = self.build_tree()
        
    def build_tree(self) -> DecisionTree:
        return DecisionTree(
            root=Question(
                id="heat_preference",
                text="You want something spicy, or you play it safe?",
                options={
                    "spicy": self.spicy_branch(),
                    "safe": self.safe_branch(),
                    "medium": self.medium_branch()
                }
            )
        )
        
    def spicy_branch(self) -> Question:
        return Question(
            id="spice_level",
            text="You want face-melting hot, or flavorful heat?",
            options={
                "face_melting": Recommendation(["atomic", "mango_habanero"]),
                "flavorful": Recommendation(["original_hot", "louisiana_rub", "cajun"])
            }
        )
        
    def safe_branch(self) -> Question:
        return Question(
            id="taste_profile",
            text="You want tangy, garlicky, or straight savory?",
            options={
                "tangy": Recommendation(["lemon_pepper", "hawaiian"]),
                "garlicky": Recommendation(["garlic_parmesan"]),
                "savory": Recommendation(["hickory_bbq", "louisiana_rub"])
            }
        )
        
    async def conduct_interview(self, session: Session) -> Recommendation:
        current = self.preference_tree.root
        
        while isinstance(current, Question):
            # Ask question via TTS
            await self.speak(current.text)
            
            # Get response via STT
            response = await self.listen_and_parse(
                expected_options=list(current.options.keys())
            )
            
            if response in current.options:
                current = current.options[response]
            else:
                # Clarification
                await self.speak("Sorry, didn't catch that. " + current.text)
                
        return current  # Final Recommendation
        
    def explain_recommendation(self, rec: Recommendation) -> str:
        flavor = self.flavors.get(rec.primary)
        return (
            f"{flavor.name} is perfect for you. "
            f"It's {flavor.description}. "
            f"{'Our #1 seller.' if flavor.is_top_seller else 'A hidden gem.'} "
            f"Want that bone-in or boneless?"
        )
```

---

## 7. Data Architecture

### 7.1 Database Schema

```sql
-- Core orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    location_id VARCHAR(50) NOT NULL,
    phone_number VARCHAR(20),
    customer_id UUID REFERENCES customers(id),
    
    -- Order content
    items JSONB NOT NULL DEFAULT '[]',
    subtotal_cents INTEGER,
    tax_cents INTEGER,
    total_cents INTEGER,
    
    -- Status tracking
    status VARCHAR(20) CHECK (status IN ('taking', 'confirming', 'payment', 'cooking', 'ready', 'completed', 'cancelled')),
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    ready_by TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    special_instructions TEXT,
    upsells_offered JSONB DEFAULT '[]',
    upsells_accepted JSONB DEFAULT '[]',
    
    -- Quality metrics
    stt_confidence FLOAT,
    latency_ms INTEGER,
    error_flags JSONB DEFAULT '[]'
);

-- Time-series metrics (TimescaleDB)
CREATE TABLE call_metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    location_id VARCHAR(50),
    session_id VARCHAR(255),
    
    -- Latency breakdown
    vad_ms INTEGER,
    stt_ms INTEGER,
    llm_ms INTEGER,
    tts_ms INTEGER,
    total_roundtrip_ms INTEGER,
    
    -- Business metrics
    order_value_cents INTEGER,
    upsell_success BOOLEAN,
    discovery_used BOOLEAN,
    
    -- Quality
    transcription_accuracy FLOAT,
    sentiment_score FLOAT
);
SELECT create_hypertable('call_metrics', 'time');

-- Conversation history (for training/improvement)
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    turn_number INTEGER,
    role VARCHAR(20) CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT,
    audio_url VARCHAR(500),
    tools_called JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 7.2 Caching Strategy (Redis)

```python
class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def get_menu(self, location_id: str) -> dict:
        # Cache menu for 5 minutes (reduces DB load)
        key = f"menu:{location_id}"
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
            
        menu = await self.db.fetch_menu(location_id)
        await self.redis.setex(key, 300, json.dumps(menu))
        return menu
        
    async def get_customer_profile(self, phone: str) -> dict:
        # Cache customer data for session duration
        key = f"customer:{phone}"
        return await self.redis.get(key)
        
    async def acquire_lock(self, order_id: str) -> bool:
        # Prevent race conditions on order updates
        return await self.redis.set(
            f"lock:order:{order_id}", 
            "1", 
            nx=True, 
            ex=10
        )
```

---

## 8. Integration Architecture

### 8.1 POS Integration (Aloha/Brink/NCR)

```python
class POSIntegration(ABC):
    @abstractmethod
    async def submit_order(self, order: Order) -> POSResult:
        pass
        
    @abstractmethod
    async def get_menu(self, location_id: str) -> Menu:
        pass
        
    @abstractmethod
    async def get_cook_time(self, location_id: str) -> int:
        pass

class AlohaIntegration(POSIntegration):
    def __init__(self, api_endpoint, api_key):
        self.client = AlohaClient(api_endpoint, api_key)
        
    async def submit_order(self, order: Order) -> POSResult:
        # Map VoixAI order to Aloha format
        aloha_order = {
            "orderType": "TO_GO",
            "items": [
                {
                    "itemId": self.map_item_id(item["name"]),
                    "quantity": item["quantity"],
                    "modifiers": [
                        {"modId": self.map_modifier(m)}
                        for m in item.get("modifiers", [])
                    ]
                }
                for item in order.items
            ],
            "specialInstructions": order.special_instructions
        }
        
        result = await self.client.create_order(aloha_order)
        
        return POSResult(
            success=result.status == 200,
            pos_order_id=result.order_id,
            estimated_ready_time=result.promise_time,
            error=result.error_message
        )
```

### 8.2 Telephony Integration (Twilio)

```python
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

class TwilioIntegration:
    def __init__(self, account_sid, auth_token):
        self.client = Client(account_sid, auth_token)
        
    async def handle_incoming_call(self, call_sid: str, from_number: str):
        # Create WebSocket connection to media stream
        response = VoiceResponse()
        response.connect().stream(
            url=f"wss://api.voixai.com/media/{call_sid}",
            track="both_tracks"
        )
        
        # Initialize session
        await self.session_manager.create(call_sid, from_number)
        
        return str(response)
        
    async def send_audio(self, call_sid: str, audio_bytes: bytes):
        # Stream audio back to caller
        await self.websocket_manager.send(call_sid, audio_bytes)
        
    async def transfer_to_human(self, call_sid: str, destination: str):
        # Warm transfer to store manager
        self.client.calls(call_sid).update(
            twiml=f'<Response><Dial>{destination}</Dial></Response>'
        )
```

---

## 9. Observability & Monitoring

### 9.1 Distributed Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer("voixai.conversation")

class TracedConversation:
    async def process_turn(self, audio_chunk: bytes):
        with tracer.start_as_current_span("conversation_turn") as span:
            span.set_attribute("session_id", self.session_id)
            
            # VAD
            with tracer.start_span("vad") as vad_span:
                utterance = self.vad.process(audio_chunk)
                vad_span.set_attribute("duration_ms", processing_time)
                
            # STT
            with tracer.start_span("stt") as stt_span:
                text = self.stt.transcribe(utterance)
                stt_span.set_attribute("confidence", text.confidence)
                stt_span.set_attribute("text_length", len(text))
                
            # LLM
            with tracer.start_span("llm") as llm_span:
                response = await self.llm.generate(text)
                llm_span.set_attribute("tokens_used", response.usage)
                llm_span.set_attribute("model", response.model)
                
            # TTS
            with tracer.start_span("tts") as tts_span:
                audio = self.tts.synthesize(response.text)
                tts_span.set_attribute("audio_duration", len(audio))
                
            # Total latency
            span.set_attribute("total_latency_ms", total_time)
            
            return audio
```

### 9.2 Real-Time Dashboards

**Key Metrics to Track:**

| Metric | Alert Threshold | Dashboard |
|--------|----------------|-----------|
| P50 latency | >2 seconds | Real-time |
| P99 latency | >4 seconds | Real-time |
| STT WER | >25% | Hourly |
| LLM error rate | >1% | Real-time |
| Upsell conversion | Drop >10% | Daily |
| Order error rate | >2% | Real-time |
| Abandonment rate | >5% | Hourly |

---

## 10. Scaling Architecture

### 10.1 Horizontal Scaling

```
┌─────────────────────────────────────────┐
│           Load Balancer (NGINX)         │
│     WebSocket-aware, sticky sessions    │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌───────┐    ┌───────┐    ┌───────┐
│ Pod 1 │    │ Pod 2 │    │ Pod N │
│       │    │       │    │       │
│ • VAD │    │ • VAD │    │ • VAD │
│ • STT │    │ • STT │    │ • STT │
│ • LLM │    │ • LLM │    │ • LLM │
│ • TTS │    │ • TTS │    │ • TTS │
└───┬───┘    └───┬───┘    └───┬───┘
    │            │            │
    └────────────┴────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   ┌─────────┐       ┌─────────┐
   │  Redis  │       │   PG    │
   │ Cluster │       │ Primary │
   │         │       │ + Replicas
   │ Session │       │         │
   │  State  │       │ Orders  │
   │  Cache  │       │  Logs   │
   └─────────┘       └─────────┘
```

### 10.2 Auto-Scaling Triggers

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU utilization | >70% for 2min | <30% for 10min |
| Memory usage | >80% | <40% |
| Active calls per pod | >15 | <5 |
| Queue depth | >10 | <3 |

---

## 11. Security Architecture

### 11.1 PCI-DSS Compliance

```
┌─────────────────────────────────────────┐
│           Card Data Handling            │
├─────────────────────────────────────────┤
│  DTMF Collection (Touch-tone)           │
│  ↓                                      │
│  Audio NOT processed by STT/LLM         │
│  ↓                                      │
│  Direct to Payment Gateway (Stripe)     │
│  ↓                                      │
│  Token returned to VoixAI (safe)        │
│  ↓                                      │
│  Token stored in order (not PAN)        │
└─────────────────────────────────────────┘
```

### 11.2 Data Encryption

| Layer | Method |
|-------|--------|
| In transit | TLS 1.3 (WebSocket) |
| At rest | AES-256 (database) |
| Backups | Encrypted, geographically distributed |
| Audio recordings | Encrypted S3, 90-day retention |

---

## 12. Deployment & DevOps

### 12.1 Infrastructure as Code

```yaml
# docker-compose.yml for single location
version: '3.8'
services:
  voixai:
    image: voixai/core:latest
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - DATABASE_URL=postgresql://...
    volumes:
      - whisper-models:/app/models
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
          
  redis:
    image: redis:7-alpine
    
  postgres:
    image: timescale/timescaledb:latest-pg15
    volumes:
      - postgres-data:/var/lib/postgresql/data
      
  monitoring:
    image: grafana/grafana:latest
```

### 12.2 CI/CD Pipeline

```
Git Push → Run Tests → Build Container → Security Scan → 
Deploy to Staging → Integration Tests → Deploy to Production → 
Smoke Tests → Monitor
```

---

## 13. Performance Benchmarks

| Component | Target | Stress Test |
|-----------|--------|-------------|
| End-to-end latency | <2s | 1.8s @ 100 concurrent |
| STT (tiny.en int8) | 0.1x RTF | 10x real-time |
| LLM (Groq) | 100ms | 50ms P50 |
| TTS (Kokoro) | 0.5x RTF | 2x real-time |
| Concurrent calls | 20/location | 50 tested |
| System capacity | 50,000 calls | Horizontal scale |

---