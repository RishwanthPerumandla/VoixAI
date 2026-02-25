"""
Conversation Pipeline for VoixAI v3.0
Connects STT -> Agent -> TTS in a streaming pipeline
"""

import asyncio
import time
from typing import Optional

from src.agent.react_agent import ReActAgent
try:
    from src.processors.deepgram_stt import DeepgramSTTProcessor, MockSTTProcessor, DEEPGRAM_AVAILABLE
except ImportError:
    from src.processors.deepgram_stt import MockSTTProcessor
    DEEPGRAM_AVAILABLE = False
from src.processors.cartesia_tts import CartesiaTTSProcessor, MockTTSProcessor
from src.transports.daily_transport import SimpleWebSocketTransport
from src.config import settings


class ConversationPipeline:
    """
    Main conversation pipeline
    
    Flow:
    1. Receive audio from transport
    2. Process with STT (Deepgram)
    3. Send text to Agent (ReAct)
    4. Synthesize response with TTS (Cartesia)
    5. Send audio back to transport
    """
    
    def __init__(
        self,
        use_mock_stt: bool = False,
        use_mock_tts: bool = False
    ):
        # Transport
        self.transport = SimpleWebSocketTransport()
        
        # STT - Use real Deepgram if API key is available
        if use_mock_stt or not settings.deepgram_api_key:
            print("[Pipeline] Using Mock STT")
            self.stt = MockSTTProcessor()
        else:
            print("[Pipeline] Using Deepgram STT (Real)")
            try:
                self.stt = DeepgramSTTProcessor()
            except Exception as e:
                print(f"[Pipeline] Failed to init Deepgram STT: {e}, using Mock")
                self.stt = MockSTTProcessor()
        
        # Agent
        self.agent = ReActAgent()
        
        # TTS - Use real Cartesia if API key is available
        if use_mock_tts or not settings.cartesia_api_key:
            print("[Pipeline] Using Mock TTS")
            self.tts = MockTTSProcessor()
        else:
            print("[Pipeline] Using Cartesia TTS (Real)")
            try:
                self.tts = CartesiaTTSProcessor()
            except Exception as e:
                print(f"[Pipeline] Failed to init Cartesia TTS: {e}, using Mock")
                self.tts = MockTTSProcessor()
        
        # Session
        self.session_id: Optional[str] = None
        self._running = False
        
        # Metrics
        self.latency_metrics = {
            "stt_ms": 0,
            "llm_ms": 0,
            "tts_ms": 0,
            "total_ms": 0
        }
    
    async def start(self) -> bool:
        """Start the pipeline"""
        try:
            print("[Pipeline] Starting...")
            
            # Start STT
            if not await self.stt.start():
                print("[Pipeline] Failed to start STT")
                return False
            
            # Set up callbacks
            self.stt.on_transcript = self._on_transcript
            self.tts.on_audio = self._on_audio_chunk
            self.transport.on_message = self._on_transport_message
            
            self._running = True
            print("[Pipeline] Started successfully")
            return True
            
        except Exception as e:
            print(f"[Pipeline] Error starting: {e}")
            return False
    
    async def stop(self):
        """Stop the pipeline"""
        print("[Pipeline] Stopping...")
        self._running = False
        
        await self.stt.stop()
        self.tts.stop()
        
        print("[Pipeline] Stopped")
    
    async def handle_websocket(self, websocket, path=""):
        """Handle WebSocket connection from transport"""
        await self.transport.handle_websocket(websocket, path)
    
    async def _on_transcript(self, transcript: str, is_final: bool):
        """Handle transcript from STT"""
        if not is_final:
            return  # Wait for final transcript
        
        print(f"[Pipeline] User said: '{transcript}'")
        
        # Generate session ID if not set
        if not self.session_id:
            self.session_id = f"session-{time.time()}"
        
        # Process with agent
        start_time = time.time()
        
        try:
            response = await self.agent.process(transcript, self.session_id)
            
            llm_latency = (time.time() - start_time) * 1000
            self.latency_metrics["llm_ms"] = llm_latency
            
            print(f"[Pipeline] Agent response: '{response}' (LLM: {llm_latency:.0f}ms)")
            
            # Send text response to client
            await self.transport.send_text({
                "type": "bot_text",
                "content": response,
                "latency_ms": llm_latency
            })
            
            # Synthesize speech
            tts_start = time.time()
            
            # Stream TTS audio
            await self.tts.synthesize_streaming(response)
            
            tts_latency = (time.time() - tts_start) * 1000
            self.latency_metrics["tts_ms"] = tts_latency
            
            total_latency = (time.time() - start_time) * 1000
            self.latency_metrics["total_ms"] = total_latency
            
            print(f"[Pipeline] TTS complete: {tts_latency:.0f}ms, Total: {total_latency:.0f}ms")
            
        except Exception as e:
            print(f"[Pipeline] Error processing: {e}")
            await self.transport.send_text({
                "type": "error",
                "content": "Sorry, I had trouble processing that."
            })
    
    async def _on_audio_chunk(self, audio_data: bytes):
        """Handle audio chunk from TTS"""
        # Send audio to transport (base64 encoded for WebSocket)
        import base64
        await self.transport.send_text({
            "type": "bot_audio",
            "data": base64.b64encode(audio_data).decode('utf-8'),
            "format": "pcm_f32le",
            "sample_rate": 24000
        })
    
    async def _on_transport_message(self, message: dict, websocket):
        """Handle message from transport"""
        msg_type = message.get("type")
        
        if msg_type == "start_conversation":
            self.session_id = message.get("session_id") or f"session-{time.time()}"
            await self.transport.send_text({
                "type": "system",
                "event": "connected",
                "session_id": self.session_id
            }, websocket)
            
        elif msg_type == "audio":
            # Audio data from client (base64 encoded)
            audio_b64 = message.get("data")
            if audio_b64:
                import base64
                audio_data = base64.b64decode(audio_b64)
                # Send to STT
                await self.stt.process_audio(audio_data)
                
        elif msg_type == "text":
            # Text message from client (for testing without STT)
            text = message.get("content", "")
            if text:
                await self._on_transcript(text, True)
                
        elif msg_type == "ping":
            await self.transport.send_text({"type": "pong"}, websocket)
    
    def get_metrics(self) -> dict:
        """Get pipeline latency metrics"""
        return self.latency_metrics.copy()
    
    def is_running(self) -> bool:
        """Check if pipeline is running"""
        return self._running


