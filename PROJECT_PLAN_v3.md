# VoixAI v3.0 - Implementation Project Plan

**Document Version:** 1.1 (Revised for Local-First Development)  
**Date:** 2025-02-24  
**Status:** Planning Phase  
**Objective:** Build v3.0 locally on i7 8th Gen + 16GB RAM, then migrate to cloud

---

## Executive Summary

### Current State (v2.0)
- **Architecture:** Monolithic FastAPI with ReAct agent
- **STT:** faster-whisper (local) 
- **LLM:** Groq API
- **TTS:** Kokoro ONNX (local)
- **Database:** SQLite
- **Deployment:** Local/Docker only
- **Latency:** 1.5-2s

### Target State (v3.0)
- **Architecture:** Pipecat pipeline (local → cloud)
- **STT:** Deepgram Nova 2 (cloud API - no local resources needed)
- **LLM:** Groq (cloud API - no local GPU needed)
- **TTS:** Cartesia (cloud API - no local synthesis needed)
- **Database:** SQLite locally → PostgreSQL in cloud
- **Vector DB:** Qdrant (local Docker)
- **Cache:** Redis (local Docker)
- **Deployment:** Docker Compose locally → Kubernetes cloud
- **Latency:** <500ms P50

### Hardware Constraints (Local Development)
| Resource | Available | Implication |
|----------|-----------|-------------|
| CPU | i7 8th Gen | Good for Pipecat, no local LLM |
| RAM | 16GB | Can't run vLLM or large models locally |
| GPU | None | Must use cloud APIs for AI |
| Storage | ~100GB free | Sufficient for local dev |

**Strategy:** Use **cloud APIs** for compute-heavy tasks (STT, LLM, TTS), **local Docker** for data services (Redis, Qdrant), and **SQLite** for persistence locally (migrate to PostgreSQL in cloud).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT (Phase 1-2)                         │
│                         Your Laptop (16GB RAM)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Docker Compose Stack                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │    Redis     │  │    Qdrant    │  │   VoixAI App         │  │    │
│  │  │   (Cache)    │  │  (Vector DB) │  │   (Pipecat Pipeline) │  │    │
│  │  │   ~100MB     │  │   ~500MB     │  │   ~2GB               │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Cloud APIs (External)                       │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │   Deepgram   │  │     Groq     │  │     Cartesia         │  │    │
│  │  │    (STT)     │  │    (LLM)     │  │      (TTS)           │  │    │
│  │  │  ~$0.043/min │  │ ~$0.50/M tok │  │   ~$0.03/min         │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Storage: SQLite (local file) ~10MB per 1000 conversations              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  Phase 3: Cloud Migration
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CLOUD DEPLOYMENT (Phase 3-4)                        │
│                         Kubernetes on AWS/GCP                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     Kubernetes Cluster                           │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │  PostgreSQL  │  │ Redis Cluster│  │   VoixAI Pods        │  │    │
│  │  │  (Primary+   │  │              │  │   (Auto-scaled)      │  │    │
│  │  │   Replicas)  │  │              │  │                      │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  │  ┌──────────────┐  ┌──────────────┐                            │    │
│  │  │    Qdrant    │  │   vLLM       │                            │    │
│  │  │   Cluster    │  │  (GPU nodes) │                            │    │
│  │  │              │  │              │                            │    │
│  │  └──────────────┘  └──────────────┘                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Observability: Prometheus + Grafana + Jaeger                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Local Foundation (Weeks 1-2)

### Goal
Get the core Pipecat pipeline working **locally on your laptop** with cloud APIs for AI services. No GPU required.

### 1.1 Project Setup & Dependencies

**Tasks:**
- [ ] Create new branch `v3-dev` from current `dev`
- [ ] Set up project structure for Pipecat-based architecture
- [ ] Add Pipecat framework dependency
- [ ] Add Daily.co Python SDK
- [ ] Add Deepgram Python SDK
- [ ] Add Cartesia Python SDK
- [ ] Add Redis client (redis-py)
- [ ] Add Qdrant client (qdrant-client)
- [ ] Update `requirements.txt` with new dependencies
- [ ] Create `.env.example` with new environment variables
- [ ] Create `docker-compose.yml` for local services (Redis, Qdrant)

