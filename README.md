# VoixAI

Real-time AI voice ordering system simulating a human Wingstop cashier named "Tasha".

## Overview

VoixAI is a voice-enabled conversational AI system for restaurant order taking. It processes natural speech input, extracts order details using function calling, and responds with synthesized speech using a consistent persona.

### Key Features

- **Multi-mode operation**: Push-to-talk, always-listening, or optimized multi-core
- **Real-time voice conversation** via WebSocket
- **Speech-to-Text** using faster-whisper (tiny.en, CPU-optimized)
- **Large Language Model** using Groq API (llama-3.3-70b-versatile)
- **Text-to-Speech** using Kokoro (PyTorch or ONNX for faster inference)
- **Multi-core processing** for better CPU utilization
- **SQLite persistence** for orders and conversation logs
- **Voice Activity Detection** using Silero VAD
- **Function calling** for structured order extraction

## Architecture

```
Browser (16kHz PCM) 
    -> WebSocket 
    -> FastAPI 
    -> AudioBuffer (VAD) 
    -> Whisper (STT) [Process Pool]
    -> Groq LLM (reasoning) 
    -> Kokoro (TTS) [Process Pool]
    -> WebSocket 
    -> Browser Playback
```

## Project Structure

```
.
├── core/
│   ├── __init__.py
│   ├── audio_stream.py      # Audio buffer with VAD
│   ├── audio_processor.py   # Multi-core audio processing
│   ├── stt_engine.py        # Speech-to-text (Whisper)
│   ├── llm_agent.py         # Conversational AI (Groq)
│   ├── tts_engine.py        # Text-to-speech (Kokoro PyTorch)
│   ├── tts_engine_onnx.py   # Text-to-speech (Kokoro ONNX)
│   └── order_manager.py     # SQLite persistence
├── static/
│   ├── index.html           # Original push-to-talk client
│   ├── index_v2.html        # Always-listening client
│   └── index_simple.html    # Drive-thru style client
├── main.py                  # Original single-core server
├── main_v2.py               # Always-listening server
├── main_simple.py           # Drive-thru style server
├── main_optimized.py        # Multi-core optimized server
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

#### Option A: Simple Drive-Thru (Recommended for Testing)
Hold button, speak, release:
```bash
python main_simple.py
```

#### Option B: Always Listening
No button required, VAD auto-detects:
```bash
python main_v2.py
```

#### Option C: Multi-Core Optimized (Fastest)
Uses all CPU cores for parallel processing:
```bash
python main_optimized.py
```

#### Option D: Original Single-Core
```bash
python main.py
```

Open browser: http://localhost:8000

## Usage

### Drive-Thru Mode (main_simple.py)
1. **Hold** the red microphone button
2. **Speak** your order (e.g., "I'd like 10 lemon pepper wings and a Coke")
3. **Release** the button when done
4. Tasha will confirm and ask if you need anything else
5. Say "That's all" when finished, then "Yes" to confirm

### Tips for Best Accuracy
- Speak **clearly** and at **moderate pace**
- Hold microphone **close** to your mouth (2-4 inches)
- Speak **loud enough** - check the volume meter if available
- **Minimize background noise**

## Configuration

Edit `config.yaml` to adjust settings:

```yaml
hardware:
  device: "cpu"
  sample_rate: 16000

audio:
  vad_threshold: 0.3          # Lower = more sensitive
  silence_duration_ms: 800    # Time to wait before processing
  min_utterance_ms: 500       # Minimum speech duration
  audio_gain: 5.0             # Auto-amplification for quiet mics

stt:
  model: "tiny.en"            # Options: tiny.en, base.en, small.en
  compute_type: "int8"        # int8 = faster, float32 = more accurate
  language: "en"

llm:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
  temperature: 0.3
  max_tokens: 150

tts:
  voice: "af_bella"
  speed: 1.0
```

### STT Model Selection

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| `tiny.en` | Fastest (~0.5s) | Basic | Demo, quiet environments |
| `base.en` | Fast (~1s) | Good | Production, general use |
| `small.en` | Slow (~2s) | Best | Noisy environments |

**Note**: `tiny.en` (default) prioritizes speed over accuracy. For better accuracy, change to `base.en` in `config.yaml`.

## Performance & Optimization

### Single-Core vs Multi-Core

| Version | Latency | CPU Usage | Efficiency |
|---------|---------|-----------|------------|
| Single Core | 4-6s | 100% of 1 core | Baseline |
| Multi-Core | 2-3s | 80% of 2-3 cores | +50% faster |

### Optimization Techniques

1. **Multi-Core Processing**: Uses ProcessPoolExecutor to bypass Python GIL
2. **ONNX Runtime**: 3-5x faster TTS than PyTorch
3. **Int8 Quantization**: Faster STT with minimal accuracy loss
4. **Parallel Pipeline**: STT and TTS run in separate processes

See [OPTIMIZATION.md](OPTIMIZATION.md) for detailed tuning guide.

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

## Known Limitations

### Accuracy
- **Whisper tiny.en** model prioritizes speed over accuracy
- May misinterpret numbers (e.g., "8" as "66") in noisy environments
- For better accuracy, use `base.en` or `small.en` model

### Performance
- TTS generation is slower on CPU without ONNX
- First request slower due to model loading
- Single-session WebSocket (no multi-user support yet)

### Audio
- Requires quiet environment for best accuracy
- Background noise can cause false triggers (in always-listening mode)
- Microphone quality affects recognition accuracy

## Troubleshooting

### "Didn't catch that" / Low Accuracy
1. Check microphone level - should be 30-70%
2. Reduce background noise
3. Switch to `base.en` model in config.yaml
4. Speak slower and more clearly

### High Latency
1. Use `main_optimized.py` for multi-core processing
2. Ensure ONNX models are downloaded (auto-download on first run)
3. Close other CPU-intensive applications

### WebSocket Disconnections
1. Check browser console for errors
2. Ensure stable internet connection
3. Try refreshing the page

## License

MIT License
