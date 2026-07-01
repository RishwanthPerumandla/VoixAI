# Agent Runtime - Python LiveKit Voice Agent
# Usage: docker build -f docker/agent-runtime/Dockerfile .

# --- Stage 1: Build ---
FROM python:3.12-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ordering/ ./packages/ordering/
RUN pip install --no-cache-dir ./packages/ordering/

COPY apps/agent-runtime/ ./apps/agent-runtime/

WORKDIR /app/apps/agent-runtime
RUN pip install --no-cache-dir \
    "livekit-agents[silero,turn-detector,openai]>=1.5.17" \
    "livekit-plugins-ai-coustics~=0.2" \
    python-dotenv

RUN pip install --no-cache-dir \
    "livekit-plugins-google @ git+https://github.com/charan632-dev/agents.git#subdirectory=livekit-plugins/livekit-plugins-google"

RUN pip install --no-cache-dir --no-deps .

# --- Stage 2: Production ---
FROM python:3.12-slim AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY apps/agent-runtime/src/ ./apps/agent-runtime/src/
COPY packages/ordering/ ./packages/ordering/
COPY apps/api/data/ ./apps/api/data/

ENV VOIXAI_CATALOG_PATH=/app/apps/api/data/wingstop_demo_catalog.json

WORKDIR /app/apps/agent-runtime

RUN python src/agent.py download-files || true

EXPOSE 8080

CMD ["python", "src/agent.py", "start"]
