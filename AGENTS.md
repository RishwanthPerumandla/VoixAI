# AGENTS.md

## Repo structure

Three apps under `apps/` + one shared Python package:

| Path | What | Run command |
|------|------|-------------|
| `apps/web` | Next.js 15 frontend | `corepack pnpm dev` |
| `apps/api` | FastAPI service | `uvicorn main:app --reload --port 8000` |
| `apps/agent-runtime` | Python LiveKit agent | `python src/agent.py dev` |
| `packages/ordering` | Shared ordering domain (`voix_ordering`) | imported by api + runtime |

The shared `packages/ordering` package is the single source of truth for menu, pricing, validation, order state, and the order state machine. It has **zero** LiveKit dependency. Both Python apps install it editable.

`apps/agent-runtime/AGENTS.md` has LiveKit-specific agent guidance — defer to it when working in that directory.

## Quick start

```powershell
# Full stack via Docker (easiest)
Copy-Item .env.example .env
# add at least one provider key to .env
make up

# Or manual per-app (see docs/LOCAL_SETUP.md)
.\scripts\start-all.ps1
```

## Package managers

- **web:** `pnpm` (v9.15.9, via `corepack pnpm`)
- **agent-runtime:** `uv` (preferred, prod) or `pip` + `venv` (local dev). Docker uses `pip`.
- **api:** `pip` + `venv`

## Docker

The Docker Compose setup includes:
- `livekit` — Local LiveKit WebRTC server (bundled)
- `api` — FastAPI backend service (runs migrations + seeds on startup)
- `agent-runtime` — Python LiveKit voice agent
- `web` — Next.js frontend

Key commands:
- `make up` — Build and start all services
- `make down` — Stop all services
- `make logs` — Tail logs from all services
- `make seed` — Seed demo data (first time only)
- `make clean` — Remove containers, volumes, and images

The Docker stack overrides LiveKit connection details internally — no hosted LiveKit needed. Provider keys (`OPENAI_API_KEY`, `GOOGLE_API_KEY`) must be set in `.env` before running.

## Tests

| What | Command (from repo root) |
|------|-----------------|
| Agent runtime tests | `apps/agent-runtime/.venv/Scripts/python.exe -m pytest apps/agent-runtime/tests -q` |
| Reliability suite | `apps/agent-runtime/.venv/Scripts/python.exe -m pytest apps/agent-runtime/tests/reliability -q` |
| API tests | `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q` |
| Web typecheck | `cd apps/web && corepack pnpm exec tsc --noEmit` |
| Web build check | `cd apps/web && corepack pnpm exec next build --no-lint` |

No browser-level E2E tests.

## Lint / format

- **web:** `corepack pnpm lint` (ESLint), `corepack pnpm format:check` (Prettier)
- **agent-runtime:** `uv run ruff check` / `uv run ruff format` (line-length=88, double quotes, target py39)
- **api:** no lint/format configured

## Architecture notes

- Browser → API (`POST /api/livekit/token`) → LiveKit room → agent-runtime joins
- Voice modes: `classic` (Deepgram→OpenAI→Cartesia), `openai_realtime`, `gemini_live`
- Runtime config precedence: frontend payload > room-scoped file > env defaults
- Telemetry published on LiveKit data channel `voixai.telemetry`
- Fresh room per order (frontend timestamps base room name)
- Three voice paths all go through the same shared intent router + FSM (`conversation_core/`)

## Edge cases / gotchas

- `apps/agent-runtime` pins `livekit-plugins-google` to a **Git fork** (`charan632-dev/agents`) — stock PyPI breaks Gemini greetings (duplicate voice). Verify the fork is installed when debugging Gemini issues.
- `yarl<1.24` pinned in pyproject.toml — yarl 1.24.1 ships only cp310 wheel.
- Docker stack overrides LiveKit vars (`ws://livekit:7880`, devkey/secret) — `.env` values are ignored at runtime.
- Agent entrypoint is `src/agent.py` — referenced in both Dockerfiles and the dev start command.
- Hot-reload for Python apps uses `watchfiles` — must pass both `src` and `packages/ordering/src` as watched directories.
- The API token endpoint has no auth or rate limiting (known debt).
- `.voixai/` is gitignored (holds local SQLite DB and session configs).
- Frontend env vars must be `NEXT_PUBLIC_*`. Provider keys (`OPENAI_API_KEY`, `GOOGLE_API_KEY`) must never go in `apps/web/.env.local`.
