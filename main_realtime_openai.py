"""VoixAI Realtime - Full-Duplex Voice Agent using OpenAI Realtime API"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from dotenv import load_dotenv
load_dotenv()

import json
import base64
import asyncio
import websockets
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.order_manager import OrderManager


OPENAI_WS_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="VoixAI - Realtime Full-Duplex")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


class OpenAIRealtimeAgent:
    def __init__(self, session_id: str, order_manager: OrderManager, order_id: int):
        self.session_id = session_id
        self.order_manager = order_manager
        self.order_id = order_id
        self.openai_ws = None
        self.client_ws = None
        self.audio_buffer = b""
        
    async def connect_to_openai(self):
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        print(f"[WS:{self.session_id}] Connecting to OpenAI...")
        self.openai_ws = await websockets.connect(OPENAI_WS_URL, extra_headers=headers)
        
        # Session config - minimal working version
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": "You are Tasha, a friendly Wingstop cashier. Greet customers warmly, ask for their name, then take their wing order.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16"
            }
        }
        
        await self.openai_ws.send(json.dumps(config))
        
        # Wait for session.created
        msg = await self.openai_ws.recv()
        event = json.loads(msg)
        print(f"[WS:{self.session_id}] Session: {event.get('type')}")
        if event.get('type') == 'error':
            print(f"[WS:{self.session_id}] Session error: {event}")
            return
        
        # Wait for session.updated
        msg = await self.openai_ws.recv()
        event = json.loads(msg)
        print(f"[WS:{self.session_id}] Session: {event.get('type')}")
        if event.get('type') == 'error':
            print(f"[WS:{self.session_id}] Session update error: {event}")
        
        # Start the conversation with a user message to trigger response
        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hi there!"}]
            }
        }))
        
        await asyncio.sleep(0.1)
        
        await self.openai_ws.send(json.dumps({"type": "response.create"}))
        print(f"[WS:{self.session_id}] Triggered initial response")
    
    async def handle_client(self, client_ws: WebSocket):
        self.client_ws = client_ws
        await self.connect_to_openai()
        
        await asyncio.gather(
            self.forward_client_to_openai(),
            self.forward_openai_to_client()
        )
    
    async def forward_client_to_openai(self):
        """Forward audio from client to OpenAI"""
        try:
            while True:
                msg = await self.client_ws.receive()
                
                if isinstance(msg, dict) and msg.get("type") == "websocket.receive":
                    if "bytes" in msg:
                        # Buffer audio and send in chunks
                        self.audio_buffer += msg["bytes"]
                        
                        # Send when we have enough data (24000 samples = 1 second)
                        if len(self.audio_buffer) >= 48000:  # 2 seconds of 16-bit 24kHz
                            audio_base64 = base64.b64encode(self.audio_buffer).decode('utf-8')
                            await self.openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": audio_base64
                            }))
                            self.audio_buffer = b""
                            
        except Exception as e:
            print(f"[WS:{self.session_id}] Client->OpenAI error: {e}")
    
    async def forward_openai_to_client(self):
        """Forward audio and events from OpenAI to client"""
        try:
            audio_chunk_count = 0
            
            async for msg in self.openai_ws:
                event = json.loads(msg)
                event_type = event.get("type")
                
                # Log all non-audio events
                if event_type not in ["response.audio.delta"]:
                    print(f"[WS:{self.session_id}] {event_type}")
                
                if event_type == "response.audio.delta":
                    audio_chunk_count += 1
                    if audio_chunk_count == 1:
                        print(f"[WS:{self.session_id}] First audio chunk!")
                    
                    audio_b64 = event.get("delta", "")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        await self.client_ws.send_bytes(audio_bytes)
                
                elif event_type == "response.audio.done":
                    print(f"[WS:{self.session_id}] Audio complete ({audio_chunk_count} chunks)")
                    audio_chunk_count = 0
                
                elif event_type == "response.audio_transcript.delta":
                    print(f"[AI] {event.get('delta', '')}")
                
                elif event_type == "error":
                    print(f"[WS:{self.session_id}] ERROR: {event}")
                    
        except Exception as e:
            print(f"[WS:{self.session_id}] OpenAI->Client error: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index_realtime_openai.html").read_text(encoding='utf-8')


@app.get("/realtime", response_class=HTMLResponse)
async def realtime_page():
    return Path("static/index_realtime_openai.html").read_text(encoding='utf-8')


@app.websocket("/ws/realtime-openai")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    session_id = str(datetime.now().timestamp())[:8]
    print(f"\n[WS:{session_id}] === Connection ===")
    
    if not OPENAI_API_KEY:
        await websocket.send_json({"type": "error", "message": "API key not set"})
        await websocket.close()
        return
    
    order_manager = OrderManager()
    order_id = order_manager.create_order(session_id)
    agent = OpenAIRealtimeAgent(session_id, order_manager, order_id)
    
    try:
        await agent.handle_client(websocket)
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
    finally:
        print(f"[WS:{session_id}] === Closed ===\n")


@app.websocket("/ws/conversational")
async def websocket_fallback(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({
        "type": "error",
        "message": "Use /ws/realtime-openai. Access /realtime"
    })
    await websocket.close()


if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set!")
        exit(1)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
