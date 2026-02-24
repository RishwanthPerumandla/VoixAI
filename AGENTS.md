# VoixAI - AI Coding Agent Guide

This document provides essential information for AI coding agents working on the VoixAI project.

## Project Overview

**VoixAI** is a production-ready conversational AI voice agent for Wingstop phone orders. It acts as "Tasha" - a friendly Wingstop cashier that takes orders through natural voice conversations.

### Key Capabilities
- Real-time voice ordering via WebSocket
- Speech-to-Text (STT) using Whisper (faster-whisper)
- Natural language processing via Groq API (llama-3.3-70b)
- Text-to-Speech (TTS) using Kokoro ONNX
- Voice Activity Detection (VAD) using Silero
- SQLite persistence for orders and conversations

### Architecture Versions
The project has two main implementations:

1. **v1.0 - State Machine Agent** (`main_conversational.py`)
   - Uses `ConversationalAgent` with `DialogueState` enum
   - Hardcoded state responses for reliability
   - Simpler, more predictable flow

2. **v2.0 - ReAct Agent** (`main.py`)
   - Uses `ReActAgent` with modular components:
     - `UnderstandingEngine` - Intent/entity extraction
     - `ReasoningEngine` - Planning and tool selection
     - `ResponseGenerator` - Natural response synthesis
   - Tool-based architecture with function calling
   - More flexible and extensible

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.11+ |
| Web Framework | FastAPI | 0.109.0 |
| STT | faster-whisper | 1.0.3 |
| LLM | Groq API | llama-3.3-70b-versatile |
| TTS | kokoro-onnx | >=0.2.0 |
| VAD | silero-vad | 5.1.2 |
| Database | SQLite | Built-in |
| Frontend | Vanilla HTML/JS | WebSocket |

## Project Structure

```
VoixAI/
├── main.py                      # v2.0 ReAct Agent entry point (port 8001)
├── main_conversational.py       # v1.0 State Machine entry point (port 8000)
├── config.yaml                  # Main configuration file
├── config.json                  # Voice configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── .env                         # Environment variables (not in git)
├── .env.example                 # Environment template
├── Makefile                     # Build automation
├── docker-compose.yml           # Docker deployment
│
├── core/                        # Core modules
│   ├── agent.py                 # ReActAgent (v2.0)
│   ├── llm_agent_conversational.py  # ConversationalAgent (v1.0)
│   ├── stt_engine.py            # Whisper STT wrapper
│   ├── tts_engine_onnx.py       # Kokoro TTS wrapper
│   ├── audio_stream.py          # VAD audio buffer
│   ├── interrupt_handler.py     # Barge-in detection
│   ├── order_manager.py         # Order persistence (v1.0)
│   ├── memory.py                # Memory manager (v2.0)
│   ├── tools.py                 # Business logic tools
│   ├── understanding.py         # Intent/entity extraction
│   ├── reasoning.py             # Planning engine
│   └── generation.py            # Response templates
│
├── static/
│   └── index.html               # Web UI (single page)
│
├── data/
│   ├── menu.json                # Wingstop menu data
│   ├── policies.json            # Business policies
│   └── orders.db                # SQLite database
│
└── tests/
    └── test_basic.py            # Basic test suite
```

## Configuration

### Environment Variables (`.env`)
```properties
# Required
GROQ_API_KEY=gsk_your_key_here

# Optional
LOG_LEVEL=INFO
DATABASE_PATH=data/orders.db
```

### Config (`config.yaml`)
Key sections:
- `app`: Application metadata
- `hardware`: CPU/device settings, sample rate (16kHz)
- `audio`: VAD thresholds, silence duration, noise gate
- `stt`: Model size (tiny.en/base.en/small.en), compute type (int8)
- `llm`: Model name, temperature (0.2-0.3), max_tokens
- `tts`: Voice (af_bella), speed (1.2-1.3), sample rate (24kHz)
- `memory`: Database paths
- `tools`: Enabled tool list

## Build and Run Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Set environment variable
set GROQ_API_KEY=gsk_...  # Windows
export GROQ_API_KEY=gsk_...  # Linux/Mac
```

### Run
```bash
# v1.0 State Machine (port 8000)
python main_conversational.py

# v2.0 ReAct Agent (port 8001)
python main.py

# Or use Makefile
make run
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
python test_conversational_agent.py

# Or via Makefile
make test
```

### Code Quality
```bash
# Format code
make format

# Run linters
make lint

# Clean build artifacts
make clean
```

## Code Style Guidelines

### General
- Follow **PEP 8** style guidelines
- Maximum line length: **100 characters**
- Use **type hints** for function signatures
- Write docstrings for all public functions and classes

### Imports
```python
# Standard library first
import os
import json
from typing import Dict, List, Any
from dataclasses import dataclass

# Third-party
import numpy as np
from groq import Groq

