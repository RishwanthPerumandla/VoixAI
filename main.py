"""VoixAI v2.0 - ReAct-based Autonomous AI Voice Agent for Wingstop"""
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

# v2.0 imports
from core.audio_stream import AudioBuffer
from core.stt_engine import STTEngine
from core.tts_engine_onnx import TTSEngineONNX
from core.agent import ReActAgent
from core.memory import MemoryManager
from core.interrupt_handler import InterruptHandler, InterruptType


# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

app = FastAPI(title="VoixAI v2.0 - ReAct Agent")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global engines
stt_engine: STTEngine = None
tts_engine: TTSEngineONNX = None


def init_engines():
    """Initialize shared engines on startup"""
    global stt_engine, tts_engine
    
    stt_config = CONFIG.get("stt", CONFIG.get("asr", {}))
    
    print("[INIT] VoixAI v2.0 - Starting ReAct Agent...")
    print("[INIT] Loading STT engine...")
    stt_engine = STTEngine(
        model_size=stt_config.get("model", "tiny.en"),
        device=CONFIG.get("hardware", {}).get("device", "cpu"),
        compute_type=stt_config.get("compute_type", "int8"),
        language=stt_config.get("language", "en")
    )
    
    print("[INIT] Loading TTS engine...")
    tts_config = CONFIG.get("tts", {})
    tts_engine = TTSEngineONNX(
        voice=tts_config.get("voice", "af_bella"),
        speed=tts_config.get("speed", 1.2)
    )
    
    print("[INIT] Ready! ReAct Agent is live.")


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index.html").read_text(encoding='utf-8')


