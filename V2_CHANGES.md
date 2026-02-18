# VoixAI v2 - Always Listening Mode

## New Features

### 1. Always-Listening Mode (No Button Required)
- **Continuous audio streaming** - No push-to-talk button
- **VAD-based auto-detection** - Automatically detects when you stop speaking
- **Status indicators** - Shows Listening/Processing/Speaking states

### 2. Kokoro ONNX TTS (Faster)
- **ONNX Runtime** - Significantly faster than PyTorch on CPU
- **Auto-download** - Downloads model files on first run
- **Expected speedup** - TTS from 3-5s to 0.5-1s

## Files Changed

### New Files
- `core/tts_engine_onnx.py` - ONNX-based TTS engine
- `main_v2.py` - Always-listening WebSocket server
- `static/index_v2.html` - Updated frontend (no button)
- `V2_CHANGES.md` - This document

### Modified Files
- `main.py` - Falls back to ONNX TTS if available
- `requirements.txt` - Added kokoro-onnx, onnxruntime

## Usage

### Option 1: Use v2 (Always Listening)
```bash
python main_v2.py
# Open http://localhost:8000
# Just speak naturally - no button needed
```

### Option 2: Use Original (Push-to-Talk)
```bash
python main.py
# Uses ONNX TTS if available (faster)
```

## How It Works

### Always-Listening Flow
1. Browser continuously sends audio chunks
2. VAD detects speech start/end automatically
3. When silence detected (800ms), processes utterance
4. No user interaction required

### Latency Improvements
| Component | v1 (PyTorch) | v2 (ONNX) |
|-----------|--------------|-----------|
| STT | ~0.7s | ~0.7s |
| LLM | ~0.5s | ~0.5s |
| TTS | ~3-5s | ~0.5-1s |
| **Total** | **~4-6s** | **~2-3s** |

## Requirements

Additional dependencies:
```bash
pip install kokoro-onnx onnxruntime
```

Model files (auto-downloaded):
- `kokoro-v1.0.onnx` (~100MB)
- `voices-v1.0.bin` (~5MB)

## Known Issues

1. **First-run download** - Initial model download takes time
2. **Background noise** - VAD may trigger on loud noises
3. **Overlap** - Speaking while Tasha is speaking may interrupt

## Future Improvements

- Streaming TTS (play chunks as they generate)
- Wake word detection ("Hey Tasha")
- Better noise filtering
- Interruption handling
