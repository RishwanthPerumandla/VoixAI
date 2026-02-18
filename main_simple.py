"""VoixAI Simple - Drive-thru style voice ordering"""
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
from core.tts_engine_onnx import TTSEngineONNX
from core.order_manager import OrderManager


# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

app = FastAPI(title="VoixAI - Drive Thru")
app.mount("/static", StaticFiles(directory="static"), name="static")

stt_engine: STTEngine = None
tts_engine: TTSEngineONNX = None


def init_engines():
    global stt_engine, tts_engine
    
    stt_config = CONFIG["stt"]
    
    print("[INIT] Loading STT...")
    stt_engine = STTEngine(
        model_size=stt_config["model"],
        device=CONFIG["hardware"]["device"],
        compute_type=stt_config["compute_type"],
        language=stt_config["language"]
    )
    
    print("[INIT] Loading TTS (ONNX)...")
    tts_engine = TTSEngineONNX(voice="af_bella", speed=1.0)
    
    print("[INIT] Ready!")


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index_simple.html").read_text(encoding='utf-8')


@app.websocket("/ws/order")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] === New Drive-Thru Order ===")
    
    # Collect all audio first, then process
    audio_chunks = []
    is_recording = False
    
    order_manager = OrderManager(db_path=CONFIG["database"]["path"])
    order_id = order_manager.create_order(session_id)
    
    try:
        agent = ConversationAgent(config=CONFIG["llm"])
    except Exception as e:
        await websocket.send_json({"type": "error", "text": "Server error"})
        await websocket.close()
        return
    
    # Send greeting
    greeting = "Hey! Welcome to Wingstop. I'm Tasha. What can I getcha?"
    try:
        audio_bytes = tts_engine.synthesize(greeting)
        await websocket.send_json({
            "type": "greeting",
            "text": greeting,
            "audio": base64.b64encode(audio_bytes).decode('utf-8'),
            "state": agent.get_order_summary(),
            "order": order_manager.get_order(order_id)
        })
        order_manager.log_turn(order_id, "assistant", greeting)
    except Exception as e:
        print(f"[WS:{session_id}] TTS error: {e}")
    
    try:
        while True:
            message = await websocket.receive()
            
            # FastAPI wraps messages in dict
            if isinstance(message, dict) and message.get("type") == "websocket.receive":
                
                # Handle binary audio chunks
                if "bytes" in message:
                    if is_recording:
                        data = message["bytes"]
                        int16_data = np.frombuffer(data, dtype=np.int16)
                        float_data = int16_data.astype(np.float32) / 32768.0
                        audio_chunks.append(float_data)
                        
                        # Debug first chunk
                        if len(audio_chunks) == 1:
                            print(f"[WS:{session_id}] First audio chunk: {len(data)} bytes, max={np.max(np.abs(int16_data))}")
                        
                        # Acknowledge every 20 chunks
                        if len(audio_chunks) % 20 == 0:
                            await websocket.send_json({
                                "type": "recording",
                                "chunks": len(audio_chunks),
                                "seconds": (len(audio_chunks) * 4096) / 16000
                            })
                
                # Handle text commands
                elif "text" in message:
                    import json
                    try:
                        cmd = json.loads(message["text"])
                        
                        if cmd.get("command") == "start_recording":
                            audio_chunks = []
                            is_recording = True
                            print(f"[WS:{session_id}] Recording STARTED")
                            await websocket.send_json({"type": "status", "status": "recording"})
                        
                        elif cmd.get("command") == "stop_recording":
                            is_recording = False
                            print(f"[WS:{session_id}] Recording STOPPED, processing {len(audio_chunks)} chunks...")
                            await websocket.send_json({"type": "status", "status": "processing"})
                            
                            if len(audio_chunks) < 5:
                                print(f"[WS:{session_id}] Too short")
                                await websocket.send_json({
                                    "type": "error",
                                    "text": "Too short, try again",
                                    "status": "idle"
                                })
                                continue
                            
                            # Process the full audio
                            try:
                                start = time.time()
                                
                                # Combine all chunks
                                full_audio = np.concatenate(audio_chunks)
                                print(f"[WS:{session_id}] Audio: {len(full_audio)/16000:.2f}s")
                                
                                # STT
                                t1 = time.time()
                                user_text = stt_engine.transcribe(full_audio)
                                stt_time = time.time() - t1
                                
                                if not user_text:
                                    await websocket.send_json({
                                        "type": "error",
                                        "text": "Didn't catch that, try again",
                                        "status": "idle"
                                    })
                                    continue
                                
                                print(f"[WS:{session_id}] Heard: '{user_text}' ({stt_time:.2f}s)")
                                order_manager.log_turn(order_id, "user", user_text)
                                
                                # LLM
                                t2 = time.time()
                                response_text, order_data = agent.process(user_text)
                                llm_time = time.time() - t2
                                
                                print(f"[WS:{session_id}] Tasha: '{response_text}' ({llm_time:.2f}s)")
                                
                                if order_data and order_data.get("items"):
                                    order_manager.update_order_items(order_id, agent.order_items)
                                if agent.state == ConversationState.CLOSING:
                                    order_manager.complete_order(order_id)
                                
                                # TTS
                                t3 = time.time()
                                response_audio = tts_engine.synthesize(response_text)
                                tts_time = time.time() - t3
                                
                                total_time = time.time() - start
                                
                                await websocket.send_json({
                                    "type": "response",
                                    "text": response_text,
                                    "audio": base64.b64encode(response_audio).decode('utf-8'),
                                    "state": agent.get_order_summary(),
                                    "order": order_manager.get_order(order_id),
                                    "latency": {
                                        "stt_ms": int(stt_time * 1000),
                                        "llm_ms": int(llm_time * 1000),
                                        "tts_ms": int(tts_time * 1000),
                                        "total_ms": int(total_time * 1000)
                                    },
                                    "status": "idle"
                                })
                                
                                order_manager.log_turn(order_id, "assistant", response_text)
                                print(f"[WS:{session_id}] Done ({total_time:.2f}s total)")
                                
                            except Exception as e:
                                print(f"[WS:{session_id}] Error: {e}")
                                import traceback
                                traceback.print_exc()
                                await websocket.send_json({
                                    "type": "error",
                                    "text": "Something went wrong, try again",
                                    "status": "idle"
                                })
                        
                        elif cmd.get("command") == "reset":
                            agent.reset()
                            order_id = order_manager.create_order(session_id)
                            audio_chunks = []
                            await websocket.send_json({
                                "type": "reset",
                                "state": agent.get_order_summary(),
                                "status": "idle"
                            })
                    
                    except json.JSONDecodeError:
                        pass
            else:
                # Debug unknown message types
                print(f"[WS:{session_id}] Unknown message: {type(message)}")
    
    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
    finally:
        print(f"[WS:{session_id}] === Closed ===\n")


if __name__ == "__main__":
    init_engines()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
