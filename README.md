# VoixAI Restaurant Voice Agent Demo

VoixAI is a small LiveKit-based MVP for learning how a browser voice agent works end to end. The current repo is a restaurant ordering demo: a web user joins a LiveKit room, a Python voice agent joins the same room, and the conversation flows through speech detection, transcription, language generation, and speech synthesis.

This is still an MVP. It is intentionally focused on local development, demo behavior, and architecture learning rather than production infrastructure.

## What Is Implemented

- `apps/web`: Next.js LiveKit client UI for joining a conversation, showing connection state, transcript, and demo panels.
- `apps/api`: FastAPI service with `GET /health` and `POST /api/livekit/token`.
- `apps/agent-runtime`: Python LiveKit agent with a restaurant persona, in-memory order state, mock totals, and mock order confirmation.
- Phase 0 through Phase 6 documentation in [docs/PHASE_STATUS.md](/d:/Personal/Projects/VoixAI/docs/PHASE_STATUS.md).

## What Is Not Implemented

- Production deployment
- Database persistence
- Real POS integration
- Payments
- Telephony
- Admin dashboard
- Analytics pipeline
- Durable order storage across sessions

## Repo Structure

```text
VoixAI/
  apps/
    web/              Next.js + LiveKit browser client
    api/              FastAPI token + health service
    agent-runtime/    Python LiveKit voice agent
  docs/
    MVP.MD
    MVP_IMPLEMENTATION_PLAN.md
    LOCAL_SETUP.md
    ENVIRONMENT_VARIABLES.md
    INTERRUPTION_TESTING.md
    DEMO_SCRIPT.md
    PHASE_STATUS.md
    CODEX_RULES.md
  README.md
```

## Architecture

The current voice path is:

1. The browser joins a LiveKit room using a token from `apps/api`.
2. The token request includes a LiveKit agent dispatch for `AGENT_NAME`.
3. The Python worker registers that same `AGENT_NAME` and is assigned into the room.
4. Inside the worker:
   - `silero` VAD helps detect speech boundaries
   - LiveKit turn detection decides when the user turn is complete
   - Deepgram STT transcribes speech
   - OpenAI LLM generates the assistant reply
   - Cartesia TTS synthesizes the reply audio
5. The web app plays the returned audio and renders transcript/status UI.

The stable local path is the classic STT -> LLM -> TTS pipeline. The worker
still contains experimental realtime provider code, but the UI and local token
flow are currently aligned around the classic pipeline so the demo stays
predictable.

## Current Demo Features

- Start and end a browser conversation
- LiveKit room join through the API
- Restaurant-style greeting and ordering flow
- In-memory order memory for one session
- Simple corrections to items, drink, and order details
- Mock order recap with demo pricing
- Mock order confirmation with `VX-####` order number
- Transcript and order-summary driven UI panels
- Worker debug logs for speech state, corrections, and latency

## Environment Variables

You need the same LiveKit project credentials for the API and the worker:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

Optional:

- `AGENT_NAME`
- `ALLOWED_ORIGINS`
- `STT_LANGUAGE`

Copy the example files first:

```powershell
Copy-Item .env.example .env
Copy-Item apps\web\.env.example apps\web\.env.local
Copy-Item apps\api\.env.example apps\api\.env
Copy-Item apps\agent-runtime\.env.example apps\agent-runtime\.env
```

The API loads env values from:

1. root `.env`
2. `apps/agent-runtime/.env`
3. `apps/api/.env`

`apps/api/.env` wins if the same variable exists in multiple places.

## Prerequisites

- Node.js 18+
- `pnpm`
- Python 3.10+
- A LiveKit server or LiveKit Cloud project
- Microphone access in the browser

## Running The Project

We are using Python `venv`, not `uv`.

### 1. Start the web app

```powershell
cd apps/web
corepack pnpm install
corepack pnpm dev
```

The web app runs at `http://localhost:3000`.

### 2. Start the API

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m uvicorn main:app --reload --port 8000
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"OK"}
```

### 3. Start the agent runtime

```powershell
cd apps/agent-runtime
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python src/agent.py download-files
python src/agent.py dev
```

### 4. Start the conversation

1. Open `http://localhost:3000`
2. Click `Start Conversation`
3. Allow microphone access
4. Speak to the restaurant agent
5. Click `End Conversation` when done

