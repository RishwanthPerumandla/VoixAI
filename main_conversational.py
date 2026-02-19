"""VoixAI Conversational - Real-time Wingstop ordering with State Machine"""
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
from core.llm_agent_conversational import ConversationalAgent, DialogueState
from core.tts_engine_onnx import TTSEngineONNX
from core.order_manager import OrderManager


# Load config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# Override STT for speed - use tiny.en for fastest transcription
CONFIG["stt"]["model"] = "tiny.en"

app = FastAPI(title="VoixAI - Conversational")
app.mount("/static", StaticFiles(directory="static"), name="static")

stt_engine: STTEngine = None
tts_engine: TTSEngineONNX = None


def init_engines():
    """Initialize shared engines on startup"""
    global stt_engine, tts_engine
    
    stt_config = CONFIG["stt"]
    
    print("[INIT] Loading STT engine (tiny.en - fastest)...")
    stt_engine = STTEngine(
        model_size=stt_config["model"],  # tiny.en for speed
        device=CONFIG["hardware"]["device"],
        compute_type="int8",
        language="en"
    )
    
    print("[INIT] Loading TTS engine (ONNX)...")
    tts_engine = TTSEngineONNX(
        voice=CONFIG["tts"]["voice"],
        speed=1.3  # Faster speed for real-time
    )
    
    print("[INIT] Ready!")


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index.html").read_text(encoding='utf-8')


class AudioProcessor:
    """Handles audio collection with VAD-based auto-detection"""
    
    def __init__(self, websocket, session_id: str, agent, order_manager, order_id: int):
        self.ws = websocket
        self.session_id = session_id
        self.agent = agent
        self.order_manager = order_manager
        self.order_id = order_id
        self.audio_chunks = []
        self.is_recording = False
        
        # Init audio buffer with optimized settings for SPEED
        audio_config = CONFIG.get("audio", {})
        self.audio_buffer = AudioBuffer(
            sample_rate=CONFIG["hardware"]["sample_rate"],
            silence_ms=800,  # Very short silence detection
            vad_threshold=0.25,  # Very sensitive VAD
            min_utterance_ms=400,  # Very short minimum
            normalization=True,
            noise_gate=0.003
        )
    
    async def start_recording(self):
        """Start a new recording session"""
        self.audio_chunks = []
        self.is_recording = True
        self.audio_buffer.reset()
        print(f"[WS:{self.session_id}] Recording STARTED")
        await self.ws.send_json({"type": "status", "status": "recording"})
    
    async def process_audio_chunk(self, chunk_bytes: bytes):
        """Process incoming audio chunk"""
        if not self.is_recording:
            return
        
        # Convert to numpy for storage
        int16_data = np.frombuffer(chunk_bytes, dtype=np.int16)
        float_data = int16_data.astype(np.float32) / 32768.0
        self.audio_chunks.append(float_data)
        
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
        """Process the captured audio"""
        try:
            start = time.time()
            
            # Combine chunks
            full_audio = np.concatenate(self.audio_chunks)
            audio_duration = len(full_audio) / 16000
            print(f"[WS:{self.session_id}] Processing {audio_duration:.2f}s audio")
            
            # STT - Fastest model
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
            
            print(f"[WS:{self.session_id}] Heard: '{user_text}' ({stt_time:.2f}s)")
            self.order_manager.log_turn(self.order_id, "user", user_text)
            
            # LLM - Conversational state machine
            t2 = time.time()
            response_text, order_data = self.agent.process(user_text)
            llm_time = time.time() - t2
            
            print(f"[WS:{self.session_id}] Tasha: '{response_text}'")
            print(f"[WS:{self.session_id}] State: {order_data.get('state', 'unknown')}, Complete: {order_data.get('order_complete', False)}")
            
            # Update order in database
            if order_data:
                self.order_manager.update_order_items(self.order_id, order_data.get("items", []))
                if order_data.get("order_complete"):
                    print(f"[WS:{self.session_id}] *** ORDER COMPLETED ***")
                    self.order_manager.complete_order(self.order_id)
            
            # TTS - Fast ONNX
            t3 = time.time()
            response_audio = tts_engine.synthesize(response_text)
            tts_time = time.time() - t3
            
            total_time = time.time() - start
            
            await self.ws.send_json({
                "type": "response",
                "text": response_text,
                "audio": base64.b64encode(response_audio).decode('utf-8'),
                "state": self.agent.get_order_summary(),
                "order": self.order_manager.get_order(self.order_id),
                "order_complete": order_data.get("order_complete", False) if order_data else False,
                "latency": {
                    "stt_ms": int(stt_time * 1000),
                    "llm_ms": int(llm_time * 1000),
                    "tts_ms": int(tts_time * 1000),
                    "total_ms": int(total_time * 1000)
                },
                "status": "idle"
            })
            
            self.order_manager.log_turn(self.order_id, "assistant", response_text)
            print(f"[WS:{self.session_id}] Done: {total_time:.2f}s")
            
        except Exception as e:
            print(f"[WS:{self.session_id}] Error: {e}")
            await self.ws.send_json({
                "type": "error",
                "text": "Something went wrong, try again",
                "status": "idle"
            })


@app.websocket("/ws/conversational")
async def websocket_endpoint(websocket: WebSocket):
    """Conversational WebSocket endpoint"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] === Conversational Connection ===")
    
    order_manager = OrderManager(db_path=CONFIG["database"]["path"])
    order_id = order_manager.create_order(session_id)
    
    try:
        agent = ConversationalAgent(config=CONFIG["llm"])
    except Exception as e:
        print(f"[WS:{session_id}] Agent init error: {e}")
        await websocket.send_json({"type": "error", "text": "Server error"})
        await websocket.close()
        return
    
    # Create audio processor
    processor = AudioProcessor(websocket, session_id, agent, order_manager, order_id)
    
    # Send greeting
    greeting = "Hey! Welcome to Wingstop! I'm Tasha. How many wings can I get started for you? Bone-in or boneless?"
    try:
        audio_bytes = tts_engine.synthesize(greeting)
        await websocket.send_json({
            "type": "greeting",
            "text": greeting,
            "audio": base64.b64encode(audio_bytes).decode('utf-8'),
            "state": agent.get_order_summary(),
            "order": order_manager.get_order(order_id),
            "status": "idle"
        })
        order_manager.log_turn(order_id, "assistant", greeting)
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
                            agent.reset()
                            order_id = order_manager.create_order(session_id)
                            processor.order_id = order_id
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
    init_engines()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
