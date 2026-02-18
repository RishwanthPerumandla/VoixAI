"""VoixAI - FastAPI Application Entry Point"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from dotenv import load_dotenv
load_dotenv()

import io
import base64
import time
import yaml
import uuid
from pathlib import Path
from typing import Dict, Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from core.audio_stream import AudioBuffer
from core.stt_engine import STTEngine
from core.llm_agent import ConversationAgent, ConversationState
try:
    from core.tts_engine_onnx import TTSEngineONNX as TTSEngine
    print("[INIT] Using ONNX TTS engine")
except ImportError:
    from core.tts_engine import TTSEngine
    print("[INIT] Using standard TTS engine")
from core.order_manager import OrderManager


# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# Initialize FastAPI
app = FastAPI(title=CONFIG["app"]["name"])
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global engines
stt_engine: STTEngine = None
tts_engine: TTSEngine = None


def init_engines():
    """Initialize shared engines on startup"""
    global stt_engine, tts_engine
    
    stt_config = CONFIG["stt"]
    tts_config = CONFIG["tts"]
    
    print("[INIT] Loading STT engine...")
    stt_engine = STTEngine(
        model_size=stt_config["model"],
        device=CONFIG["hardware"]["device"],
        compute_type=stt_config["compute_type"],
        language=stt_config["language"]
    )
    
    print("[INIT] Loading TTS engine...")
    tts_engine = TTSEngine(
        voice=tts_config["voice"],
        speed=tts_config["speed"],
        sample_rate=tts_config["sample_rate"]
    )
    
    print("[INIT] All engines loaded successfully!")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path("static/index.html")
    if html_path.exists():
        content = html_path.read_text(encoding='utf-8')
        # Add cache-busting comment to force reload
        return content + f"<!-- v={time.time()} -->"
    return "<h1>VoixAI Server Running</h1><p>Visit /static/index.html</p>"


@app.websocket("/ws/conversation")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for voice conversation"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] ===== New Connection =====")
    
    # Initialize per-connection state
    audio_buffer = AudioBuffer(
        sample_rate=CONFIG["hardware"]["sample_rate"],
        silence_ms=CONFIG["audio"]["silence_duration_ms"],
        vad_threshold=CONFIG["audio"]["vad_threshold"],
        min_utterance_ms=CONFIG["audio"]["min_utterance_ms"]
    )
    
    order_manager = OrderManager(db_path=CONFIG["database"]["path"])
    order_id = order_manager.create_order(session_id)
    
    try:
        agent = ConversationAgent(config=CONFIG["llm"])
        print(f"[WS:{session_id}] Agent ready")
    except Exception as e:
        print(f"[WS:{session_id}] ERROR: {e}")
        await websocket.send_json({"type": "error", "text": "Server error: Check API key"})
        await websocket.close()
        return
    
    # Send greeting
    greeting = "Hey! Welcome to Wingstop. I'm Tasha. What can I getcha?"
    try:
        audio_bytes = tts_engine.synthesize(greeting)
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        await websocket.send_json({
            "type": "greeting",
            "text": greeting,
            "audio": audio_b64,
            "state": agent.get_order_summary(),
            "order": order_manager.get_order(order_id)
        })
        order_manager.log_turn(order_id, "assistant", greeting)
        print(f"[WS:{session_id}] Greeting sent")
    except Exception as e:
        print(f"[WS:{session_id}] TTS Error: {e}")
    
    # Message loop
    audio_chunks = []  # Store all audio chunks
    start_time = None
    
    try:
        while True:
            raw_message = await websocket.receive()
            
            # Unwrap FastAPI's internal format
            if isinstance(raw_message, dict):
                if raw_message.get("type") == "websocket.receive":
                    if "bytes" in raw_message:
                        message = raw_message["bytes"]
                    elif "text" in raw_message:
                        import json
                        try:
                            message = json.loads(raw_message["text"])
                        except:
                            message = raw_message["text"]
                    else:
                        continue
                else:
                    # Skip internal messages
                    continue
            else:
                message = raw_message
            
            # Handle JSON commands
            if isinstance(message, dict):
                # Skip ping messages
                if message.get("ping"):
                    continue
                
                cmd = message.get("command")
                if cmd:
                    print(f"[WS:{session_id}] Command: {cmd}")
                else:
                    print(f"[WS:{session_id}] JSON (no cmd): {str(message)[:50]}...")
                
                if cmd == "reset":
                    agent.reset()
                    audio_chunks = []
                    order_id = order_manager.create_order(session_id)
                    await websocket.send_json({
                        "type": "reset",
                        "state": agent.get_order_summary()
                    })
                
                elif cmd == "process_audio":
                    # Process all collected audio
                    if not audio_chunks:
                        print(f"[WS:{session_id}] No audio to process")
                        await websocket.send_json({
                            "type": "error",
                            "text": "No audio recorded. Hold button longer?"
                        })
                        continue
                    
                    print(f"[WS:{session_id}] Processing {len(audio_chunks)} chunks...")
                    
                    try:
                        # Combine all chunks
                        full_audio = np.concatenate(audio_chunks)
                        audio_chunks = []  # Clear after processing
                        
                        print(f"[WS:{session_id}] Audio: {len(full_audio)/16000:.2f}s")
                        
                        # STT
                        t1 = time.time()
                        user_text = stt_engine.transcribe(full_audio)
                        stt_time = time.time() - t1
                        
                        if not user_text:
                            print(f"[WS:{session_id}] No speech detected")
                            await websocket.send_json({
                                "type": "error",
                                "text": "Didn't catch that. Try again?"
                            })
                            continue
                        
                        print(f"[WS:{session_id}] User: '{user_text}' (STT: {stt_time:.2f}s)")
                        order_manager.log_turn(order_id, "user", user_text)
                        
                        # LLM
                        t2 = time.time()
                        response_text, order_data = agent.process(user_text)
                        llm_time = time.time() - t2
                        
                        print(f"[WS:{session_id}] Tasha: '{response_text}' (LLM: {llm_time:.2f}s)")
                        
                        # Update order
                        if order_data and order_data.get("items"):
                            order_manager.update_order_items(order_id, agent.order_items)
                        
                        if agent.state == ConversationState.CLOSING:
                            order_manager.complete_order(order_id)
                        
                        # TTS
                        t3 = time.time()
                        response_audio = tts_engine.synthesize(response_text)
                        tts_time = time.time() - t3
                        
                        audio_b64 = base64.b64encode(response_audio).decode('utf-8')
                        
                        total_time = stt_time + llm_time + tts_time
                        
                        await websocket.send_json({
                            "type": "response",
                            "text": response_text,
                            "audio": audio_b64,
                            "state": agent.get_order_summary(),
                            "order": order_manager.get_order(order_id),
                            "latency": {
                                "stt_ms": int(stt_time * 1000),
                                "llm_ms": int(llm_time * 1000),
                                "tts_ms": int(tts_time * 1000),
                                "total_ms": int(total_time * 1000)
                            }
                        })
                        
                        order_manager.log_turn(order_id, "assistant", response_text)
                        print(f"[WS:{session_id}] Response sent (Total: {total_time:.2f}s)")
                        
                    except Exception as e:
                        print(f"[WS:{session_id}] Error: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "text": "Something went wrong. Try again?"
                        })
            
            # Handle binary audio chunks
            elif isinstance(message, bytes):
                # Convert bytes to numpy array
                int16_data = np.frombuffer(message, dtype=np.int16)
                float_data = int16_data.astype(np.float32) / 32768.0
                audio_chunks.append(float_data)
                
                # Log every 10th chunk
                if len(audio_chunks) % 10 == 1:
                    print(f"[WS:{session_id}] Audio chunk #{len(audio_chunks)}: {len(int16_data)} samples")
            else:
                print(f"[WS:{session_id}] Unknown message type: {type(message)}")
    
    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[WS:{session_id}] ===== Connection Closed =====\n")


if __name__ == "__main__":
    init_engines()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
