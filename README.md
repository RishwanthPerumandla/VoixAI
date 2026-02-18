# VoixAI

Real-time AI voice ordering system simulating a human Wingstop cashier named "Tasha".

## Overview

VoixAI is a voice-enabled conversational AI system for restaurant order taking. It processes natural speech input, extracts order details using function calling, and responds with synthesized speech using a consistent persona.

### Key Features

- Real-time voice conversation via WebSocket
- Speech-to-Text using faster-whisper (tiny.en, CPU-optimized)
- Large Language Model using Groq API (llama-3.3-70b-versatile)
- Text-to-Speech using Kokoro (af_bella voice)
- SQLite persistence for orders and conversation logs
- Voice Activity Detection using Silero VAD
- Function calling for structured order extraction

## Architecture

```
Browser (16kHz PCM) 
    -> WebSocket 
    -> FastAPI 
    -> AudioBuffer (VAD) 
    -> Whisper (STT) 
    -> Groq LLM (reasoning) 
    -> Kokoro (TTS) 
    -> WebSocket 
    -> Browser Playback
```

## Project Structure

```
.
├── core/
│   ├── __init__.py
│   ├── audio_stream.py      # Audio buffer with VAD
│   ├── stt_engine.py        # Speech-to-text (Whisper)
│   ├── llm_agent.py         # Conversational AI (Groq)
│   ├── tts_engine.py        # Text-to-speech (Kokoro)
│   └── order_manager.py     # SQLite persistence
├── static/
│   └── index.html           # Web client
├── main.py                  # FastAPI application entry
├── config.yaml              # Configuration
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## Requirements

- Python 3.10+
- Intel i7 8th Gen or equivalent (CPU-only, no GPU required)
- 16GB RAM
- Microphone access for voice input

## Installation

### 1. Clone and Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install PyTorch CPU first (required for faster-whisper and kokoro)
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `.env` file:

```properties
GROQ_API_KEY=gsk_your_key_here
```

Get your free API key at: https://console.groq.com

### 3. Run

```bash
python main.py
```

Open browser: http://localhost:8000

## Usage

1. Click and hold the microphone button
2. Speak your order naturally (e.g., "I'd like 10 lemon pepper wings and a Coke")
3. Release the button
4. Tasha will confirm and ask if you need anything else
5. Say "That's all" when finished, then "Yes" to confirm

## Configuration

Edit `config.yaml` to adjust settings:

```yaml
hardware:
  device: "cpu"
  sample_rate: 16000

audio:
  vad_threshold: 0.5
  silence_duration_ms: 800
  min_utterance_ms: 500

stt:
  model: "tiny.en"
  compute_type: "int8"

llm:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
  temperature: 0.3

tts:
  voice: "af_bella"
  speed: 1.1
```

## Database Schema

SQLite database (`orders.db`) contains two tables:

### orders
- id (INTEGER PRIMARY KEY)
- session_id (TEXT)
- items_json (TEXT)
- total_items (INTEGER)
- status (TEXT)
- special_instructions (TEXT)
- created_at (TIMESTAMP)
- completed_at (TIMESTAMP)

### conversation_logs
- id (INTEGER PRIMARY KEY)
- order_id (INTEGER, FOREIGN KEY)
- role (TEXT)
- content (TEXT)
- audio_ms (INTEGER)
- timestamp (TIMESTAMP)

## Performance Metrics

Typical latency breakdown:
- STT: 0.5-1.5s
- LLM: 0.3-0.8s (Groq)
- TTS: 2-5s (Kokoro on CPU)
- Total: 3-7s

Note: TTS latency is the primary bottleneck on CPU-only systems.

## Limitations

- TTS generation is slow on CPU (consider GPU for production)
- Single-session WebSocket (no multi-user support yet)
- Limited to English language
- No phone integration (browser-only)

## License

MIT License