class ConversationalProcessor:
    """Handles conversational audio processing with the ReAct agent"""
    
    def __init__(self, websocket, session_id: str, agent: ReActAgent, 
                 memory: MemoryManager, order_id: int):
        self.ws = websocket
        self.session_id = session_id
        self.agent = agent
        self.memory = memory
        self.order_id = order_id
        self.audio_chunks = []
        self.is_recording = False
        
        # Initialize audio buffer with config settings
        audio_config = CONFIG.get("audio", {})
        self.audio_buffer = AudioBuffer(
            sample_rate=CONFIG.get("hardware", {}).get("sample_rate", 16000),
            silence_ms=audio_config.get("silence_duration_ms", 800),
            vad_threshold=audio_config.get("vad_threshold", 0.25),
            min_utterance_ms=audio_config.get("min_utterance_ms", 400),
            normalization=audio_config.get("normalization", True),
            noise_gate=audio_config.get("noise_gate", 0.003)
        )
        
        # Initialize interrupt handler
        self.interrupt_handler = InterruptHandler(
            sample_rate=CONFIG.get("hardware", {}).get("sample_rate", 16000),
            energy_threshold=audio_config.get("interruption_threshold", 0.7)
        )
    
    async def start_recording(self):
        """Start a new recording session"""
        self.audio_chunks = []
        self.is_recording = True
        self.audio_buffer.reset()
        self.interrupt_handler.reset()
        print(f"[WS:{self.session_id}] Recording STARTED")
        await self.ws.send_json({"type": "status", "status": "recording"})
    
    async def process_audio_chunk(self, chunk_bytes: bytes):
        """Process incoming audio chunk"""
        if not self.is_recording:
            return
        
        # Convert to numpy
        int16_data = np.frombuffer(chunk_bytes, dtype=np.int16)
        float_data = int16_data.astype(np.float32) / 32768.0
        self.audio_chunks.append(float_data)
        
        # Check for interrupts
        interrupt = self.interrupt_handler.process_audio(float_data)
        if interrupt != InterruptType.NONE:
            print(f"[WS:{self.session_id}] Interrupt detected: {interrupt.value}")
            # Could emit backchannel here
        
        # Feed to VAD
        utterance = self.audio_buffer.add_chunk(chunk_bytes)
        
        # If VAD detected end of speech, auto-process
        if utterance is not None:
            print(f"[WS:{self.session_id}] VAD detected end of speech")
            await self.stop_and_process()
    
    async def stop_and_process(self):
        """Stop recording and process"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        chunk_count = len(self.audio_chunks)
        
        print(f"[WS:{self.session_id}] Recording STOPPED, {chunk_count} chunks")
        await self.ws.send_json({"type": "status", "status": "processing"})
        
        if chunk_count < 3:
            await self.ws.send_json({
                "type": "error",
                "text": "Too short - speak a bit longer",
                "status": "idle"
            })
            return
        
        await self._process_utterance()
    
    async def _process_utterance(self):
        """Process the captured audio with the ReAct agent"""
        try:
            start = time.time()
            
            # Combine chunks
            full_audio = np.concatenate(self.audio_chunks)
            audio_duration = len(full_audio) / 16000
            print(f"[WS:{self.session_id}] Processing {audio_duration:.2f}s audio")
            
            # STT
            t1 = time.time()
            user_text = stt_engine.transcribe(full_audio)
            stt_time = time.time() - t1
            
            if not user_text or len(user_text.strip()) < 2:
                await self.ws.send_json({
                    "type": "error",
                    "text": "Couldn't hear you - speak louder",
                    "status": "idle"
                })
                return
            
            print(f"[WS:{self.session_id}] Heard: '{user_text}' ({stt_time*1000:.0f}ms)")
            
            # ReAct Agent Processing
            t2 = time.time()
            response_text, order_data = self.agent.process(user_text, self.session_id)
            agent_time = time.time() - t2
            
            print(f"[WS:{self.session_id}] Tasha: '{response_text}'")
            print(f"[WS:{self.session_id}] State: {order_data.get('state', 'unknown')}, Complete: {order_data.get('order_complete', False)}")
            
            # Update order in database
            if order_data and order_data.get("items"):
                # Calculate total
                total = order_data.get("total_price", 0)
                self.memory.update_order(self.order_id, order_data["items"], total)
                
                # Complete order if done
                if order_data.get("order_complete"):
                    print(f"[WS:{self.session_id}] *** ORDER COMPLETED ***")
                    self.memory.complete_order(self.order_id)
            
            # TTS
            t3 = time.time()
            response_audio = tts_engine.synthesize(response_text)
            tts_time = time.time() - t3
            
            total_time = time.time() - start
            latency = order_data.get("latency", {})
            
            await self.ws.send_json({
                "type": "response",
                "text": response_text,
                "audio": base64.b64encode(response_audio).decode('utf-8'),
                "state": self.agent.get_order_summary_dict(self.session_id),
                "order": self.memory.get_order(self.order_id),
                "order_complete": order_data.get("order_complete", False),
                "latency": {
                    "stt_ms": int(stt_time * 1000),
                    "agent_ms": int(agent_time * 1000),
                    "tts_ms": int(tts_time * 1000),
                    "total_ms": int(total_time * 1000),
                    "understand_ms": latency.get("understand_ms", 0),
                    "reason_ms": latency.get("reason_ms", 0),
                    "act_ms": latency.get("act_ms", 0),
                    "generate_ms": latency.get("generate_ms", 0)
                },
                "status": "idle"
            })
            
            print(f"[WS:{self.session_id}] Done: {total_time:.2f}s")
            
        except Exception as e:
            print(f"[WS:{self.session_id}] Error: {e}")
            import traceback
            traceback.print_exc()
            await self.ws.send_json({
                "type": "error",
                "text": "Something went wrong, try again",
                "status": "idle"
            })


@app.websocket("/ws/conversational")
async def websocket_endpoint(websocket: WebSocket):
    """Conversational WebSocket endpoint for ReAct agent"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] === ReAct Agent Connection ===")
    
    # Initialize memory and agent
    memory = MemoryManager(db_path=CONFIG.get("memory", {}).get("session_db", "data/orders.db"))
    order_id = memory.create_order(session_id)
    
    try:
        agent = ReActAgent(config=CONFIG.get("llm", {}))
    except Exception as e:
        print(f"[WS:{session_id}] Agent init error: {e}")
        await websocket.send_json({"type": "error", "text": "Server error"})
        await websocket.close()
        return
    
    # Create processor
    processor = ConversationalProcessor(websocket, session_id, agent, memory, order_id)
    
    # Send greeting
    greeting = "Hey! Welcome to Wingstop, I'm Tasha. What's your name?"
    try:
        audio_bytes = tts_engine.synthesize(greeting)
        await websocket.send_json({
            "type": "greeting",
            "text": greeting,
            "audio": base64.b64encode(audio_bytes).decode('utf-8'),
            "state": agent.get_order_summary_dict(session_id),
            "order": memory.get_order(order_id),
            "status": "idle"
        })
        # Add greeting to memory
        memory.add_turn(session_id, "assistant", greeting)
    except Exception as e:
        print(f"[WS:{session_id}] TTS error: {e}")
    
    try:
        while True:
            try:
                message = await websocket.receive()
            except RuntimeError as e:
                # Client disconnected
                if "disconnect" in str(e).lower():
                    print(f"[WS:{session_id}] Client disconnected")
                    break
                raise
            
            # Handle FastAPI wrapped messages
            if isinstance(message, dict) and message.get("type") == "websocket.receive":
                
                # Handle binary audio
                if "bytes" in message:
                    await processor.process_audio_chunk(message["bytes"])
                
                # Handle commands
                elif "text" in message:
                    import json
                    try:
                        cmd = json.loads(message["text"])
                        
                        if cmd.get("command") == "start_recording":
                            await processor.start_recording()
                        
                        elif cmd.get("command") == "stop_recording":
                            await processor.stop_and_process()
                        
                        elif cmd.get("command") == "reset":
                            agent.reset(session_id)
                            order_id = memory.create_order(session_id)
                            processor.order_id = order_id
                            await websocket.send_json({
                                "type": "reset",
                                "state": agent.get_order_summary_dict(session_id),
                                "status": "idle"
                            })
                    
                    except json.JSONDecodeError:
                        pass
    
    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
    finally:
        # Cleanup
        memory.clear_session(session_id)
        print(f"[WS:{session_id}] === Closed ===\n")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "agent_type": "ReAct"
    }


@app.get("/api/analytics")
async def get_analytics():
    """Get conversation analytics"""
    memory = MemoryManager(db_path=CONFIG.get("memory", {}).get("session_db", "data/orders.db"))
    return memory.get_analytics()


if __name__ == "__main__":
    init_engines()
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
