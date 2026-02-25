"""
VoixAI v3.0 - Main Entry Point
Local development server with Pipecat pipeline
"""

import asyncio
import os
import sys
from pathlib import Path

# Windows OpenMP fix
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from src.config import settings

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

# Create FastAPI app
app = FastAPI(
    title="VoixAI v3.0",
    description="AI Voice Agent for Restaurant Ordering",
    version="3.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main web interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VoixAI v3.0</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #1a1a2e;
                color: #eee;
            }
            h1 { color: #e94560; }
            .status { 
                padding: 10px; 
                border-radius: 5px; 
                margin: 10px 0;
                background: #16213e;
            }
            .online { color: #4ecca3; }
            button {
                background: #e94560;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover { background: #c73e54; }
            button:disabled { background: #666; }
        </style>
    </head>
    <body>
        <h1>🎙️ VoixAI v3.0</h1>
        <div class="status">
            <p><strong>Status:</strong> <span class="online">● Online</span></p>
            <p><strong>Version:</strong> 3.0.0 (Local Development)</p>
            <p><strong>Pipeline:</strong> Daily.co → Deepgram → Groq → Cartesia</p>
        </div>
        <p>WebSocket endpoint: <code>ws://localhost:8000/ws</code></p>
        <p>Daily.co integration coming in Phase 1.2...</p>
        <br>
        <button onclick="alert('Daily.co integration coming soon!')">
            Start Conversation
        </button>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "environment": settings.environment
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for voice conversations"""
    await websocket.accept()
    session_id = None
    
    try:
        logger.info("WebSocket connection established")
        
        # TODO: Phase 1.2 - Integrate Pipecat pipeline here
        # For now, just echo back for testing
        
        while True:
            message = await websocket.receive_text()
            logger.debug("Received message", message=message)
            
            # Echo for testing
            await websocket.send_text(f"Echo: {message}")
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        if session_id:
            logger.info("Cleaning up session", session_id=session_id)


@app.on_event("startup")
async def startup():
    """Startup event"""
    settings.ensure_data_dir()
    logger.info(
        "VoixAI v3.0 starting up",
        environment=settings.environment,
        log_level=settings.log_level
    )


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event"""
    logger.info("VoixAI v3.0 shutting down")


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
