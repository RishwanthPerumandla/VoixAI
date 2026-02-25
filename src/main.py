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
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

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

# Create FastAPI app
app = FastAPI(
    title="VoixAI v3.0",
    description="AI Voice Agent for Restaurant Ordering",
    version="3.0.0"
)

# Global pipeline instance
pipeline = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main web interface"""
    return get_html_client()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "environment": settings.environment,
        "pipeline_running": pipeline.is_running() if pipeline else False
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
    
    try:
        # Handle WebSocket through pipeline transport
        await pipeline.handle_websocket(websocket)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))


def get_html_client():
    """Return HTML client for testing"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VoixAI v3.0 - Voice Ordering</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                color: #eee;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: rgba(0,0,0,0.3);
                padding: 20px;
                text-align: center;
            }
            
            .header h1 {
                color: #e94560;
                font-size: 2rem;
                margin-bottom: 5px;
            }
            
            .status {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(78, 204, 163, 0.2);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.9rem;
            }
            
            .status-dot {
                width: 8px;
                height: 8px;
                background: #4ecca3;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .container {
                flex: 1;
                display: flex;
                flex-direction: column;
                max-width: 800px;
                margin: 0 auto;
                width: 100%;
                padding: 20px;
            }
            
            .chat-area {
                flex: 1;
                background: rgba(0,0,0,0.2);
                border-radius: 15px;
                padding: 20px;
                overflow-y: auto;
                margin-bottom: 20px;
                min-height: 300px;
            }
            
            .message {
                margin-bottom: 15px;
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .message-user {
                text-align: right;
            }
            
            .message-bot {
                text-align: left;
            }
            
            .message-bubble {
                display: inline-block;
                padding: 12px 18px;
                border-radius: 20px;
                max-width: 70%;
                word-wrap: break-word;
            }
            
            .message-user .message-bubble {
                background: #e94560;
                color: white;
                border-bottom-right-radius: 5px;
            }
            
            .message-bot .message-bubble {
                background: rgba(255,255,255,0.1);
                color: #eee;
                border-bottom-left-radius: 5px;
            }
            
            .input-area {
                display: flex;
                gap: 10px;
            }
            
            input[type="text"] {
                flex: 1;
                padding: 15px 20px;
                border: none;
                border-radius: 30px;
                background: rgba(255,255,255,0.1);
                color: #eee;
                font-size: 1rem;
                outline: none;
            }
            
            input[type="text"]::placeholder {
                color: rgba(255,255,255,0.5);
            }
            
            button {
                padding: 15px 30px;
                border: none;
                border-radius: 30px;
                background: #e94560;
                color: white;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            button:hover {
                background: #c73e54;
                transform: scale(1.05);
            }
            
            button:disabled {
                background: #666;
                cursor: not-allowed;
                transform: none;
            }
            
            .connection-status {
                text-align: center;
                padding: 10px;
                font-size: 0.85rem;
                color: rgba(255,255,255,0.6);
            }
            
            .latency {
                font-size: 0.8rem;
                color: rgba(255,255,255,0.5);
                margin-top: 5px;
            }
            
            .info-box {
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-size: 0.9rem;
            }
            
            .info-box h3 {
                color: #e94560;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>VoixAI v3.0</h1>
            <div class="status">
                <span class="status-dot"></span>
                <span>Online</span>
            </div>
        </div>
        
        <div class="container">
            <div class="info-box">
                <h3>Welcome to VoixAI!</h3>
                <p>I'm Tasha, your Wingstop cashier. Type your order below or use voice (coming soon).</p>
                <p><strong>Try saying:</strong> "Hi, I'd like to order some wings"</p>
            </div>
            
            <div class="chat-area" id="chatArea">
                <div class="message message-bot">
                    <div class="message-bubble">
                        Hey there! Welcome to Wingstop! I'm Tasha. What can I get for you today?
                    </div>
                </div>
            </div>
            
            <div class="connection-status" id="connectionStatus">Connecting...</div>
            
            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Type your message..." disabled>
                <button id="sendBtn" disabled>Send</button>
            </div>
        </div>
        
        <script>
            const chatArea = document.getElementById('chatArea');
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            const connectionStatus = document.getElementById('connectionStatus');
            
            let ws = null;
            let sessionId = null;
            
            // Connect to WebSocket
            function connect() {
                const wsUrl = `ws://${window.location.host}/ws`;
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    console.log('WebSocket connected');
                    connectionStatus.textContent = 'Connected';
                    messageInput.disabled = false;
                    sendBtn.disabled = false;
                    messageInput.focus();
                    
                    // Start conversation
                    ws.send(JSON.stringify({
                        type: 'start_conversation'
                    }));
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('Received:', data);
                    
                    if (data.type === 'system' && data.event === 'connected') {
                        sessionId = data.session_id;
                        console.log('Session:', sessionId);
                    }
                    else if (data.type === 'bot_text') {
                        addMessage(data.content, 'bot', data.latency_ms);
                    }
                    else if (data.type === 'error') {
                        addMessage(data.content, 'bot');
                    }
                };
                
                ws.onclose = () => {
                    console.log('WebSocket closed');
                    connectionStatus.textContent = 'Disconnected - Reconnecting...';
                    messageInput.disabled = true;
                    sendBtn.disabled = true;
                    
                    // Reconnect after 3 seconds
                    setTimeout(connect, 3000);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    connectionStatus.textContent = 'Connection error';
                };
            }
            
            // Add message to chat
            function addMessage(text, sender, latency = null) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message message-${sender}`;
                
                let latencyText = '';
                if (latency) {
                    latencyText = `<div class="latency">${latency.toFixed(0)}ms</div>`;
                }
                
                messageDiv.innerHTML = `
                    <div class="message-bubble">
                        ${escapeHtml(text)}
                        ${latencyText}
                    </div>
                `;
                
                chatArea.appendChild(messageDiv);
                chatArea.scrollTop = chatArea.scrollHeight;
            }
            
            // Escape HTML
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Send message
            function sendMessage() {
                const text = messageInput.value.trim();
                if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
                
                addMessage(text, 'user');
                
                ws.send(JSON.stringify({
                    type: 'text',
                    content: text
                }));
                
                messageInput.value = '';
            }
            
            // Event listeners
            sendBtn.addEventListener('click', sendMessage);
            
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
            
            // Connect on load
            connect();
        </script>
    </body>
    </html>
    """


@app.on_event("startup")
async def startup():
    """Startup event"""
    global pipeline
    
    settings.ensure_data_dir()
    
    # Initialize pipeline
    # Use mock mode if API keys are not set
    use_mock = not (settings.deepgram_api_key and settings.cartesia_api_key)
    
    if use_mock:
        logger.info("Starting in MOCK mode (API keys not set)")
        pipeline = MockPipeline()
    else:
        logger.info("Starting in PRODUCTION mode")
        pipeline = ConversationPipeline()
    
    # Start pipeline
    if not await pipeline.start():
        logger.error("Failed to start pipeline")
        raise Exception("Pipeline startup failed")
    
    logger.info(
        "VoixAI v3.0 started",
        environment=settings.environment,
        mock_mode=use_mock
    )


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event"""
    global pipeline
    
    if pipeline:
        await pipeline.stop()
    
    logger.info("VoixAI v3.0 shutdown")


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
