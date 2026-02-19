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


# OpenAI Realtime API configuration
OPENAI_WS_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="VoixAI - Realtime Full-Duplex")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Wingstop order context that we'll inject into the conversation
WINGSTOP_CONTEXT = """
You are Tasha, a friendly and enthusiastic Wingstop cashier taking phone orders. You're talking to customers in real-time with your voice.

YOUR PERSONALITY:
- Use casual, upbeat language: "lemme", "gotcha", "awesome", "perfect"
- Be enthusiastic but not overwhelming
- Always confirm what you heard before moving on
- Up-sell naturally: suggest combos for 6+ wings, extra dips, larger drinks

WINGSTOP MENU:
Wings: Bone-in or boneless, quantities: 6, 8, 10, 15, 20 pieces
Flavors: Lemon Pepper (most popular), Cajun, Garlic Parmesan, Hickory Smoked BBQ, Mild, Original Hot, Atomic, Mango Habanero, Korean BBQ, Spicy Korean, Louisiana Rub
Combos: Include fries + drink, saves $3 (great for 6+ wings)
Drinks: Coke, Diet Coke, Sprite, Dr Pepper, Lemonade (20oz or 32oz)
Sides: Seasoned Fries, Veggie Sticks, Cheese Fries
Dips: Ranch, Blue Cheese, Honey Mustard ($0.99 extra)

ORDER FLOW:
1. Greet and get customer name
2. Ask wing quantity and type (bone-in or boneless)
3. Suggest combo if 6+ wings
4. Get flavors (up to 2)
5. Ask about drinks/sides if not combo
6. Confirm order with total price
7. Give pickup time (15-20 mins)

PRICING (calculate accurately):
- Wings: $1.29 each
- Combo: saves $3 (includes fries + drink)
- 32oz drink: $3.49, 20oz: $2.49
- Extra dip: $0.99

UPSELL TRIGGERS:
- "That's 6+ wings, want to make it a combo? Saves you $3!"
- "Want to add an extra dip for $0.99?"
- "Upgrade to 32oz for just $0.50 more?"

Always say the total price clearly before confirming. Be conversational - let customers interrupt you, clarify when needed, and make the experience feel human.

Current order state will be provided in function calls. Use the place_order function when they're ready to confirm.
"""


