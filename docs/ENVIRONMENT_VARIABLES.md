# Environment Variables

## Root `.env.example`

- `LIVEKIT_URL`: shared LiveKit websocket URL
- `LIVEKIT_API_KEY`: shared LiveKit API key
- `LIVEKIT_API_SECRET`: shared LiveKit API secret
- `AGENT_NAME`: shared agent dispatch name, default `my-agent`
- `WEB_PORT`: local web port, default `3000`
- `API_PORT`: local API port, default `8000`

## `apps/web/.env.example`

- `NEXT_PUBLIC_API_BASE_URL`: URL for the FastAPI service, default `http://127.0.0.1:8000`
- `NEXT_PUBLIC_LIVEKIT_ROOM_NAME`: default room name, default `voixai-mvp-demo`
- `NEXT_PUBLIC_PARTICIPANT_NAME`: browser participant name, default `web-user`
- `NEXT_PUBLIC_AGENT_NAME`: expected dispatched agent name, default `my-agent`
- `NEXT_PUBLIC_CONN_DETAILS_ENDPOINT`: optional sandbox connection-details endpoint
- `NEXT_PUBLIC_APP_CONFIG_ENDPOINT`: optional app config endpoint from the starter
- `SANDBOX_ID`: optional LiveKit sandbox identifier from the starter

## `apps/agent-runtime/.env.example`

- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `AGENT_NAME`: worker registration name, default `my-agent`

## `apps/api/.env.example`

- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `AGENT_NAME`: agent dispatch target, default `my-agent`
- `API_HOST`: API bind host
- `API_PORT`: API bind port
- `ALLOWED_ORIGINS`: comma-separated browser origins allowed to call the API

## Phase 1 note

Phase 1 uses these variables to mint browser participant tokens in `apps/api`, connect the web client to the shared room, and dispatch the Python agent by name.
