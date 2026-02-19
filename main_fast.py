"""VoixAI Fast - Optimized half-duplex with streaming TTS"""
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

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from core.audio_stream import AudioBuffer
from core.stt_engine import STTEngine  
from core.llm_agent_conversational import ConversationalAgent, DialogueState
from core.order_manager import OrderManager

# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# Use fastest settings
CONFIG["stt"]["model"] = "tiny.en"

app = FastAPI(title="VoixAI - Fast")
app.mount("/static", StaticFiles(directory="static"), name="static")

stt_engine = None

class FastAgent:
    """Optimized streaming agent"""
    
    def __init__(self):
        self.stt = STTEngine(
            model_size="tiny.en",
            device="cpu", 
            compute_type="int8",
            language="en"
        )
        
    def transcribe_stream(self, audio_chunks):
        """Fast transcription"""
        if len(audio_chunks) < 3:
            return None
        
        full_audio = np.concatenate(audio_chunks)
        return self.stt.transcribe(full_audio)


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index_fast.html").read_text(encoding='utf-8')


@app.websocket("/ws/fast")
async def websocket_endpoint(websocket: WebSocket):
    """Fast WebSocket with streaming"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] Connected")
    
    order_manager = OrderManager()
    order_id = order_manager.create_order(session_id)
    agent = ConversationalAgent(config=CONFIG["llm"])
    
    # Simple greeting - no TTS delay
    greeting = "Hey! I'm Tasha. What's your name and how many wings?"
    await websocket.send_json({
        "type": "greeting",
        "text": greeting,
        "state": agent.get_order_summary(),
        "use_browser_tts": True  # Flag to use browser TTS
    })
    
    audio_chunks = []
    is_recording = False
    
    try:
        while True:
            msg = await websocket.receive()
            
            if isinstance(msg, dict) and msg.get("type") == "websocket.receive":
                
                if "bytes" in msg:
                    if is_recording:
                        int16_data = np.frombuffer(msg["bytes"], dtype=np.int16)
                        float_data = int16_data.astype(np.float32) / 32768.0
                        audio_chunks.append(float_data)
                
                elif "text" in msg:
                    import json
                    cmd = json.loads(msg["text"])
                    
                    if cmd.get("command") == "start":
                        audio_chunks = []
                        is_recording = True
                        await websocket.send_json({"type": "status", "status": "listening"})
                    
                    elif cmd.get("command") == "stop":
                        is_recording = False
                        await websocket.send_json({"type": "status", "status": "thinking"})
                        
                        if len(audio_chunks) < 3:
                            await websocket.send_json({"type": "error", "text": "Too short"})
                            continue
                        
                        # Fast STT
                        start = time.time()
                        user_text = stt_engine.transcribe(np.concatenate(audio_chunks))
                        stt_time = time.time() - start
                        
                        if not user_text:
                            await websocket.send_json({"type": "error", "text": "Didn't catch that"})
                            continue
                        
                        print(f"[WS:{session_id}] Heard: '{user_text}' ({stt_time:.2f}s)")
                        
                        # Fast LLM
                        start = time.time()
                        response_text, order_data = agent.process(user_text)
                        llm_time = time.time() - start
                        
                        # Update order
                        if order_data:
                            order_manager.update_order_items(order_id, order_data.get("items", []))
                        
                        total_time = time.time() - start
                        
                        await websocket.send_json({
                            "type": "response",
                            "text": response_text,
                            "state": agent.get_order_summary(),
                            "order": order_manager.get_order(order_id),
                            "order_complete": order_data.get("order_complete", False),
                            "use_browser_tts": True,
                            "latency": {
                                "stt_ms": int(stt_time * 1000),
                                "llm_ms": int(llm_time * 1000),
                                "total_ms": int(total_time * 1000)
                            }
                        })
                        
                        print(f"[WS:{session_id}] Tasha: '{response_text}' ({total_time:.2f}s total)")
    
    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")


if __name__ == "__main__":
    print("[INIT] Loading STT (tiny.en)...")
    stt_engine = STTEngine(
        model_size="tiny.en",
        device="cpu",
        compute_type="int8", 
        language="en"
    )
    print("[INIT] Ready!")
    uvicorn.run(app, host="0.0.0.0", port=8000)
