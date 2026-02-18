"""VoixAI v2 - Always Listening Mode"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from dotenv import load_dotenv
load_dotenv()

import io
import base64
import time
import yaml
import uuid
import asyncio
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
from core.tts_engine_onnx import TTSEngineONNX
from core.order_manager import OrderManager


# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# Initialize FastAPI
app = FastAPI(title=f"{CONFIG['app']['name']} - Always Listening")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global engines
stt_engine: STTEngine = None
tts_engine: TTSEngineONNX = None


def init_engines():
    """Initialize shared engines on startup"""
    global stt_engine, tts_engine
    
    stt_config = CONFIG["stt"]
    
    print("[INIT] Loading STT engine...")
    stt_engine = STTEngine(
        model_size=stt_config["model"],
        device=CONFIG["hardware"]["device"],
        compute_type=stt_config["compute_type"],
        language=stt_config["language"]
    )
    
    print("[INIT] Loading TTS engine (ONNX)...")
    tts_engine = TTSEngineONNX(
        voice="af_bella",
        speed=1.0
    )
    
    print("[INIT] All engines loaded successfully!")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path("static/index_v2.html")
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return "<h1>VoixAI v2 - Always Listening</h1>"


@app.websocket("/ws/conversation")
async def websocket_endpoint(websocket: WebSocket):
    """Always-listening WebSocket with VAD auto-detection"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] ===== New Connection (Always Listening) =====")
    
    # Initialize per-connection state
    audio_buffer = AudioBuffer(
        sample_rate=CONFIG["hardware"]["sample_rate"],
        silence_ms=800,  # 800ms silence = end of utterance
        vad_threshold=0.5,
        min_utterance_ms=500
    )
    
    order_manager = OrderManager(db_path=CONFIG["database"]["path"])
    order_id = order_manager.create_order(session_id)
    
    try:
        agent = ConversationAgent(config=CONFIG["llm"])
        print(f"[WS:{session_id}] Agent ready")
    except Exception as e:
        print(f"[WS:{session_id}] ERROR: {e}")
        await websocket.send_json({"type": "error", "text": "Server error"})
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
            "order": order_manager.get_order(order_id),
            "listening": True
        })
        order_manager.log_turn(order_id, "assistant", greeting)
        print(f"[WS:{session_id}] Greeting sent - now listening...")
    except Exception as e:
        print(f"[WS:{session_id}] TTS Error: {e}")
    
    # Processing state
    is_processing = False
    audio_chunks = []
    
    async def process_utterance(utterance: np.ndarray):
        """Process detected utterance"""
        nonlocal is_processing
        is_processing = True
        
        await websocket.send_json({"type": "processing", "status": "started"})
        
        start_time = time.time()
        timings = {}
        
        try:
            # STT
            t1 = time.time()
            user_text = stt_engine.transcribe(utterance)
            timings["stt_ms"] = int((time.time() - t1) * 1000)
            
            if not user_text:
                print(f"[WS:{session_id}] No speech detected")
                await websocket.send_json({
                    "type": "error",
                    "text": "Didn't catch that",
                    "listening": True
                })
                is_processing = False
                return
            
            print(f"[WS:{session_id}] User: '{user_text}'")
            order_manager.log_turn(order_id, "user", user_text)
            
            # LLM
            t2 = time.time()
            response_text, order_data = agent.process(user_text)
            timings["llm_ms"] = int((time.time() - t2) * 1000)
            
            print(f"[WS:{session_id}] Tasha: '{response_text}'")
            
            # Update order
            if order_data and order_data.get("items"):
                order_manager.update_order_items(order_id, agent.order_items)
            if agent.state == ConversationState.CLOSING:
                order_manager.complete_order(order_id)
            
            # TTS
            t3 = time.time()
            response_audio = tts_engine.synthesize(response_text)
            timings["tts_ms"] = int((time.time() - t3) * 1000)
            
            total_ms = int((time.time() - start_time) * 1000)
            timings["total_ms"] = total_ms
            
            audio_b64 = base64.b64encode(response_audio).decode('utf-8')
            
            await websocket.send_json({
                "type": "response",
                "text": response_text,
                "audio": audio_b64,
                "state": agent.get_order_summary(),
                "order": order_manager.get_order(order_id),
                "latency": timings,
                "listening": True
            })
            
            order_manager.log_turn(order_id, "assistant", response_text)
            print(f"[WS:{session_id}] Response sent ({total_ms}ms)")
            
        except Exception as e:
            print(f"[WS:{session_id}] Error: {e}")
            await websocket.send_json({
                "type": "error",
                "text": "Something went wrong",
                "listening": True
            })
        finally:
            is_processing = False
    
    try:
        while True:
            # Receive audio chunks continuously
            raw_message = await websocket.receive()
            
            # Unwrap FastAPI's internal format
            if isinstance(raw_message, dict):
                if raw_message.get("type") == "websocket.receive":
                    if "bytes" in raw_message:
                        message = raw_message["bytes"]
                    elif "text" in raw_message:
                        import json
                        try:
                            cmd = json.loads(raw_message["text"])
                            if cmd.get("command") == "reset":
                                agent.reset()
                                audio_chunks = []
                                order_id = order_manager.create_order(session_id)
                                await websocket.send_json({
                                    "type": "reset",
                                    "state": agent.get_order_summary(),
                                    "listening": True
                                })
                            continue
                        except:
                            continue
                    else:
                        continue
                else:
                    continue
            else:
                message = raw_message
            
            # Skip if currently processing (don't buffer new audio during response)
            if is_processing:
                continue
            
            # Handle binary audio
            if isinstance(message, bytes):
                # Convert to numpy
                int16_data = np.frombuffer(message, dtype=np.int16)
                float_data = int16_data.astype(np.float32) / 32768.0
                
                # Feed to VAD
                utterance = audio_buffer.add_chunk(message)
                
                # If VAD detected end of utterance, process it
                if utterance is not None:
                    print(f"[WS:{session_id}] VAD: Utterance detected ({len(utterance)/16000:.2f}s)")
                    # Process in background so we can keep receiving
                    asyncio.create_task(process_utterance(utterance))
    
    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
    finally:
        print(f"[WS:{session_id}] ===== Connection Closed =====\n")


if __name__ == "__main__":
    init_engines()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
