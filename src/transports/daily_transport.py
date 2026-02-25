"""
Daily.co WebRTC Transport for VoixAI v3.0
Handles real-time audio streaming with Daily.co
"""

import asyncio
import json
from typing import Callable, Optional
import aiohttp

from src.config import settings


class DailyTransport:
    """
    WebRTC transport using Daily.co
    
    Handles:
    - Room connection/disconnection
    - Audio streaming (send/receive)
    - Participant events
    """
    
    def __init__(self, room_url: str = None, token: str = None):
        self.room_url = room_url
        self.token = token or settings.daily_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Callbacks
        self.on_participant_joined: Optional[Callable] = None
        self.on_participant_left: Optional[Callable] = None
        self.on_audio_frame: Optional[Callable] = None
        self.on_transcript: Optional[Callable] = None
        
        self._connected = False
        self._room_name = None
    
    async def connect(self) -> bool:
        """Connect to Daily.co room"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Create room if not provided
            if not self.room_url:
                room = await self._create_room()
                self.room_url = room["url"]
                self._room_name = room["name"]
            
            self._connected = True
            print(f"[DailyTransport] Connected to room: {self.room_url}")
            return True
            
        except Exception as e:
            print(f"[DailyTransport] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from room"""
        self._connected = False
        if self.session:
            await self.session.close()
            self.session = None
        print("[DailyTransport] Disconnected")
    
    async def _create_room(self) -> dict:
        """Create a new Daily.co room via API"""
        url = "https://api.daily.co/v1/rooms"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "name": f"voixai-{asyncio.get_event_loop().time()}",
            "privacy": "public",
            "properties": {
                "start_audio_off": False,
                "start_video_off": True,
                "enable_screenshare": False,
                "enable_chat": False,
                "exp": int(asyncio.get_event_loop().time()) + 3600  # 1 hour
            }
        }
        
        async with self.session.post(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                raise Exception(f"Failed to create room: {error}")
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the room"""
        # This will be implemented with Pipecat's daily transport
        # For now, we'll use a WebSocket-based approach
        pass
    
    async def receive_audio(self) -> bytes:
        """Receive audio data from the room"""
        # Placeholder for audio receiving
        await asyncio.sleep(0.1)
        return b""
    
    def is_connected(self) -> bool:
        """Check if transport is connected"""
        return self._connected
    
    def get_room_url(self) -> Optional[str]:
        """Get the room URL"""
        return self.room_url


class SimpleWebSocketTransport:
    """
    Fallback WebSocket transport for local testing
    Uses simple WebSocket without Daily.co (for testing)
    """
    
    def __init__(self):
        self.connections = []
        self.on_message: Optional[Callable] = None
        self.on_audio: Optional[Callable] = None
    
    async def handle_websocket(self, websocket, path=""):
        """Handle WebSocket connection"""
        self.connections.append(websocket)
        print(f"[WebSocket] Client connected. Total: {len(self.connections)}")
        
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    # Audio data
                    if self.on_audio:
                        await self.on_audio(message)
                else:
                    # Text message
                    data = json.loads(message)
                    if self.on_message:
                        await self.on_message(data, websocket)
                        
        except Exception as e:
            print(f"[WebSocket] Error: {e}")
        finally:
            self.connections.remove(websocket)
            print(f"[WebSocket] Client disconnected. Total: {len(self.connections)}")
    
    async def send_text(self, message: dict, websocket=None):
        """Send text message to client(s)"""
        if websocket:
            await websocket.send(json.dumps(message))
        else:
            # Broadcast to all
            for conn in self.connections:
                await conn.send(json.dumps(message))
    
    async def send_audio(self, audio_data: bytes, websocket=None):
        """Send audio data to client(s)"""
        if websocket:
            await websocket.send(audio_data)
        else:
            # Broadcast to all
            for conn in self.connections:
                await conn.send(audio_data)
