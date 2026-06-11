# Environment Variables

## Root `.env.example`

The current local demo path is `VOICE_ENGINE=pipeline`. Realtime-related
variables are still listed because the worker code keeps those experimental
paths, but the UI is currently centered on the classic pipeline flow.

- `LIVEKIT_URL`: shared LiveKit websocket URL
- `LIVEKIT_API_KEY`: shared LiveKit API key
- `LIVEKIT_API_SECRET`: shared LiveKit API secret
- `AGENT_NAME`: shared agent dispatch name, default `my-agent`
- `VOICE_ENGINE`: runtime path, one of `pipeline`, `openai_realtime`, `openai_realtime_text`, `gemini_live`, `gemini_live_text`
- `LLM_MODEL`: pipeline LLM model, default `openai/gpt-5.3-chat-latest`
- `STT_MODEL`: pipeline speech-to-text model, default `deepgram/flux-general`
- `STT_LANGUAGE`: pipeline speech-to-text language, default `en`
- `TTS_MODEL`: text-to-speech model, default `cartesia/sonic-3`
- `TTS_SPEED`: voice playback speed multiplier, default `1.08`
- `OPENAI_REALTIME_MODEL`: OpenAI realtime model, default `gpt-realtime-2`
- `OPENAI_REALTIME_VOICE`: OpenAI realtime voice, default `marin`
- `OPENAI_REALTIME_EAGERNESS`: OpenAI semantic VAD eagerness, default `medium`
- `GOOGLE_REALTIME_MODEL`: Gemini Live model, default `gemini-2.5-flash`
- `GOOGLE_REALTIME_VOICE`: Gemini Live voice, default `Puck`
- `REALTIME_TEMPERATURE`: realtime model temperature, default `0.6`
- `REALTIME_ENABLE_AFFECTIVE_DIALOG`: Gemini native-audio affective dialog toggle, default `false`
- `REALTIME_ENABLE_PROACTIVITY`: Gemini native-audio proactive audio toggle, default `false`
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

For the most reliable local setup, keep `VOICE_ENGINE=pipeline`,
`STT_MODEL=deepgram/flux-general`, and `STT_LANGUAGE=en`.

- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `AGENT_NAME`: worker registration name, default `my-agent`
- `VOICE_ENGINE`: runtime path, one of `pipeline`, `openai_realtime`, `openai_realtime_text`, `gemini_live`, `gemini_live_text`
- `LLM_MODEL`: pipeline LLM model, default `openai/gpt-5.3-chat-latest`
- `STT_MODEL`: pipeline speech-to-text model, default `deepgram/flux-general`
- `STT_LANGUAGE`: pipeline speech-to-text language, default `en`
- `TTS_MODEL`: text-to-speech model, default `cartesia/sonic-3`
- `TTS_SPEED`: voice playback speed multiplier, default `1.08`
- `OPENAI_REALTIME_MODEL`: OpenAI realtime model, default `gpt-realtime-2`
- `OPENAI_REALTIME_VOICE`: OpenAI realtime voice, default `marin`
- `OPENAI_REALTIME_EAGERNESS`: OpenAI semantic VAD eagerness, default `medium`
- `GOOGLE_REALTIME_MODEL`: Gemini Live model, default `gemini-2.5-flash`
- `GOOGLE_REALTIME_VOICE`: Gemini Live voice, default `Puck`
- `REALTIME_TEMPERATURE`: realtime model temperature, default `0.6`
- `REALTIME_ENABLE_AFFECTIVE_DIALOG`: Gemini native-audio affective dialog toggle, default `false`
- `REALTIME_ENABLE_PROACTIVITY`: Gemini native-audio proactive audio toggle, default `false`

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
