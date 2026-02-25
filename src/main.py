"""
VoixAI v3.0 - Main Entry Point
Local development server with Pipecat pipeline
"""

import os
import sys
from pathlib import Path

# Windows OpenMP fix
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
import base64
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager

from src.config import settings
from src.pipeline.conversation_pipeline import ConversationPipeline, MockPipeline

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global pipeline instance
pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global pipeline
    
    # Startup
    settings.ensure_data_dir()
    
    # Initialize pipeline with real APIs if keys are available
    use_real_stt = bool(settings.deepgram_api_key)
    use_real_tts = bool(settings.cartesia_api_key)
    
    if not use_real_stt and not use_real_tts:
        logger.info("Starting in MOCK mode")
        pipeline = MockPipeline()
    else:
        logger.info(f"Starting with Real APIs - STT: {use_real_stt}, TTS: {use_real_tts}")
        pipeline = ConversationPipeline(
            use_mock_stt=not use_real_stt,
            use_mock_tts=not use_real_tts
        )
    
    # Start pipeline
    if not await pipeline.start():
        logger.error("Failed to start pipeline")
        raise Exception("Pipeline startup failed")
    
    logger.info(
        "VoixAI v3.0 started",
        environment=settings.environment,
        mock_mode=not (use_real_stt or use_real_tts)
    )
    
    yield
    
    # Shutdown
    if pipeline:
        await pipeline.stop()
    logger.info("VoixAI v3.0 shutdown")


# Create FastAPI app
app = FastAPI(
    title="VoixAI v3.0",
    description="AI Voice Agent for Restaurant Ordering",
    version="3.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main web interface"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "environment": settings.environment,
        "pipeline_running": pipeline.is_running() if pipeline else False,
        "real_stt": bool(settings.deepgram_api_key),
        "real_tts": bool(settings.cartesia_api_key)
    }


@app.get("/metrics")
async def get_metrics():
    """Get pipeline metrics"""
    if pipeline:
        return {
            "latency_ms": pipeline.get_metrics(),
            "session_id": pipeline.session_id
        }
    return {"error": "Pipeline not initialized"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for voice conversations"""
    global pipeline
    
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Create a connection handler
    handler = WebSocketHandler(websocket, pipeline)
    
    try:
        await handler.run()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("WebSocket connection closed")


class WebSocketHandler:
    """Handles individual WebSocket connections"""
    
    def __init__(self, websocket, pipeline):
        self.websocket = websocket
        self.pipeline = pipeline
        self.session_id = None
        self.pending_transcript = None
        
        # Set up STT callback
        if hasattr(self.pipeline.stt, 'on_transcript'):
            self.pipeline.stt.on_transcript = self._on_stt_transcript
    
    async def run(self):
        """Main message loop"""
        # Send connection confirmation
        await self.websocket.send_text(json.dumps({
            "type": "system",
            "event": "connected",
            "session_id": f"session-{asyncio.get_event_loop().time()}"
        }))
        
        while True:
            try:
                # Receive message
                data = await self.websocket.receive_text()
                message = json.loads(data)
                
                await self._handle_message(message)
                
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await self.websocket.send_text(json.dumps({
                    "type": "error",
                    "content": "Sorry, I had trouble processing that."
                }))
    
    async def _handle_message(self, message: dict):
        """Handle a single message"""
        msg_type = message.get("type")
        
        if msg_type == "start_conversation":
            self.session_id = message.get("session_id") or f"session-{asyncio.get_event_loop().time()}"
            await self.websocket.send_text(json.dumps({
                "type": "system",
                "event": "session_started",
                "session_id": self.session_id
            }))
            
        elif msg_type == "audio":
            # Process audio from client
            await self._handle_audio(message)
            
        elif msg_type == "text":
            # Process text message
            await self._handle_text(message)
            
        elif msg_type == "ping":
            await self.websocket.send_text(json.dumps({"type": "pong"}))
    
    async def _handle_audio(self, message: dict):
        """Handle audio message from client"""
        audio_b64 = message.get("data")
        if not audio_b64 or not self.session_id:
            return
        
        print("[WS] Received audio, sending to Deepgram...")
        
        try:
            # Decode audio
            audio_data = base64.b64decode(audio_b64)
            print(f"[WS] Audio size: {len(audio_data)} bytes")
            
            # Reset pending transcript
            self.pending_transcript = None
            
            # Send to STT for transcription
            await self.pipeline.stt.process_audio(audio_data)
            
            # Wait a bit for transcription (in production, this would be async)
            await asyncio.sleep(2)
            
            # Check if we got a transcript
            if hasattr(self.pipeline.stt, 'get_final_transcript'):
                transcript = self.pipeline.stt.get_final_transcript()
                if transcript:
                    print(f"[WS] Transcript: '{transcript}'")
                    await self._process_transcript(transcript)
                    self.pipeline.stt.clear_buffer()
                else:
                    await self.websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "I couldn't hear that. Please try again."
                    }))
            else:
                # Mock STT - simulate
                await self.websocket.send_text(json.dumps({
                    "type": "system",
                    "event": "audio_received"
                }))
            
        except Exception as e:
            print(f"[WS] Error processing audio: {e}")
            await self.websocket.send_text(json.dumps({
                "type": "error",
                "content": "Could not process audio. Please try again."
            }))
    
    async def _handle_text(self, message: dict):
        """Handle text message from client"""
        text = message.get("content", "")
        if not text or not self.session_id:
            return
        
        print(f"[WS] User: '{text}'")
        await self._process_transcript(text)
    
    async def _process_transcript(self, transcript: str):
        """Process transcript through agent and send response"""
        import time
        start_time = time.time()
        
        # Process through agent
        response = await self.pipeline.agent.process(transcript, self.session_id)
        
        latency_ms = (time.time() - start_time) * 1000
        print(f"[WS] Bot: '{response}' ({latency_ms:.0f}ms)")
        
        # Send text response
        await self.websocket.send_text(json.dumps({
            "type": "bot_text",
            "content": response,
            "latency_ms": latency_ms
        }))
        
        # Generate audio response if using real TTS
        if settings.cartesia_api_key:
            try:
                print("[WS] Synthesizing audio response...")
                audio_data = await self.pipeline.tts.synthesize(response)
                if audio_data:
                    await self.websocket.send_text(json.dumps({
                        "type": "bot_audio",
                        "data": base64.b64encode(audio_data).decode('utf-8'),
                        "format": "pcm_f32le",
                        "sample_rate": 24000
                    }))
            except Exception as e:
                print(f"[WS] TTS error: {e}")
    
    async def _on_stt_transcript(self, transcript: str, is_final: bool):
        """Callback for STT transcript"""
        if is_final:
            self.pending_transcript = transcript
            print(f"[STT Callback] Final: '{transcript}'")


if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        "Starting server",
        host="0.0.0.0",
        port=settings.port
    )
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