class MockPipeline:
    """
    Mock pipeline for testing without external APIs
    """
    
    def __init__(self):
        self.transport = SimpleWebSocketTransport()
        self.agent = ReActAgent()
        self.stt = MockSTTProcessor()
        self.session_id = None
        self._running = False
    
    async def start(self):
        print("[MockPipeline] Starting...")
        await self.stt.start()
        self.stt.on_transcript = self._on_transcript
        self._running = True
        return True
    
    async def stop(self):
        print("[MockPipeline] Stopping...")
        await self.stt.stop()
        self._running = False
    
    async def handle_websocket(self, websocket, path=""):
        await self.transport.handle_websocket(websocket, path)
    
    async def _on_transcript(self, transcript: str, is_final: bool):
        if not is_final:
            return
        
        if not self.session_id:
            self.session_id = f"session-{time.time()}"
        
        print(f"[MockPipeline] User: '{transcript}'")
        
        response = await self.agent.process(transcript, self.session_id)
        
        print(f"[MockPipeline] Bot: '{response}'")
        
        await self.transport.send_text({
            "type": "bot_text",
            "content": response,
            "latency_ms": 0
        })
    
    async def simulate_user_message(self, text: str):
        """Simulate user message for testing"""
        await self.stt.simulate_transcript(text)
    
    def is_running(self) -> bool:
        return self._running
    
    def get_metrics(self) -> dict:
        return {"stt_ms": 0, "llm_ms": 0, "tts_ms": 0, "total_ms": 0}
