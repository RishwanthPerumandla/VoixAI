FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

COPY packages/ordering /app/packages/ordering
COPY apps/api /app/apps/api

RUN python -m pip install /app/packages/ordering \
    && python -m pip install /app/apps/api

WORKDIR /app/apps/api

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

