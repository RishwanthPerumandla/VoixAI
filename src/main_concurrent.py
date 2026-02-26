"""
VoixAI v3.0 - Concurrent Main Entry Point
Supports multiple simultaneous customer sessions
"""

import os
import sys
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager

from src.config import settings
from src.api.websocket_concurrent import (
    get_websocket_endpoint, 
    shutdown_websocket,
    ConcurrentWebSocketEndpoint
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("[Server] Starting VoixAI v3.0 (Concurrent Mode)")
    ws_endpoint = await get_websocket_endpoint()
    print("[Server] WebSocket endpoint initialized")
    
    yield
    
    # Shutdown
    await shutdown_websocket()
    print("[Server] Shutdown complete")


app = FastAPI(
    title="VoixAI v3.0 - Concurrent",
    version="3.0.0",
    description="Multi-customer voice ordering system"
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.router.lifespan_context = lifespan


@app.get("/")
async def root():
    """Serve main page"""
    return FileResponse("static/index.html")


@app.get("/dashboard")
async def dashboard_page():
    """Serve dashboard page"""
    return FileResponse("static/dashboard.html")


@app.get("/health")
async def health():
    """Health check endpoint"""
    ws_endpoint = await get_websocket_endpoint()
    stats = await ws_endpoint.get_global_stats()
    
    return {
        "status": "healthy",
        "mode": "concurrent",
        "active_sessions": stats["active_sessions"],
        "total_sessions": stats["total_sessions"]
    }


@app.get("/api/dashboard")
async def dashboard():
    """Get dashboard data for all active sessions"""
    ws_endpoint = await get_websocket_endpoint()
    return await ws_endpoint.get_dashboard_data()


@app.get("/api/stats")
async def stats():
    """Get global statistics"""
    ws_endpoint = await get_websocket_endpoint()
    return await ws_endpoint.get_global_stats()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint - each connection gets its own isolated session
    Supports multiple simultaneous customers (one per tab)
    """
    ws_endpoint = await get_websocket_endpoint()
    await ws_endpoint.handle_connection(websocket)


# Legacy endpoints for compatibility
@app.post("/daily/create-room")
async def create_daily_room():
    """Create a Daily.co room (legacy)"""
    return {"status": "not_implemented", "message": "Use WebSocket endpoint instead"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