class OpenAIRealtimeAgent:
    """Full-duplex agent using OpenAI Realtime API"""
    
    def __init__(self, session_id: str, order_manager: OrderManager, order_id: int):
        self.session_id = session_id
        self.order_manager = order_manager
        self.order_id = order_id
        self.openai_ws = None
        self.client_ws = None
        self.order_data = {
            "customer_name": "",
            "items": [],
            "wing_qty": 0,
            "wing_type": "",
            "flavors": [],
            "is_combo": False,
            "drink": "",
            "side": "",
            "dip": "",
            "total": 0.0,
            "confirmed": False
        }
    
    async def connect_to_openai(self):
        """Connect to OpenAI Realtime API"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.openai_ws = await websockets.connect(
            OPENAI_WS_URL,
            extra_headers=headers
        )
        
        # Configure the session
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": WINGSTOP_CONTEXT,
                "voice": "alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "update_order",
                        "description": "Update the order with wing quantity, type, flavors, combo status, etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_name": {"type": "string"},
                                "wing_qty": {"type": "integer"},
                                "wing_type": {"type": "string", "enum": ["boneless", "bone-in"]},
                                "flavors": {"type": "array", "items": {"type": "string"}},
                                "is_combo": {"type": "boolean"},
                                "drink": {"type": "string"},
                                "side": {"type": "string"},
                                "dip": {"type": "string"}
                            }
                        }
                    },
                    {
                        "type": "function", 
                        "name": "calculate_total",
                        "description": "Calculate the total price of the order",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "type": "function",
                        "name": "place_order",
                        "description": "Place the final order when customer confirms",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }
        
        await self.openai_ws.send(json.dumps(session_config))
        print(f"[WS:{self.session_id}] Session config sent")
        
        # Wait for session.created confirmation
        response = await self.openai_ws.recv()
        event = json.loads(response)
        print(f"[WS:{self.session_id}] Session event: {event.get('type')}")
        
        # Wait a bit for session to be ready
        await asyncio.sleep(0.5)
        
        # Create initial response to start conversation - simpler approach
        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hello, I'd like to place an order"}]
            }
        }))
        print(f"[WS:{self.session_id}] Sent user message")
        
        await asyncio.sleep(0.2)
        
        await self.openai_ws.send(json.dumps({
            "type": "response.create"
        }))
        print(f"[WS:{self.session_id}] Sent response.create")
    
    async def handle_client(self, client_ws: WebSocket):
        """Handle client WebSocket connection"""
        self.client_ws = client_ws
        await self.connect_to_openai()
        
        # Start bidirectional streaming
        await asyncio.gather(
            self.client_to_openai(),
            self.openai_to_client()
        )
    
    async def client_to_openai(self):
        """Stream audio from client to OpenAI"""
        try:
            while True:
                message = await self.client_ws.receive()
                
                if isinstance(message, dict):
                    if message.get("type") == "websocket.receive":
                        # Handle binary audio from client
                        if "bytes" in message:
                            # Send to OpenAI as base64
                            audio_base64 = base64.b64encode(message["bytes"]).decode('utf-8')
                            await self.openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": audio_base64
                            }))
                        
                        # Handle text commands
                        elif "text" in message:
                            data = json.loads(message["text"])
                            if data.get("type") == "response.create":
                                # Force a response from the model
                                await self.openai_ws.send(json.dumps({
                                    "type": "response.create"
                                }))
        except WebSocketDisconnect:
            print(f"[WS:{self.session_id}] Client disconnected")
        except Exception as e:
            print(f"[WS:{self.session_id}] Error in client_to_openai: {e}")
    
    async def openai_to_client(self):
        """Stream audio and events from OpenAI to client"""
        try:
            async for message in self.openai_ws:
                event = json.loads(message)
                event_type = event.get("type")
                
                # Log events
                if event_type not in ["response.audio.delta", "input_audio_buffer.committed"]:
                    print(f"[WS:{self.session_id}] Event: {event_type}")
                
                # Check for errors
                if event_type == "error":
                    print(f"[WS:{self.session_id}] ERROR: {event}")
                
                # Count audio chunks
                if event_type == "response.audio.delta":
                    if not hasattr(self, '_audio_count'):
                        self._audio_count = 0
                        print(f"[WS:{self.session_id}] First audio chunk received!")
                    self._audio_count += 1
                
                # Handle different event types
                if event_type == "response.audio.delta":
                    # Stream audio to client
                    try:
                        audio_base64 = event.get("delta", "")
                        if audio_base64:
                            audio_data = base64.b64decode(audio_base64)
                            await self.client_ws.send_bytes(audio_data)
                    except Exception as e:
                        print(f"[WS:{self.session_id}] Audio decode error: {e}")
                
                elif event_type == "response.audio.done":
                    print(f"[WS:{self.session_id}] AI audio response complete ({getattr(self, '_audio_count', 0)} chunks)")
                    self._audio_count = 0
                
                elif event_type == "response.audio_transcript.delta":
                    # Real-time transcription of what AI is saying
                    print(f"[AI] {event.get('delta', '')}")
                
                elif event_type == "input_audio_buffer.speech_started":
                    # User started speaking (interrupt)
                    print(f"[WS:{self.session_id}] User interrupted!")
                    await self.client_ws.send_json({
                        "type": "user_started_speaking"
                    })
                
                elif event_type == "input_audio_buffer.speech_stopped":
                    # User stopped speaking
                    print(f"[WS:{self.session_id}] User stopped speaking")
                
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Full transcription of user speech
                    transcript = event.get("transcript", "")
                    print(f"[User] {transcript}")
                    self.order_manager.log_turn(self.order_id, "user", transcript)
                
                elif event_type == "response.done":
                    # AI finished responding
                    print(f"[WS:{self.session_id}] AI response complete")
                    await self.client_ws.send_json({
                        "type": "ai_response_complete"
                    })
                
                elif event_type == "response.function_call_arguments.done":
                    # Handle function calls
                    await self._handle_function_call(event)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"[WS:{self.session_id}] OpenAI connection closed")
        except Exception as e:
            print(f"[WS:{self.session_id}] Error in openai_to_client: {e}")
    
    async def _handle_function_call(self, event: Dict):
        """Handle function calls from OpenAI"""
        function_name = event.get("name")
        call_id = event.get("call_id")
        arguments = json.loads(event.get("arguments", "{}"))
        
        print(f"[WS:{self.session_id}] Function call: {function_name}({arguments})")
        
        if function_name == "update_order":
            # Update order data
            for key, value in arguments.items():
                if value:
                    self.order_data[key] = value
            
            # Save to database
            items = self._order_data_to_items()
            self.order_manager.update_order_items(self.order_id, items)
            
            # Send result back to OpenAI
            await self.openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"success": True, "order": self.order_data})
                }
            }))
        
        elif function_name == "calculate_total":
            total = self._calculate_price()
            self.order_data["total"] = total
            
            await self.openai_ws.send(json.dumps({
                "type": "conversation.item.create", 
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"total": total})
                }
            }))
        
        elif function_name == "place_order":
            self.order_data["confirmed"] = True
            self.order_manager.complete_order(self.order_id)
            
            await self.openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output", 
                    "call_id": call_id,
                    "output": json.dumps({
                        "success": True,
                        "order_number": self.order_id,
                        "pickup_time": "15-20 minutes",
                        "total": self.order_data["total"]
                    })
                }
            }))
            
            # Notify client
            await self.client_ws.send_json({
                "type": "order_complete",
                "order": self.order_data
            })
    
    def _order_data_to_items(self) -> list:
        """Convert order data to items list"""
        items = []
        if self.order_data["wing_qty"] > 0:
            items.append({
                "name": f"{self.order_data['wing_type']} wings",
                "qty": self.order_data["wing_qty"],
                "category": "wings",
                "modifiers": {
                    "flavors": self.order_data["flavors"],
                    "type": self.order_data["wing_type"]
                }
            })
        # Add other items...
        return items
    
    def _calculate_price(self) -> float:
        """Calculate order total"""
        total = 0.0
        if self.order_data["wing_qty"] > 0:
            total += self.order_data["wing_qty"] * 1.29
        if self.order_data["is_combo"]:
            total -= 3.00
        if self.order_data["dip"]:
            total += 0.99
        return max(total, 0)


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index_realtime_openai.html").read_text(encoding='utf-8')

@app.get("/realtime", response_class=HTMLResponse)
async def realtime_page():
    return Path("static/index_realtime_openai.html").read_text(encoding='utf-8')


@app.websocket("/ws/realtime-openai")
async def websocket_endpoint(websocket: WebSocket):
    """Full-duplex WebSocket endpoint"""
    await websocket.accept()
    
    session_id = str(datetime.now().timestamp())[:8]
    print(f"\n[WS:{session_id}] === Realtime OpenAI Connection ===")
    
    if not OPENAI_API_KEY:
        await websocket.send_json({"type": "error", "message": "OpenAI API key not configured"})
        await websocket.close()
        return
    
    order_manager = OrderManager()
    order_id = order_manager.create_order(session_id)
    
    agent = OpenAIRealtimeAgent(session_id, order_manager, order_id)
    
    try:
        await agent.handle_client(websocket)
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[WS:{session_id}] === Closed ===\n")


# Fallback for old endpoint - redirect to new
@app.websocket("/ws/conversational")
async def websocket_fallback(websocket: WebSocket):
    """Fallback endpoint for backward compatibility"""
    await websocket.accept()
    await websocket.send_json({
        "type": "error",
        "message": "Please use /ws/realtime-openai endpoint. Access http://localhost:8000/realtime"
    })
    await websocket.close()


if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set!")
        exit(1)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
