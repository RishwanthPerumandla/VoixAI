FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git gcc g++ python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY packages/ordering /app/packages/ordering
COPY apps/agent-runtime /app/apps/agent-runtime

RUN python -m pip install /app/packages/ordering \
    && python -m pip install /app/apps/agent-runtime \
    && python -m livekit.agents download-files

WORKDIR /app/apps/agent-runtime

CMD ["python", "src/agent.py", "start"]

