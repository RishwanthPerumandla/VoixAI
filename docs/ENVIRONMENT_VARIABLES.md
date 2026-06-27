# Environment Variables

## Root `.env.example`

The root env file is shared local-development configuration for the API and worker.

- `LIVEKIT_URL`: shared LiveKit websocket URL
- `LIVEKIT_API_KEY`: shared LiveKit API key
- `LIVEKIT_API_SECRET`: shared LiveKit API secret
- `OPENAI_API_KEY`: required for OpenAI Realtime; never place this in `apps/web/.env.local`
- `GOOGLE_API_KEY`: required for Gemini Live; never place this in `apps/web/.env.local`
- `AGENT_NAME`: shared agent dispatch name, default `my-agent`
- `VOICE_PROVIDER`: worker runtime mode, `classic`, `openai_realtime`, or `gemini_live`
- `LLM_MODEL`: pipeline LLM model, default `openai/gpt-5.3-chat-latest`
- `STT_MODEL`: pipeline speech-to-text model, default `deepgram/flux-general`
- `STT_LANGUAGE`: pipeline speech-to-text language, default `en`
- `TTS_MODEL`: text-to-speech model, default `cartesia/sonic-3`
- `TTS_SPEED`: voice playback speed multiplier, default `1.08`
- `OPENAI_REALTIME_MODEL`: OpenAI Realtime model, default `gpt-realtime`
- `OPENAI_REALTIME_VOICE`: OpenAI Realtime voice, default `alloy`
- `OPENAI_REALTIME_EAGERNESS`: OpenAI semantic VAD eagerness, default `medium`
- `GOOGLE_REALTIME_MODEL`: Gemini Live model, default `gemini-3.1-flash-live-preview`
- `GOOGLE_REALTIME_VOICE`: Gemini Live voice, default `Achird`
- `REALTIME_TEMPERATURE`: realtime model temperature, default `0.6`
- `REALTIME_ENABLE_AFFECTIVE_DIALOG`: Google realtime feature flag
- `REALTIME_ENABLE_PROACTIVITY`: Google realtime feature flag
- `WEB_PORT`: local web port, default `3000`
- `API_PORT`: local API port, default `8000`
- `VOIXAI_API_URL`: agent telemetry endpoint, default `http://127.0.0.1:8000`
- `DATABASE_URL`: optional SQLAlchemy database URL for `apps/api`; leave empty for SQLite or set a Postgres URL in dev/prod
- `VOIXAI_DB_PATH`: SQLite fallback path when `DATABASE_URL` is unset, default `.voixai/voixai.db`

Docker note:

- `compose.yaml` overrides the LiveKit connection values per service so the local Docker stack can use the bundled `livekit` container
- in Docker, the API returns `ws://localhost:7880` to the browser, while the worker connects internally to `ws://livekit:7880`
- in manual non-Docker runs, the root `LIVEKIT_*` values are used directly

## `apps/web/.env.example`

- `NEXT_PUBLIC_API_BASE_URL`: URL for the FastAPI service, default `http://127.0.0.1:8000`
- `NEXT_PUBLIC_LIVEKIT_ROOM_NAME`: base room name, default `voixai-mvp-demo`
- `NEXT_PUBLIC_PARTICIPANT_NAME`: browser participant name, default `web-user`
- `NEXT_PUBLIC_AGENT_NAME`: expected dispatched agent name, default `my-agent`
- `NEXT_PUBLIC_DEFAULT_VOICE_MODE`: optional frontend default mode, for example `classic`, `openai_realtime`, or `gemini_live`
- `NEXT_PUBLIC_CONN_DETAILS_ENDPOINT`: optional sandbox connection-details endpoint
- `NEXT_PUBLIC_APP_CONFIG_ENDPOINT`: optional app config endpoint from the starter
- `SANDBOX_ID`: optional LiveKit sandbox identifier from the starter

Important note:

- the frontend now creates a fresh room name per new order by suffixing the base room name at runtime
- `NEXT_PUBLIC_LIVEKIT_ROOM_NAME` is the base prefix, not the exact room reused forever

## `apps/agent-runtime/.env.example`

The runtime can start in classic, OpenAI Realtime, or Gemini Live depending on env defaults and room-scoped session config.

- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `OPENAI_API_KEY`: required for OpenAI Realtime
- `GOOGLE_API_KEY`: required for Gemini Live
- `AGENT_NAME`: worker registration name, default `my-agent`
- `VOIXAI_API_BASE_URL`: backend base URL for menu lookup, validation, and pricing, default `http://127.0.0.1:8000`
- `VOIXAI_API_URL`: backend base URL for call telemetry/dashboard writes, default `http://127.0.0.1:8000`
- `VOICE_PROVIDER`: worker runtime mode, `classic`, `openai_realtime`, or `gemini_live`
- `LLM_MODEL`: pipeline LLM model, default `openai/gpt-5.3-chat-latest`
- `STT_MODEL`: pipeline speech-to-text model, default `deepgram/flux-general`
- `STT_LANGUAGE`: pipeline speech-to-text language, default `en`
- `TTS_MODEL`: text-to-speech model, default `cartesia/sonic-3`
- `TTS_SPEED`: voice playback speed multiplier, default `1.08`
- `OPENAI_REALTIME_MODEL`: OpenAI Realtime model, default `gpt-realtime`
- `OPENAI_REALTIME_VOICE`: OpenAI Realtime voice, default `alloy`
- `OPENAI_REALTIME_EAGERNESS`: OpenAI semantic VAD eagerness, default `medium`
- `GOOGLE_REALTIME_MODEL`: Gemini Live model, default `gemini-3.1-flash-live-preview`
- `GOOGLE_REALTIME_VOICE`: Gemini Live voice, default `Achird`
- `REALTIME_TEMPERATURE`: realtime model temperature, default `0.6`
- `REALTIME_ENABLE_AFFECTIVE_DIALOG`: Google realtime feature flag
- `REALTIME_ENABLE_PROACTIVITY`: Google realtime feature flag

## Provider notes

- `classic`: uses Deepgram STT, OpenAI text generation, and Cartesia TTS through the existing LiveKit pipeline path
- `openai_realtime`: uses the LiveKit OpenAI Realtime plugin inside the Python worker while the browser still connects only to LiveKit
- `gemini_live`: uses the LiveKit Google realtime plugin inside the Python worker while the browser still connects only to LiveKit
- `gemini_live` on `gemini-3.1-flash-live-preview` greets and prompts in its own voice via native `generate_reply(...)`; no separate worker TTS voice is used (requires the `charan632-dev/agents` Google plugin fork)
- `Achird` is the default Gemini Live voice for Wingstop ordering because it sounds the most friendly and approachable for fast-food calls
- good alternatives are `Sulafat` for a warmer hospitality tone and `Kore` for a calmer, firmer tone
- `OPENAI_API_KEY` belongs only in the worker or shared server-side env files
- `GOOGLE_API_KEY` belongs only in the worker or shared server-side env files
- `apps/api` does not need `OPENAI_API_KEY` for the existing token endpoint
- `apps/api` does not need `GOOGLE_API_KEY` for the existing token endpoint

## Runtime config precedence

The final session runtime mode is not determined only by worker startup env.

Current precedence is:

1. frontend-selected runtime config sent to `POST /api/livekit/token`
2. room-scoped config written by `apps/api`
3. env defaults used by `apps/agent-runtime`

That means the authoritative session-level log line is:

- `Voice runtime profile selected`

and not just the worker startup provider log.

## `apps/api/.env.example`

- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `AGENT_NAME`: agent dispatch target, default `my-agent`
- `API_HOST`: API bind host
- `API_PORT`: API bind port
- `ALLOWED_ORIGINS`: comma-separated browser origins allowed to call the API
- `ALLOWED_ORIGIN_REGEX`: optional regex allowlist for browser origins
- `DATABASE_URL`: SQLAlchemy URL for the API database. Use Postgres for dev/prod, for example `postgresql+psycopg://voixai:voixai@localhost:5432/voixai`
- `VOIXAI_DATABASE_URL`: optional VoixAI-specific alias for `DATABASE_URL`
- `VOIXAI_DB_PATH`: optional SQLite path used only when `DATABASE_URL`/`VOIXAI_DATABASE_URL` are unset; defaults to `.voixai/voixai.db`

Local development note:

- if neither `ALLOWED_ORIGINS` nor `ALLOWED_ORIGIN_REGEX` is set, the API accepts loopback browser origins matching `localhost` or `127.0.0.1` on any port so Next.js can fall forward from `3000` to `3001+` without breaking CORS preflight

## Current API note

The API uses these variables to mint browser participant tokens, persist room-scoped runtime config, connect the web client to a fresh room for each new order, and dispatch the Python agent by name.

For the current Wingstop scenario, the API also serves the backend-backed menu lookup, order validation, pricing, and Phase 1 persistence endpoints used by the agent runtime.

Phase 1 persistence note:

- `apps/api` uses SQLAlchemy models and Alembic migrations.
- SQLite remains the deterministic offline/test path.
- Postgres is selected by setting `DATABASE_URL`; no provider API keys are needed for persistence tests.
