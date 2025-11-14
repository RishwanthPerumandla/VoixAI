from fastapi import FastAPI
from routers import voice, order
from utils.logger import log

app = FastAPI(title="VoixAI — Local Voice Ordering MVP")

@app.on_event("startup")
async def startup():
    log("🚀 VoixAI Server Started")

app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(order.router, prefix="/orders", tags=["orders"])
