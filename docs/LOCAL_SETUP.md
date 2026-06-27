# Local Setup

## Prerequisites

- Node.js 18 or newer
- `pnpm`
- Python 3.10 or newer
- Docker Desktop (or Docker Engine + Compose v2) for the containerized path
- LiveKit Cloud or a self-hosted LiveKit server

## Docker Quick Start

If you want the fastest reproducible local run on a new machine, use Docker:

1. Copy the root env file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Add at least one provider key to `.env`:

   - `OPENAI_API_KEY` for `openai_realtime`
   - `GOOGLE_API_KEY` for `gemini_live`

3. Start the full stack from the repo root:

   ```powershell
   docker compose up --build
   ```

4. Open `http://localhost:3000`.

What the Docker stack includes:

- a local LiveKit server on `ws://localhost:7880`
- the FastAPI service on `http://localhost:8000`
- the Python agent runtime connected to the internal Docker LiveKit hostname
- the Next.js frontend on `http://localhost:3000`

Important Docker notes:

- `docker compose` overrides the LiveKit connection details internally, so you do not need a separate hosted LiveKit project just to boot the local stack
- the browser still needs a real model provider key to have an actual voice conversation
- the API persists SQLite data in the `voixai-data` Docker volume
- room-scoped fallback files are shared through the `voixai-shared` Docker volume

To stop the stack:

```powershell
docker compose down
```

To stop it and remove persisted local Docker data:

```powershell
docker compose down -v
```

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

Docker note:

- for `docker compose`, these are overridden automatically to the bundled local LiveKit service
- for manual non-Docker runs, set them to your LiveKit Cloud or self-hosted server values

Optional but recommended:

- `AGENT_NAME`
- `ALLOWED_ORIGINS`
- `ALLOWED_ORIGIN_REGEX`

Local CORS note:

- if you leave both unset, the API accepts `http://localhost:*` and `http://127.0.0.1:*` during local development so browser preflight still works when Next.js moves off port `3000`

Worker provider defaults:

- `VOICE_PROVIDER=classic` keeps the existing Deepgram -> OpenAI -> Cartesia pipeline
- `VOICE_PROVIDER=openai_realtime` switches the worker to OpenAI Realtime through LiveKit
- `VOICE_PROVIDER=gemini_live` switches the worker to Gemini Live through LiveKit
- keep `OPENAI_API_KEY` out of `apps/web/.env.local`
- keep `GOOGLE_API_KEY` out of `apps/web/.env.local`

Frontend mode defaults:

- `NEXT_PUBLIC_DEFAULT_VOICE_MODE=openai_realtime` starts the UI in OpenAI Realtime by default
- `NEXT_PUBLIC_DEFAULT_VOICE_MODE=gemini_live` starts the UI in Gemini Live by default
- if omitted, the frontend can still derive its default mode from server-side `VOICE_PROVIDER`

## 2. Install local dependencies

> The ordering domain (menu, pricing, validation, order state, order state
> machine) lives in the shared `packages/ordering` package and is the single
> source of truth used by both `apps/api` and `apps/agent-runtime`. Each Python
> venv installs it editable with `python -m pip install -e ../../packages/ordering`
> (shown in the steps below). For the agent runtime, `uv sync` also picks it up
> via `[tool.uv.sources]` in `apps/agent-runtime/pyproject.toml`.

Web:

```powershell
cd apps/web
corepack pnpm install
```

Agent runtime:

```powershell
cd apps/agent-runtime
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -e ../../packages/ordering
python src/agent.py download-files
```

Note:

- `apps/agent-runtime` pulls `livekit-plugins-google` from the `charan632-dev/agents`
  fork (it adds forced-`generate_reply` support for Gemini 3.1 so the model greets
  in its own voice). The `pip install -e .` above should install it from the
  pinned git URL, but if a stock PyPI build slipped in (which causes a duplicate
  Gemini greeting in two voices), force the fork and verify:

  ```powershell
  .\.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps "livekit-plugins-google @ git+https://github.com/charan632-dev/agents.git#subdirectory=livekit-plugins/livekit-plugins-google"
  # confirm the fork is installed (must show the git url):
  Get-Content .\.venv\Lib\site-packages\livekit_plugins_google-*.dist-info\direct_url.json
  ```

API:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -e ../../packages/ordering
```

Database:

- leave `DATABASE_URL` empty to use SQLite at `.voixai/voixai.db`
- set `DATABASE_URL` to a Postgres URL for dev/prod, for example `postgresql+psycopg://voixai:voixai@localhost:5432/voixai`
- after installing API dependencies, run migrations and seed the demo store/menu:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
cd ..\..
.\scripts\seed-api-db.ps1
```

## 3. Start everything with one command

From the repo root:

```powershell
.\scripts\start-all.ps1
```

This opens three PowerShell windows for:

- `apps/api`
- `apps/agent-runtime`
- `apps/web`

All three **hot-reload on code changes** — no manual restart needed:

- `apps/web` via Next.js fast refresh
- `apps/api` via `uvicorn --reload`, watching both `apps/api` and the shared
  `packages/ordering/src`
- `apps/agent-runtime` via `watchfiles`, restarting the worker on changes in
  both `src` and `packages/ordering/src`

Because the shared `packages/ordering` domain is watched by both Python
services, editing the menu/pricing/validation/state-machine code restarts the
API and the worker automatically.

If you only want to confirm the launch commands without starting them:

```powershell
.\scripts\start-all.ps1 -DryRun
```

## 4. Start the web app manually

```powershell
cd apps/web
corepack pnpm install
corepack pnpm dev
```

Open `http://localhost:3000`.

## 5. Start the agent runtime manually

We are using `venv`, not `uv`.

```powershell
cd apps/agent-runtime
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -e ../../packages/ordering
python src/agent.py download-files
python src/agent.py dev
```

To enable OpenAI Realtime, set this in `apps/agent-runtime/.env` before starting the worker:

```text
VOICE_PROVIDER=openai_realtime
OPENAI_API_KEY=sk-...
OPENAI_REALTIME_MODEL=gpt-realtime
OPENAI_REALTIME_VOICE=alloy
```

To enable Gemini Live, set:

```text
VOICE_PROVIDER=gemini_live
GOOGLE_API_KEY=...
GOOGLE_REALTIME_MODEL=gemini-3.1-flash-live-preview
GOOGLE_REALTIME_VOICE=Achird
```

Gemini Live note:

- `gemini-3.1-flash-live-preview` greets in its own voice via native `generate_reply(...)`, which requires the `charan632-dev/agents` Google plugin fork (it adds forced-`generate_reply` support for Gemini 3.1). If the stock PyPI plugin is installed instead, you get a duplicate greeting in two different voices. Ensure the fork is installed (see below).
- `Achird` is the recommended default for Wingstop ordering. If you want a warmer hospitality feel, try `Sulafat`. If you want a calmer, firmer tone, try `Kore`.

## 6. Start the API manually

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -e ../../packages/ordering
python -m alembic -c alembic.ini upgrade head
python -m seed
python -m uvicorn main:app --reload --port 8000
```

## 7. Check the health endpoint

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response body:

```json
{"status":"OK"}
```

## 8. Check token generation

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

## 9. Demo run order

1. Run `.\scripts\start-all.ps1` from the repo root.
2. Open `http://localhost:3000`.
3. Choose a voice mode if needed.
4. Click `Start voice order`.
5. Allow microphone access when prompted.
6. Speak with the restaurant agent.
7. End the order and start another one if you want to test switching modes.

Important:

- the app now uses a fresh room per new order
- that prevents stale session config from reusing the previous order's mode

## 10. Verifying the active mode

Do not rely only on worker startup log lines like:

- `Voice provider: openai_realtime`

Those reflect env defaults and prewarm behavior.

The authoritative per-session log line is:

- `Voice runtime profile selected`

Examples:

- Classic session:
  - `voice_provider: classic`
  - `voice_engine: pipeline`
- OpenAI Realtime session:
  - `voice_provider: openai_realtime`
  - `voice_engine: openai_realtime`
- Gemini Live session:
  - `voice_provider: gemini_live`
  - `voice_engine: gemini_live`

## 11. Watching latency

The worker logs include timing hints for each turn. Watch the terminal running:

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

In `openai_realtime` mode, classic STT/LLM/TTS stage metrics are not emitted because the realtime model handles the combined audio stack.

In `gemini_live` mode, classic STT/LLM/TTS stage metrics are also not emitted because the realtime model handles the combined audio stack.

## 12. Demo tips

- Use the session indicators to verify `Connected`, `Listening`, and `Speaking`.
- Use the transcript panel to see what the system heard and replied with.
- If the browser is connected but the agent does not join, compare `AGENT_NAME` in the API and worker environments.
- If mode selection looks wrong, inspect the session-level `Voice runtime profile selected` log.
- If latency feels high, say one short sentence at a time so turn detection has a clearer end of speech.
