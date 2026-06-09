# MVP Phase 1 Implementation Plan

## Goal

Connect the browser and Python voice agent through LiveKit using a minimal FastAPI token service.

## Delivered in Phase 1

- `apps/api` exposes `POST /api/livekit/token`.
- `apps/api` creates participant tokens with room dispatch for the Python agent.
- `apps/web` requests connection details from `apps/api`.
- `apps/web` joins the fixed MVP room and shows basic connection status.
- `apps/agent-runtime` registers under the shared agent name and can be dispatched into the room.
- Phase 1 environment and setup docs have been updated.

## Not delivered in Phase 1

- Restaurant ordering logic
- Database or persistence
- Analytics
- Admin dashboard
- Production deployment
- Telephony
- POS integrations

## Verification target

- `apps/api` starts locally and returns LiveKit connection details.
- `apps/web` starts and requests tokens from `apps/api`.
- `apps/agent-runtime` starts with valid LiveKit credentials and waits for dispatch.
- The browser can join `voixai-mvp-demo` and wait for the Python agent.

## Next step

Phase 2 should keep the same room connection flow and change the assistant behavior into a short, restaurant-style order-taking assistant.
