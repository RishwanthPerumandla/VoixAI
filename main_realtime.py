"""VoixAI Realtime - Optimized for accuracy and reliability"""
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
from typing import Dict, Any, Optional

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

app = FastAPI(title="VoixAI - Realtime Optimized")
app.mount("/static", StaticFiles(directory="static"), name="static")

stt_engine: STTEngine = None
tts_engine: TTSEngineONNX = None


def init_engines():
    """Initialize shared engines on startup"""
    global stt_engine, tts_engine
    
    stt_config = CONFIG["stt"]
    
    print("[INIT] Loading STT engine...")
    stt_engine = STTEngine(
        model_size=stt_config["model"],
        device=CONFIG["hardware"]["device"],
        compute_type=stt_config["compute_type"],
        language=stt_config["language"]
    )
    
    print("[INIT] Loading TTS engine (ONNX)...")
    tts_engine = TTSEngineONNX(
        voice="af_bella",
        speed=1.0
    )
    
    print("[INIT] Ready!")


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index_realtime.html").read_text(encoding='utf-8')


class AudioProcessor:
    """Handles audio collection with retry mechanism"""
    
    def __init__(self, websocket, session_id: str, agent, order_manager, order_id: int):
        self.ws = websocket
        self.session_id = session_id
        self.agent = agent
        self.order_manager = order_manager
        self.order_id = order_id
        self.audio_chunks = []
        self.is_recording = False
        
        # Init audio buffer with config settings
        audio_config = CONFIG.get("audio", {})
        self.audio_buffer = AudioBuffer(
            sample_rate=CONFIG["hardware"]["sample_rate"],
            silence_ms=audio_config.get("silence_duration_ms", 1500),
            vad_threshold=audio_config.get("vad_threshold", 0.4),
            min_utterance_ms=audio_config.get("min_utterance_ms", 800),
            normalization=audio_config.get("normalization", True),
            noise_gate=audio_config.get("noise_gate", 0.01)
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
        
        # Convert to numpy
        int16_data = np.frombuffer(chunk_bytes, dtype=np.int16)
        float_data = int16_data.astype(np.float32) / 32768.0
        self.audio_chunks.append(float_data)
        
        # Check chunk level for debugging
        if len(self.audio_chunks) == 1:
            max_val = np.max(np.abs(int16_data))
            print(f"[WS:{self.session_id}] First chunk: {len(chunk_bytes)} bytes, max={max_val}")
        
        # Feed to VAD
        utterance = self.audio_buffer.add_chunk(chunk_bytes)
        
        # If VAD detected end of speech, auto-process
        if utterance is not None:
            print(f"[WS:{self.session_id}] VAD auto-detected end of speech")
            await self.stop_and_process()
    
    async def stop_and_process(self):
        """Stop recording and process with retry logic"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        chunk_count = len(self.audio_chunks)
        
        print(f"[WS:{self.session_id}] Recording STOPPED, {chunk_count} chunks")
        await self.ws.send_json({"type": "status", "status": "processing"})
        
        if chunk_count < 5:
            await self.ws.send_json({
                "type": "error",
                "text": "Too short - hold button longer and speak clearly",
                "status": "idle"
            })
            return
        
        # Process with retry
        await self._process_with_retry()
    
    async def _process_with_retry(self, max_retries: int = 2):
        """Process audio with STT retry logic"""
        for attempt in range(max_retries):
            try:
                start = time.time()
                
                # Combine chunks
                full_audio = np.concatenate(self.audio_chunks)
                audio_duration = len(full_audio) / 16000
                print(f"[WS:{self.session_id}] Processing {audio_duration:.2f}s audio (attempt {attempt + 1})")
                
                # STT
                t1 = time.time()
                user_text = stt_engine.transcribe(full_audio)
                stt_time = time.time() - t1
                
                # Validate STT result
                if not user_text or len(user_text.strip()) < 3:
                    if attempt < max_retries - 1:
                        print(f"[WS:{self.session_id}] STT empty, retrying...")
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        await self.ws.send_json({
                            "type": "error",
                            "text": "Couldn't hear you clearly - please speak louder and closer to the mic",
                            "status": "idle"
                        })
                        return
                
                # Check for gibberish (repeated words, nonsense)
                words = user_text.lower().split()
                if len(words) > 3:
                    # Check for excessive repetition
                    unique_ratio = len(set(words)) / len(words)
                    if unique_ratio < 0.3:  # Too much repetition
                        if attempt < max_retries - 1:
                            print(f"[WS:{self.session_id}] Gibberish detected, retrying...")
                            await asyncio.sleep(0.1)
                            continue
                
                print(f"[WS:{self.session_id}] Heard: '{user_text}' ({stt_time:.2f}s)")
                self.order_manager.log_turn(self.order_id, "user", user_text)
                
                # LLM
                t2 = time.time()
                response_text, order_data = self.agent.process(user_text)
                llm_time = time.time() - t2
                
                print(f"[WS:{self.session_id}] Tasha: '{response_text}'")
                
                # Update order
                if order_data and order_data.get("items"):
                    self.order_manager.update_order_items(self.order_id, self.agent.order_items)
                if self.agent.state == ConversationState.CLOSING:
                    self.order_manager.complete_order(self.order_id)
                
                # TTS
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
                return
                
            except Exception as e:
                print(f"[WS:{self.session_id}] Error: {e}")
                if attempt < max_retries - 1:
                    continue
                await self.ws.send_json({
                    "type": "error",
                    "text": "Something went wrong, try again",
                    "status": "idle"
                })


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """Realtime WebSocket with auto-detection and retry"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())[:8]
    print(f"\n[WS:{session_id}] === Realtime Connection ===")
    
    order_manager = OrderManager(db_path=CONFIG["database"]["path"])
    order_id = order_manager.create_order(session_id)
    
    try:
        agent = ConversationAgent(config=CONFIG["llm"])
    except Exception as e:
        await websocket.send_json({"type": "error", "text": "Server error"})
        await websocket.close()
        return
    
    # Create audio processor
    processor = AudioProcessor(websocket, session_id, agent, order_manager, order_id)
    
    # Send greeting
    greeting = "Hey! Welcome to Wingstop. I'm Tasha. What can I getcha?"
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
            message = await websocket.receive()
            
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
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
