# VoixAI v1.0 - Wingstop Conversational Voice Agent

A production-ready conversational AI agent for Wingstop phone orders. Built with a state machine architecture for natural, human-like ordering conversations.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Overview

VoixAI acts as "Tasha" - a friendly Wingstop cashier that:
- Takes phone orders through natural conversation
- Collects customer names for personalized service  
- Upsells naturally - suggests combos for 6+ wings
- Handles complete menu - wings, flavors, drinks, sides, dips
- Calculates prices in real-time
- Confirms orders before finalizing

## Quick Start

### Prerequisites
- Python 3.11+
- Groq API key (for fast LLM inference)
- Microphone access

### Installation

```bash
# Clone repository
git clone <repo-url>
cd VoixAI

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
set GROQ_API_KEY=gsk_...
```

### Run the Agent

```bash
python main_conversational.py
```

Open browser: **http://localhost:8000**

## Example Conversation

```
Tasha: "Hey! Welcome to Wingstop! I'm Tasha. What's your name?"

User: "Rishi"

Tasha: "Rishi, gotcha! How many wings can I get you?"

User: "10 boneless"

Tasha: "10 wings, gotcha! Bone-in or boneless?"

User: "Boneless"

Tasha: "Rishi, boneless, nice! Want to make that a combo?"

User: "No thanks"

Tasha: "Rishi, boneless, nice! What flavors? Lemon Pepper's popular!"

User: "Lemon pepper"

Tasha: "So that's 10 boneless wings (10 lemon pepper). Total is $12.90. Look right?"

User: "Yes"

Tasha: "Perfect! Ready in 15-20 mins, Rishi. Total $12.90. See you then!"
```

## Architecture

### State Machine Flow
```
GREETING → ASKING_NAME → ASKING_MAIN_ITEM → ASKING_COMBO → 
ASKING_FLAVOR → CONFIRMING → COMPLETED
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **STT** | Whisper tiny.en | Fast speech-to-text (~100ms) |
| **LLM** | Groq (llama-3.3-70b) | Conversational AI (~300ms) |
| **TTS** | Kokoro ONNX | Natural voice synthesis (~1s) |
| **State Machine** | Python Enum | Reliable conversation flow |
| **Database** | SQLite | Order persistence |

### Files Structure

```
VoixAI/
├── main_conversational.py      # Entry point
├── core/
│   ├── llm_agent_conversational.py  # State machine agent
│   ├── stt_engine.py          # Whisper STT
│   ├── tts_engine_onnx.py     # Kokoro TTS
│   ├── audio_stream.py        # VAD audio buffer
│   └── order_manager.py       # Order persistence
├── static/
│   └── index.html             # Web UI
├── config.yaml                # Configuration
└── requirements.txt           # Dependencies
```

## Configuration

Edit `config.yaml` to customize:

```yaml
# STT - whisper model size
stt:
  model: "tiny.en"  # tiny.en (fast) | base.en (balanced) | small.en (accurate)

# LLM - Groq settings  
llm:
  model: "llama-3.3-70b-versatile"
  temperature: 0.2  # Lower = more consistent
  max_tokens: 80    # Shorter = faster

# TTS - voice speed
tts:
  speed: 1.3        # 1.0 = normal, 1.3 = faster
```

## Features

### Conversational Intelligence
- Natural dialogue flow
- Handles interruptions gracefully
- Remembers context (name, previous items)
- Smart upselling (combos for 6+ wings)

### Voice Quality
- Fast response (~2s total latency)
- Accurate STT (tiny.en optimized)
- Natural TTS (Kokoro ONNX)
- VAD-based auto-detection

### Order Management
- Customer name collection
- Complete order tracking
- Price calculation
- Pickup time estimation
- Order confirmation

### Reliability
- Hardcoded state responses (no hallucination)
- Fuzzy matching for STT errors
- Automatic retries
- SQLite persistence

## Advanced Usage

### Environment Variables
```bash
set GROQ_API_KEY=gsk_...        # Required - LLM inference
set KMP_DUPLICATE_LIB_OK=TRUE   # Windows OpenMP fix
```

### Database
Orders stored in `orders.db`:
```python
# Query orders
sqlite3 orders.db "SELECT * FROM orders;"
```

### Testing
```bash
# Run test suite
python -m pytest tests/

# Test agent logic
python test_conversational_agent.py
```

## Performance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| STT Latency | < 500ms | ~100ms |
| LLM Latency | < 1s | ~300ms |
| TTS Latency | < 2s | ~1s |
| Total Response | < 3s | ~2s |
| Order Completion | 95%+ | Working |

## Changelog

### v1.0.0 (Current)
- Conversational state machine with 9 states
- Customer name collection
- Complete order flow (wings → flavors → combo → confirm)
- Price calculation
- Pickup time display
- Hardcoded responses for reliability
- Fuzzy matching for STT corrections

## Roadmap

### v1.1 (Planned)
- Payment integration
- SMS order confirmation
- Multi-language support

### v2.0 (Future)
- Full-duplex streaming (OpenAI Realtime API)
- Emotional voice modulation
- Advanced upselling with ML

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push: `git push origin feature-name`
5. Submit pull request

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- [Groq](https://groq.com) for fast LLM inference
- [Whisper](https://github.com/openai/whisper) for STT
- [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) for TTS
- [FastAPI](https://fastapi.tiangolo.com) for web framework

---

**Made for Wingstop**