**New Dependencies:**
```txt
# Core framework
pipecat-ai[daily,deepgram,cartesia]>=0.0.40
daily-python>=0.9.0

# Cloud APIs
deepgram-sdk>=3.0.0
cartesia>=1.0.0
groq>=0.4.0

# Local data services (lightweight, run in Docker)
redis>=5.0.0
qdrant-client>=1.7.0

# Local persistence
aiosqlite>=0.19.0  # Async SQLite

# Observability (lightweight for local)
prometheus-client>=0.19.0
```

**Files to Create:**
```
├── src/
│   ├── pipeline/          # Pipecat pipeline modules
│   ├── transports/        # Daily.co transport
│   ├── processors/        # Custom frame processors
│   ├── tools/             # Business logic tools
│   ├── memory/            # Memory management
│   ├── vector_db/         # Qdrant client
│   └── db/                # SQLite repositories
├── docker-compose.yml     # Local services
├── .env.example           # Environment template
└── scripts/
    ├── index_menu.py      # Menu indexing script
    └── setup_local.sh     # Local setup script
```

**Docker Compose (Local Services):**
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
      
volumes:
  redis_data:
  qdrant_data:
```

**Why these choices for 16GB RAM:**
- Redis: 256MB limit (plenty for local dev)
- Qdrant: ~500MB for menu vectors (small dataset)
- App: ~2GB for Pipecat pipeline
- Total: ~3GB leaving 13GB for OS and browser

### 1.2 Daily.co WebRTC Transport

**Tasks:**
- [ ] Create `DailyTransport` wrapper class
- [ ] Implement WebRTC connection lifecycle
- [ ] Handle audio frame callbacks
- [ ] Test with Daily.co sandbox room

**Key Components:**
```python
# src/transports/daily_transport.py
class DailyTransport:
    def __init__(self, room_url: str, token: str):
        self.room_url = room_url
        self.token = token
        self.daily = Daily()
        
    async def connect(self):
        # Join Daily.co room
        pass
        
    async def disconnect(self):
        # Leave room
        pass
        
    def on_audio_frame(self, frame):
        # Receive audio from user
        pass
        
    async def send_audio(self, audio_bytes):
        # Send TTS audio to user
        pass
```

**Acceptance Criteria:**
- Can join Daily.co room from browser
- Audio flows bidirectionally
- No GPU required (WebRTC handled by Daily.co SDK)

### 1.3 Pipecat Pipeline Setup

**Tasks:**
- [ ] Create `ConversationPipeline` class
- [ ] Set up frame processors:
  - `VADProcessor` (Silero VAD)
  - `DeepgramSTTProcessor` 
  - `ReActProcessor` (our agent)
  - `CartesiaTTSProcessor`
- [ ] Connect processors in pipeline
- [ ] Handle frame flow

**Pipeline Architecture:**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Daily.co   │───▶│   VAD        │───▶│  Deepgram    │
│  Transport   │    │  Processor   │    │     STT      │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Daily.co   │◀───│  Cartesia    │◀───│  ReAct       │
│  Transport   │    │     TTS      │    │  Processor   │
└──────────────┘    └──────────────┘    └──────────────┘
```

**Files:**
- `src/pipeline/conversation_pipeline.py`
- `src/processors/vad_processor.py`
- `src/processors/deepgram_stt.py`
- `src/processors/cartesia_tts.py`
- `src/processors/react_processor.py`

### 1.4 Deepgram STT Integration

**Tasks:**
- [ ] Create `DeepgramSTTProcessor` for Pipecat
- [ ] Configure Nova 2 model (streaming)
- [ ] Handle interim and final transcripts
- [ ] Add confidence thresholding

**Configuration:**
```python
DEEPGRAM_CONFIG = {
    "model": "nova-2",
    "language": "en-US",
    "smart_format": True,
    "interim_results": True,
    "endpointing": 300,  # 300ms of silence = end of utterance
    "filler_words": False,
    "profanity_filter": False,
}
```

**Acceptance Criteria:**
- STT latency <300ms (measured)
- Real-time streaming works
- Accurate on restaurant terminology

### 1.5 Cartesia TTS Integration