## Quick Troubleshooting

If the browser says it is waiting for the agent:

- Confirm the API and worker use the same `LIVEKIT_URL`
- Confirm both use the same `AGENT_NAME`
- Confirm the worker logs `registered worker`
- Confirm the API token request succeeds
- Confirm the worker starts a session for the same room name

If the worker says `LIVEKIT_URL` is missing:

- Make sure `apps/agent-runtime/.env` exists
- Make sure you started the worker from `apps/agent-runtime`
- Make sure `.env` contains real values, not blanks

If the worker crashes with a Deepgram language mismatch:

- Set `STT_LANGUAGE=en` in `apps/agent-runtime/.env`
- Keep `STT_MODEL=deepgram/flux-general` unless you intentionally change providers

## Understanding The Delay

The delay you hear is usually not just one thing. In this stack it is the sum of:

1. `VAD / turn detection`
   The system waits long enough to decide you finished speaking.
2. `STT`
   Your audio is sent to Deepgram and turned into text.
3. `LLM`
   The text is sent to OpenAI and the agent waits for the first generated tokens.
4. `TTS`
   The reply text is sent to Cartesia and the browser waits for audio to start.
5. `Network + playback`
   LiveKit transport and browser playback add a little more time.

So the user experience is usually:

`you stop speaking -> end of turn detected -> transcript ready -> LLM starts answering -> TTS starts streaming audio -> you hear the voice`

## Where To See STT, LLM, and TTS Timing

The worker now logs per-turn latency in [apps/agent-runtime/src/agent.py](/d:/Personal/Projects/VoixAI/apps/agent-runtime/src/agent.py).

When you run:

```powershell
python src/agent.py dev
```

look for logs like:

```text
User turn latency metrics: transcription_delay=0.42s end_of_turn_delay=0.78s on_user_turn_completed_delay=0.81s
Assistant turn latency metrics: llm_ttft=0.64s tts_ttfb=0.31s e2e_latency=1.86s started_speaking_at=... stopped_speaking_at=...
```

How to read them:

- `transcription_delay`: how long it took to get the transcript after speech
- `end_of_turn_delay`: how long turn detection waited after you stopped
- `llm_ttft`: LLM time to first token
- `tts_ttfb`: TTS time to first audio byte
- `e2e_latency`: overall latency for the assistant turn

If `end_of_turn_delay` is the big number, the wait is mostly turn detection.
If `llm_ttft` is the big number, the wait is mostly the model.
If `tts_ttfb` is the big number, the wait is mostly speech synthesis.

## Current Limitations

- Order state is in memory only and resets when the session or worker ends.
- The order summary and final order panels are transcript-driven UI helpers, not a direct realtime state sync.
- The web UI now surfaces live latency cards, but the worker logs are still the source of truth for raw per-turn timing.
- The demo depends on external providers for STT, LLM, and TTS, so network and provider latency will vary.

## Future Upgrades

- Add a dedicated latency panel in the web app for STT, LLM, TTS, and e2e timing
- Stream structured order state from the worker to the UI instead of inferring from transcript text
- Persist mock orders in a small database
- Add better correction handling and clearer recap logic
- Support multiple rooms and participant sessions
- Add observability dashboards for latency, interruptions, and provider health
- Add production-safe token auth and environment separation
- Reintroduce provider comparisons only after the classic pipeline path stays stable

## Useful Docs

- [docs/LOCAL_SETUP.md](/d:/Personal/Projects/VoixAI/docs/LOCAL_SETUP.md)
- [docs/ENVIRONMENT_VARIABLES.md](/d:/Personal/Projects/VoixAI/docs/ENVIRONMENT_VARIABLES.md)
- [docs/PHASE_STATUS.md](/d:/Personal/Projects/VoixAI/docs/PHASE_STATUS.md)
- [docs/INTERRUPTION_TESTING.md](/d:/Personal/Projects/VoixAI/docs/INTERRUPTION_TESTING.md)
- [docs/DEMO_SCRIPT.md](/d:/Personal/Projects/VoixAI/docs/DEMO_SCRIPT.md)
