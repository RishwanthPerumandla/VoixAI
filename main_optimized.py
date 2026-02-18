"""VoixAI Optimized - Multi-core audio processing"""
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
from core.llm_agent import ConversationAgent, ConversationState
from core.order_manager import OrderManager
from core.audio_processor import get_processor, shutdown_processor


# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

app = FastAPI(title="VoixAI - Multi-Core Optimized")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    """Initialize multi-core processor on startup"""
    print("\n" + "="*60)
    print("Starting VoixAI with Multi-Core Processing")
    print(f"CPU Cores: {os.cpu_count()}")
    print("="*60 + "\n")
    
    await get_processor(CONFIG["stt"], CONFIG["tts"])


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await shutdown_processor()


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index_simple.html").read_text(encoding='utf-8')


@app.websocket("/ws/order")
async def websocket_endpoint(websocket: WebSocket):
    """Optimized WebSocket with multi-core audio processing"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] === New Connection ===")
    
    # Get processor instance
    processor = await get_processor()
    
    # State
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
        # TTS in parallel
        audio_bytes = await processor.synthesize(greeting)
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
            
            # Handle FastAPI wrapped messages
            if isinstance(message, dict) and message.get("type") == "websocket.receive":
                
                # Handle binary audio
                if "bytes" in message:
                    if is_recording:
                        data = message["bytes"]
                        int16_data = np.frombuffer(data, dtype=np.int16)
                        float_data = int16_data.astype(np.float32) / 32768.0
                        audio_chunks.append(float_data)
                        
                        if len(audio_chunks) == 1:
                            print(f"[WS:{session_id}] Recording started, first chunk: {len(data)} bytes")
                        elif len(audio_chunks) % 20 == 0:
                            seconds = (len(audio_chunks) * 4096) / 16000
                            await websocket.send_json({
                                "type": "recording",
                                "chunks": len(audio_chunks),
                                "seconds": seconds
                            })
                
                # Handle commands
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
                            chunk_count = len(audio_chunks)
                            print(f"[WS:{session_id}] Recording STOPPED, processing {chunk_count} chunks...")
                            await websocket.send_json({"type": "status", "status": "processing"})
                            
                            if chunk_count < 5:
                                print(f"[WS:{session_id}] Too short")
                                await websocket.send_json({
                                    "type": "error",
                                    "text": "Too short, try again",
                                    "status": "idle"
                                })
                                continue
                            
                            # Process audio in parallel
                            try:
                                pipeline_start = time.time()
                                
                                # Combine chunks
                                full_audio = np.concatenate(audio_chunks)
                                audio_duration = len(full_audio) / 16000
                                print(f"[WS:{session_id}] Audio: {audio_duration:.2f}s")
                                
                                # STT (in process pool, non-blocking)
                                stt_start = time.time()
                                user_text = await processor.transcribe(full_audio)
                                stt_time = time.time() - stt_start
                                
                                if not user_text:
                                    await websocket.send_json({
                                        "type": "error",
                                        "text": "Didn't catch that, try again",
                                        "status": "idle"
                                    })
                                    continue
                                
                                print(f"[WS:{session_id}] Heard: '{user_text}'")
                                order_manager.log_turn(order_id, "user", user_text)
                                
                                # LLM (async, non-blocking)
                                llm_start = time.time()
                                response_text, order_data = agent.process(user_text)
                                llm_time = time.time() - llm_start
                                
                                print(f"[WS:{session_id}] Tasha: '{response_text}'")
                                
                                if order_data and order_data.get("items"):
                                    order_manager.update_order_items(order_id, agent.order_items)
                                if agent.state == ConversationState.CLOSING:
                                    order_manager.complete_order(order_id)
                                
                                # TTS (in process pool, non-blocking)
                                tts_start = time.time()
                                response_audio = await processor.synthesize(response_text)
                                tts_time = time.time() - tts_start
                                
                                pipeline_time = time.time() - pipeline_start
                                
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
                                        "pipeline_ms": int(pipeline_time * 1000)
                                    },
                                    "status": "idle"
                                })
                                
                                order_manager.log_turn(order_id, "assistant", response_text)
                                
                                # Report efficiency gain
                                sequential_estimate = stt_time + llm_time + tts_time
                                if sequential_estimate > 0:
                                    efficiency = (sequential_estimate / pipeline_time) * 100
                                    print(f"[WS:{session_id}] Done: {pipeline_time:.2f}s (efficiency: {efficiency:.0f}%)")
                                
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
    
    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
    finally:
        print(f"[WS:{session_id}] === Closed ===\n")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
