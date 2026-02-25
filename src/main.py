"""
VoixAI v3.0 - Main Entry Point
"""

import os
import sys
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
import base64
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from contextlib import asynccontextmanager

from src.config import settings
from src.pipeline.conversation_pipeline import ConversationPipeline, MockPipeline
from src.audio_utils import convert_audio_to_pcm

app = FastAPI(title="VoixAI v3.0", version="3.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global pipeline
pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    
    use_real = bool(settings.deepgram_api_key)
    if not use_real:
        pipeline = MockPipeline()
    else:
        pipeline = ConversationPipeline(use_mock_stt=False, use_mock_tts=False)
    
    await pipeline.start()
    print(f"[Server] Started with {'Real' if use_real else 'Mock'} APIs")
    
    yield
    
    await pipeline.stop()
    print("[Server] Shutdown")

app.router.lifespan_context = lifespan


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "real_stt": bool(settings.deepgram_api_key),
        "real_tts": bool(settings.cartesia_api_key)
    }


@app.post("/daily/create-room")
async def create_daily_room():
    """Create a Daily.co room for WebRTC audio"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {settings.daily_api_key}"}
            data = {
                "privacy": "public",
                "properties": {
                    "start_audio_off": False,
                    "start_video_off": True,
                    "enable_screenshare": False
                }
            }
            
            async with session.post(
                "https://api.daily.co/v1/rooms",
                headers=headers,
                json=data
            ) as resp:
                if resp.status == 200:
                    room_data = await resp.json()
                    return {"url": room_data["url"], "name": room_data["name"]}
                else:
                    error = await resp.text()
                    print(f"[Daily] Error creating room: {error}")
                    return JSONResponse(
                        status_code=500,
                        content={"error": "Failed to create room"}
                    )
    except Exception as e:
        print(f"[Daily] Exception: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")
    
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
            if msg_type == "start_conversation":
                session_id = f"session-{asyncio.get_event_loop().time()}"
                await websocket.send_json({
                    "type": "system",
                    "event": "session_started",
                    "session_id": session_id
                })
                
            elif msg_type == "audio":
                # Handle audio from client
                audio_b64 = message.get("data")
                if audio_b64 and session_id:
                    try:
                        print("[WS] Received audio, processing...")
                        
                        # Decode base64 audio
                        audio_data = base64.b64decode(audio_b64)
                        print(f"[WS] Audio size: {len(audio_data)} bytes")
                        
                        # Convert to PCM
                        pcm_audio = convert_audio_to_pcm(audio_data)
                        print(f"[WS] PCM size: {len(pcm_audio)} bytes")
                        
                        # Send to Deepgram for transcription
                        if hasattr(pipeline.stt, 'connection') and pipeline.stt.connection:
                            # Send audio chunk
                            await pipeline.stt.connection.send(pcm_audio)
                            print("[WS] Sent to Deepgram")
                            
                            # Wait for transcript (simplified - in production use callback)
                            await asyncio.sleep(2)
                            
                            transcript = pipeline.stt.get_final_transcript()
                            if transcript:
                                print(f"[WS] Transcript: '{transcript}'")
                                pipeline.stt.clear_buffer()
                                
                                # Show user transcript
                                await websocket.send_json({
                                    "type": "user_transcript",
                                    "content": transcript
                                })
                                
                                # Process through agent
                                import time
                                start = time.time()
                                response = await pipeline.agent.process(transcript, session_id)
                                latency = (time.time() - start) * 1000
                                
                                # Send response
                                await websocket.send_json({
                                    "type": "bot_text",
                                    "content": response,
                                    "latency_ms": latency
                                })
                                
                                # Generate TTS audio
                                if settings.cartesia_api_key:
                                    try:
                                        audio_response = await pipeline.tts.synthesize(response)
                                        if audio_response:
                                            await websocket.send_json({
                                                "type": "bot_audio",
                                                "data": base64.b64encode(audio_response).decode()
                                            })
                                    except Exception as e:
                                        print(f"[WS] TTS error: {e}")
                            else:
                                await websocket.send_json({
                                    "type": "error",
                                    "content": "I couldn't hear that. Please try again."
                                })
                        else:
                            # Fallback: use text mode
                            await websocket.send_json({
                                "type": "error",
                                "content": "Voice processing unavailable. Please type."
                            })
                            
                    except Exception as e:
                        print(f"[WS] Audio processing error: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "content": "Error processing audio. Please try again."
                        })
                        
            elif msg_type == "text":
                text = message.get("content", "")
                if text and session_id:
                    print(f"[WS] User: '{text}'")
                    
                    import time
                    start = time.time()
                    response = await pipeline.agent.process(text, session_id)
                    latency = (time.time() - start) * 1000
                    
                    print(f"[WS] Bot: '{response}' ({latency:.0f}ms)")
                    
                    await websocket.send_json({
                        "type": "bot_text",
                        "content": response,
                        "latency_ms": latency
                    })
                    
    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.port, reload=True)
