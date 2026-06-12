import os
import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from livekit.api import AccessToken, VideoGrants
from livekit.protocol.agent_dispatch import RoomAgentDispatch
from livekit.protocol.room import RoomConfiguration


API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent.parent
SESSION_CONFIG_DIR = ROOT_DIR / ".voixai" / "session-configs"

load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "apps" / "agent-runtime" / ".env")
load_dotenv(API_DIR / ".env", override=True)

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")


class TokenRequest(BaseModel):
    room_name: str = Field(min_length=1)
    participant_name: str = Field(min_length=1)
    runtime_config: dict[str, object] | None = None


class TokenResponse(BaseModel):
    livekit_url: str
    token: str
    room_name: str


def _session_config_path(room_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in room_name).strip("-")
    return SESSION_CONFIG_DIR / f"{safe_name or 'default-room'}.json"


app = FastAPI(title="VoixAI MVP API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "OK"}


@app.post("/api/livekit/token", response_model=TokenResponse)
async def create_livekit_token(payload: TokenRequest) -> TokenResponse:
    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail=(
                "Realtime transport environment variables are missing. Set LIVEKIT_URL, "
                "LIVEKIT_API_KEY, and LIVEKIT_API_SECRET before requesting tokens."
            ),
        )

    if payload.runtime_config is not None:
        SESSION_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _session_config_path(payload.room_name).write_text(
            json.dumps(payload.runtime_config, indent=2),
            encoding="utf-8",
        )

    identity = f"{payload.participant_name}-{uuid4().hex[:8]}"
    room_config = RoomConfiguration(
        agents=[RoomAgentDispatch(agent_name=AGENT_NAME)]
    )

    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(payload.participant_name)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=payload.room_name,
                can_publish=True,
                can_publish_data=True,
                can_subscribe=True,
            )
        )
        .with_room_config(room_config)
        .to_jwt()
    )

    return TokenResponse(
        livekit_url=LIVEKIT_URL,
        token=token,
        room_name=payload.room_name,
    )
