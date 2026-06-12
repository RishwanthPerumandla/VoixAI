# OpenAI Realtime

OpenAI Realtime is an optional worker mode for the VoixAI MVP.

The stable default is still the classic LiveKit pipeline:

- Deepgram STT
- OpenAI text generation
- Cartesia TTS

The browser and API architecture do not change when you enable OpenAI Realtime. The web app still joins a LiveKit room, the API still mints the LiveKit token, and the Python worker still joins the same room through LiveKit agent dispatch.

## Enable it

Set these values in `apps/agent-runtime/.env`:

```text
VOICE_PROVIDER=openai_realtime
OPENAI_API_KEY=sk-...
OPENAI_REALTIME_MODEL=gpt-realtime
OPENAI_REALTIME_VOICE=alloy
```

Then start the worker as usual:

```powershell
cd apps/agent-runtime
.\.venv\Scripts\Activate.ps1
python src/agent.py dev
```

## Important notes

- Do not place `OPENAI_API_KEY` in `apps/web/.env.local`.
- `apps/api` does not need `OPENAI_API_KEY` for `POST /api/livekit/token`.
- The browser is still not connecting directly to OpenAI in this phase.
- No `/api/openai/realtime/session` endpoint or ephemeral OpenAI browser token flow was added.

## Startup logs

When realtime mode is active, the worker logs:

- `Voice provider: openai_realtime`
- `OpenAI Realtime model: gpt-realtime`
- `OpenAI Realtime voice: alloy`

It also logs that classic per-stage STT, LLM, and TTS latency metrics are not emitted in realtime mode because the realtime model handles the combined audio stack.

## Behavioral scope

The worker keeps the same restaurant persona and tool-backed order flow in both modes:

- greet naturally
- take a food order
- support simple corrections
- recap the order
- generate a mock `VX-####` confirmation number

This is still a demo. The worker does not claim real POS, payment, or order submission integration.