# Local modules
from core.tools import MenuManager
from core.memory import MemoryManager
```

### Naming Conventions
- `PascalCase` for classes: `ReActAgent`, `UnderstandingEngine`
- `snake_case` for functions/variables: `process_audio`, `customer_name`
- `UPPER_CASE` for constants: `FLAVORS`, `MAX_TURNS`
- `DialogueState` enum values: `GREETING`, `ASKING_FLAVOR`

### Error Handling
```python
try:
    result = self.tools[tool_name](**params)
except Exception as e:
    print(f"[Agent] Tool error: {e}")
    return {"success": False, "error": str(e)}
```

### Logging
Use print statements with prefixes for different components:
```python
print(f"[WS:{session_id}] Message")
print(f"[Agent] State: {state}")
print(f"[TTS] Synthesizing...")
print(f"[VAD] Energy: {energy:.2f}")
```

## Key Implementation Details

### State Machine Flow (v1.0)
```
GREETING → ASKING_NAME → ASKING_MAIN_ITEM → ASKING_FLAVOR → 
ASKING_COMBO → (ASKING_DRINK → ASKING_SIDES → ASKING_DIP) → 
CONFIRMING → COMPLETED
```

### ReAct Flow (v2.0)
```
1. UNDERSTAND: Extract intent, entities, sentiment
2. REASON: Decide action based on context
3. ACT: Execute tools (search_menu, calculate_price, etc.)
4. GENERATE: Create natural response
```

### Audio Processing Pipeline
1. Client sends 16kHz PCM audio via WebSocket
2. `AudioBuffer` accumulates chunks with VAD
3. VAD detects end-of-speech (silence threshold)
4. `STTEngine.transcribe()` converts to text
5. Agent processes text and generates response
6. `TTSEngineONNX.synthesize()` creates audio
7. Base64-encoded audio sent back to client

### Order Data Structure
```python
{
    "items": [
        {
            "name": "Boneless Wings",
            "qty": 10,
            "category": "wings",
            "modifiers": {
                "type": "boneless",
                "flavors": [{"flavor": "Lemon Pepper", "qty": 10}]
            }
        }
    ],
    "customer_name": "Rishi",
    "total_price": 12.90,
    "state": "confirming",
    "order_complete": False
}
```

## Testing Strategy

### Unit Tests
Located in `tests/test_basic.py`:
- `TestOrderManager`: Database operations
- `TestConversationAgent`: Agent state transitions

### Manual Testing
Use `test_conversational_agent.py` for:
- State enum validation
- Order dataclass testing
- Info extraction patterns
- State transition logic

### Integration Testing
1. Start server: `python main_conversational.py`
2. Open browser: `http://localhost:8000`
3. Test full conversation flow
4. Check latency metrics in UI

## Security Considerations

### API Keys
- Store in `.env` file (never commit)
- `.env` is in `.gitignore`
- Use environment variables in code: `os.getenv("GROQ_API_KEY")`

### Input Validation
- All user input processed through STT
- Text cleaned before LLM processing
- Forbidden phrases filtered in responses

### Database
- SQLite with parameterized queries
- Context managers for connections
- No raw SQL with user input

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| STT Latency | < 500ms | tiny.en model, greedy decoding |
| LLM Latency | < 1s | Groq API, max_tokens=80 |
| TTS Latency | < 2s | Kokoro ONNX with caching |
| Total Response | < 3s | End-to-end |
| Audio Sample Rate | 16kHz input, 24kHz output | - |

## Common Tasks

### Adding a New Flavor
1. Edit `data/menu.json` - Add flavor item
2. Edit `core/llm_agent_conversational.py` - Add to `FLAVORS` list
3. Edit `core/understanding.py` - Add to `FLAVOR_MAP`

### Adding a New Tool
1. Define function in `core/tools.py`
2. Add to `TOOL_DEFINITIONS` list
3. Register in `ReActAgent.__init__` `self.tools` dict
4. Handle in `ReasoningEngine` if needed

### Modifying Response Style
1. Edit `core/generation.py` - Update `response_templates`
2. Or modify system prompt in `core/agent.py`
3. Keep responses under 12-15 words for speed

### Database Schema Changes
1. Edit `core/memory.py` or `core/order_manager.py`
2. Update `_init_database()` or `_init_tables()`
3. SQLite will auto-migrate on next run

## Troubleshooting

### Windows OpenMP Error
Set environment variable at start of files:
```python
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
```

### High Latency
- Check STT model size (tiny.en is fastest)
- Verify TTS caching is working
- Monitor CPU usage during TTS generation

### WebSocket Disconnections
- Check network stability
- Verify WebSocket URL in `static/index.html`
- Check server logs for errors

### Audio Not Playing
- Verify browser autoplay policy
- Check audio format (WAV, 24kHz, 16-bit PCM)
- Test with `playAudio()` in browser console

## Deployment

See `DEPLOYMENT.md` for:
- Docker deployment
- systemd service setup
- nginx reverse proxy
- SSL/TLS configuration
- Database backup strategies

## License

MIT License - See `LICENSE` file
