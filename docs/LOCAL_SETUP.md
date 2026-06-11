# Local Setup

## Prerequisites

- Node.js 18 or newer
- `pnpm`
- Python 3.10 or newer
- LiveKit Cloud or a self-hosted LiveKit server

## 1. Configure environment files

Copy the example files:

```powershell
Copy-Item .env.example .env
Copy-Item apps\web\.env.example apps\web\.env.local
Copy-Item apps\agent-runtime\.env.example apps\agent-runtime\.env
Copy-Item apps\api\.env.example apps\api\.env
```

Required LiveKit variables:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

Optional but recommended:

- `AGENT_NAME`
- `ALLOWED_ORIGINS`

Worker provider defaults:

- `VOICE_PROVIDER=classic` keeps the existing Deepgram -> OpenAI -> Cartesia pipeline
- `VOICE_PROVIDER=openai_realtime` switches only the Python worker to OpenAI Realtime through LiveKit
- Keep `OPENAI_API_KEY` out of `apps/web/.env.local`

## 2. Start the web app

```powershell
cd apps/web
corepack pnpm install
corepack pnpm dev
```

Open `http://localhost:3000`.

## 3. Start the agent runtime

We are using `venv`, not `uv`.

```powershell
cd apps/agent-runtime
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python src/agent.py download-files
python src/agent.py dev
```

Classic mode stays the default. To enable OpenAI Realtime, set this in `apps/agent-runtime/.env` before starting the worker:

```text
VOICE_PROVIDER=openai_realtime
OPENAI_API_KEY=sk-...
OPENAI_REALTIME_MODEL=gpt-realtime
OPENAI_REALTIME_VOICE=alloy
```

## 4. Start the API

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m uvicorn main:app --reload --port 8000
```

## 5. Check the health endpoint

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response body:

```json
{"status":"OK"}
```

## 6. Check token generation

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/livekit/token `
  -H "Content-Type: application/json" `
  -d "{\"room_name\":\"voixai-mvp-demo\",\"participant_name\":\"web-user\"}"
```

Expected response shape:

```json
{
  "livekit_url": "wss://...",
  "token": "...",
  "room_name": "voixai-mvp-demo"
}
```

## 7. Demo run order

1. Start `apps/api`.
2. Start `apps/agent-runtime`.
3. Start `apps/web`.
4. Open `http://localhost:3000`.
5. Click `Start Conversation`.
6. Allow microphone access when prompted.
7. Speak with the restaurant agent.
8. Ask for a recap.
9. Confirm the order to generate the mock order number.

## 8. Watching latency

The worker logs now include timing hints for each turn. Watch the terminal running:

```powershell
python src/agent.py dev
```

Look for lines like:

```text
User turn latency metrics: transcription_delay=... end_of_turn_delay=... on_user_turn_completed_delay=...
Assistant turn latency metrics: llm_ttft=... tts_ttfb=... e2e_latency=...
```

Quick interpretation:

- `end_of_turn_delay` is the pause after you stop speaking
- `transcription_delay` is STT-related delay
- `llm_ttft` is how long the LLM takes to start responding
- `tts_ttfb` is how long TTS takes to begin audio
- `e2e_latency` is the overall assistant response latency

In `openai_realtime` mode, the worker logs that classic per-stage STT/LLM/TTS latency metrics are not emitted because the realtime model handles the combined audio stack.

## 9. Demo tips

- Use the session indicators to verify `Connected`, `Listening`, and `Speaking`.
- Use the transcript panel to see what the system heard and replied with.
- If the browser is connected but the agent does not join, compare `AGENT_NAME` in the API and worker environments.
- If latency feels high, say one short sentence at a time so turn detection has a clearer end of speech.