**Tasks:**
- [ ] Create `CartesiaTTSProcessor` for Pipecat
- [ ] Set up Cartesia client
- [ ] Select base voice (we'll clone "Tasha" later)
- [ ] Configure streaming TTS

**Configuration:**
```python
CARTESIA_CONFIG = {
    "model": "sonic",
    "voice_id": "base-voice-id",  # Replace with Tasha later
    "speed": 1.2,
    "sample_rate": 24000,
    "streaming": True,
}
```

**Acceptance Criteria:**
- TTS starts streaming on first chunk
- Latency <200ms
- Audio plays correctly in browser

### 1.6 Basic ReAct Agent (2 Tools)

**Tasks:**
- [ ] Port existing ReAct agent to Pipecat
- [ ] Integrate with Groq LLM (Llama 3.3 70B)
- [ ] Implement 2 tools:
  - `search_menu`: Simple keyword search
  - `create_order`: Basic order creation in SQLite
- [ ] Handle conversation flow

**Tool Interface:**
```python
class BaseTool:
    name: str
    description: str
    parameters: dict
    
    async def execute(self, **params) -> ToolResult:
        pass
```

**Files:**
- `src/tools/base.py`
- `src/tools/menu_search.py` (keyword search only for now)
- `src/tools/order_creation.py` (SQLite)
- `src/tools/registry.py`
- `src/agent/react_agent.py`

### 1.7 Local Data Layer

**Tasks:**
- [ ] Set up SQLite with async support (aiosqlite)
- [ ] Create schema for local development:
  - `conversations` table
  - `messages` table
  - `orders` table
  - `customers` table (minimal)
- [ ] Create repository classes
- [ ] Add connection pooling (SQLite handles this)

**SQLite Schema (Simplified):**
```sql
-- Local development schema (will migrate to PostgreSQL in cloud)
CREATE TABLE customers (
    id TEXT PRIMARY KEY,
    phone_number TEXT UNIQUE,
    name TEXT,
    preferences TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    customer_id TEXT,
    session_id TEXT UNIQUE,
    channel TEXT DEFAULT 'web',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT DEFAULT 'active',
    metadata TEXT  -- JSON
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    latency_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    customer_id TEXT,
    items TEXT,  -- JSON
    total_amount REAL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.8 Redis Session Storage

**Tasks:**
- [ ] Create `RedisMemory` class
- [ ] Implement session state storage
- [ ] Cache conversation history
- [ ] Set TTL (1 hour)

**Redis Data Structure:**
```python
# Session state (Hash)
HSET session:{session_id}
    customer_id "uuid"
    current_order "json"
    conversation_history "json"
    state "ordering"
    last_activity_timestamp "1699123456"
    TTL 3600

# Rate limiting (for local testing)
SET rate_limit:{customer_id}:calls "10" EX 60 NX
```

### 1.9 Local Testing & Validation

**Tasks:**
- [ ] Create `test_local_pipeline.py`
- [ ] Test end-to-end conversation
- [ ] Measure latency breakdown
- [ ] Verify no memory leaks

**Test Script:**
```python
# scripts/test_local.py
async def test_conversation():
    # Start docker-compose
    # Connect to Daily.co room
    # Run test conversation
    # Report metrics
```

**Acceptance Criteria for Phase 1:**
| Metric | Target |
|--------|--------|
| End-to-end conversation | Working locally |
| Latency | <1000ms |
| Memory usage | <3GB total |
| Tools working | 2 (search_menu, create_order) |
| No GPU required | ✓ |

---

## Phase 2: Local Intelligence (Weeks 3-4)

### Goal
Add full business logic locally: all 8 tools, vector search with Qdrant, interruption handling, and upsell engine.

### 2.1 Complete Tool Registry (8 Tools)

**Tools to Implement:**
| Tool | Local Implementation | Cloud Migration |
|------|---------------------|-----------------|
| `search_menu` | Qdrant vector search | Same |
| `calculate_price` | Local calculation | Same |
| `create_order` | SQLite | PostgreSQL |
| `modify_order` | SQLite | PostgreSQL |
| `validate_order` | Local validation | Same |
| `suggest_upsell` | Rule-based | Same (+ML later) |
| `check_policy` | Local JSON lookup | Same |
| `create_ticket` | SQLite (local tickets) | PostgreSQL |

**Files:**
- `src/tools/` (all 8 tools)
- `src/tools/registry.py`

### 2.2 Vector Search with Local Qdrant

**Tasks:**
- [ ] Generate embeddings for menu items
- [ ] Create Qdrant collection
- [ ] Implement semantic search
- [ ] Add hybrid search (vector + keyword)

**Qdrant Setup (Local Docker):**
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Create collection
cclient.create_collection(
    collection_name="menu_items",
    vectors_config={"size": 384, "distance": "Cosine"}
)
```

**Memory Impact:**
- Menu items: ~100 items
- Embedding size: 384 dims × 4 bytes = 1.5KB per item
- Total: ~150KB + overhead = ~10MB

### 2.3 Interruption Handling

**Tasks:**
- [ ] Create `InterruptionProcessor`
- [ ] Energy-based barge-in detection
- [ ] Graceful fade-out
- [ ] Context preservation

**Local Implementation:**
```python
class InterruptionProcessor(FrameProcessor):
    def __init__(self):
        self.energy_threshold = 0.6
        self.fade_duration_ms = 100
        
    async def process_frame(self, frame):
        # Detect energy spike
        # Trigger fade-out
        # Preserve context
        pass
```

### 2.4 Three-Tier Memory System (Local)

**Implementation:**
```python
class MemoryManager:
    def __init__(self):
        # Working: In-memory (Python list)
        self.working_memory = WorkingMemory(capacity=5)
        
        # Short-term: Redis (local Docker)
        self.short_term_memory = RedisMemory(
            host="localhost", port=6379
        )
        
        # Episodic: SQLite (local file)
        self.episodic_memory = SQLiteMemory(
            db_path="data/voixai.db"
        )
```

### 2.5 Enhanced Understanding Engine

**Tasks:**
- [ ] Intent classification (8+ intents)
- [ ] NER extraction
- [ ] Sentiment analysis
- [ ] Urgency detection
- [ ] Ambiguity scoring

### 2.6 Upsell Engine

**Tasks:**
- [ ] Rule-based suggestions
- [ ] Track acceptance rates in SQLite
- [ ] Max 2 suggestions per order

### 2.7 Local Load Testing

**Tasks:**
- [ ] Test with 5 concurrent conversations
- [ ] Monitor memory usage
- [ ] Check for bottlenecks

**Acceptance Criteria for Phase 2:**
| Metric | Target |
|--------|--------|
| Task completion rate | >80% |
| Tools working | 8 |
| Memory usage | <4GB |
| Concurrent conversations | 5 (local limit) |
| Interruption detection | >90% |

---

## Phase 3: Cloud Migration (Weeks 5-6)

### Goal
Migrate from local laptop to Kubernetes cloud infrastructure. Add observability and scaling.

### 3.1 Infrastructure Migration Plan

| Component | Local | Cloud | Migration Strategy |
|-----------|-------|-------|-------------------|
| SQLite | Local file | PostgreSQL RDS | Export/import + dual-write |
| Redis | Docker | ElastiCache | Same API, config change |
| Qdrant | Docker | Qdrant Cloud | Snapshot restore |
| App | Local run | Kubernetes | Containerize |
| STT | Deepgram | Deepgram | Same, just scale |
| LLM | Groq | Groq + vLLM | Add fallback |
| TTS | Cartesia | Cartesia + ElevenLabs | Add fallback |

### 3.2 PostgreSQL Migration

**Tasks:**
- [ ] Set up RDS PostgreSQL
- [ ] Run migration scripts
- [ ] Export SQLite data
- [ ] Import to PostgreSQL
- [ ] Update repositories to use PostgreSQL
- [ ] Add connection pooling (PgBouncer)

### 3.3 Kubernetes Deployment

**Tasks:**
- [ ] Create Docker image for app
- [ ] Write K8s manifests
- [ ] Deploy to EKS/GKE
- [ ] Configure environment variables

### 3.4 Observability Stack

**Tasks:**
- [ ] Deploy Prometheus + Grafana
- [ ] Add Jaeger for tracing
- [ ] Create dashboards
- [ ] Set up alerts

### 3.5 Auto-scaling

**Tasks:**
- [ ] Configure HPA
- [ ] Set up cluster auto-scaler
- [ ] Test scaling behavior

---

## Phase 4: Cloud Optimization (Weeks 7-8)

### Goal
Optimize for cost ($0.01/min) and add advanced features.

### 4.1 vLLM Deployment (GPU)

**Tasks:**
- [ ] Deploy vLLM on GPU nodes
- [ ] Configure Llama 3.2 3B
- [ ] Add routing logic

### 4.2 Multi-Layer Caching

**Tasks:**
- [ ] TTS phrase cache (Redis)
- [ ] Menu embeddings cache
- [ ] LLM response cache (semantic)

### 4.3 Cost Optimization

**Tasks:**
- [ ] Dynamic service routing
- [ ] Track costs per conversation
- [ ] Optimize for $0.01/min target

---

## Local Development Environment

### Prerequisites
- Python 3.11+
- Docker Desktop
- 16GB RAM available

### Quick Start (Local)
```bash
# 1. Clone and setup
git clone <repo>
cd voixai
git checkout v3-dev

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 5. Start local services
docker-compose up -d redis qdrant

# 6. Index menu
python scripts/index_menu.py

# 7. Run app
python src/main.py
```

### Local Resource Usage
| Service | Memory | CPU | Notes |
|---------|--------|-----|-------|
| Redis | 256MB | 0.1 core | Limited via config |
| Qdrant | 512MB | 0.2 core | Small vector dataset |
| App | 2GB | 1 core | Pipecat pipeline |
| **Total** | **~3GB** | **1.3 cores** | Leaves 13GB free |

---

## Cost Analysis

### Local Development Costs (Monthly)
| Service | Usage | Cost |
|---------|-------|------|
| Deepgram STT | 1000 min testing | $43 |
| Groq LLM | 500K tokens | $7.50 |
| Cartesia TTS | 1000 min | $30 |
| Daily.co | 1000 min | $15 |
| **Total** | | **~$96/month** |

### Production Costs (Phase 3-4)
See original plan for production cost breakdown.

---

## Revised Timeline

```
Phase 1: Local Foundation (Weeks 1-2)
├── Day 1-3:   Setup, Docker, Pipecat install
├── Day 4-7:   Daily.co + Deepgram + Cartesia integration
├── Day 8-10:  Basic ReAct agent (2 tools)
├── Day 11-14: Testing, refinement
└── Milestone: Working local pipeline

Phase 2: Local Intelligence (Weeks 3-4)
├── Day 15-18: All 8 tools, Qdrant vectors
├── Day 19-21: Interruptions, memory system
├── Day 22-25: Upsell, sentiment, enhancements
├── Day 26-28: Load testing, optimization
└── Milestone: Full features locally

Phase 3: Cloud Migration (Weeks 5-6)
├── Day 29-32: PostgreSQL migration, containerization
├── Day 33-36: Kubernetes deployment
├── Day 37-40: Observability, auto-scaling
├── Day 41-42: Load testing, validation
└── Milestone: Cloud deployment working

Phase 4: Cloud Optimization (Weeks 7-8)
├── Day 43-46: vLLM, caching, cost optimization
├── Day 47-50: Advanced features, A/B testing
├── Day 51-54: Documentation, training
├── Day 55-56: Final validation
└── Milestone: Production ready, $0.01/min
```

---

## Success Criteria Summary

| Phase | Key Metric | Target |
|-------|------------|--------|
| Phase 1 | Local pipeline | Working on 16GB RAM |
| Phase 1 | Latency | <1000ms |
| Phase 2 | Task completion | >80% |
| Phase 2 | Memory usage | <4GB |
| Phase 3 | Uptime | 99.9% |
| Phase 3 | Scale | 1000+ concurrent |
| Phase 4 | Cost/min | $0.01 |

---

## Next Steps

1. **Review this revised plan** - Confirm local-first approach
2. **Provision API keys:**
   - [ ] Daily.co account + room
   - [ ] Deepgram API key
   - [ ] Cartesia API key
   - [ ] Groq API key (already have)
3. **Start Phase 1.1** - Project Setup & Dependencies

Ready to begin Phase 1.1? I can start by creating the new branch and setting up the project structure for Pipecat-based v3.0.
