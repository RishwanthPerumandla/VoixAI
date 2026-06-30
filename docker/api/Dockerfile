# API app - FastAPI
# Usage: docker build -f docker/api/Dockerfile .

# --- Stage 1: Build ---
FROM python:3.12-slim AS builder
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the shared ordering package first (build context is repo root)
COPY packages/ordering/ ./packages/ordering/
RUN pip install --no-cache-dir ./packages/ordering/

# Copy API app
COPY apps/api/ ./apps/api/

# Install API deps one by one (pip can't resolve local voix-ordering)
WORKDIR /app/apps/api
RUN pip install --no-cache-dir \
    "alembic>=1.13,<2.0" \
    "fastapi>=0.116,<1.0" \
    "livekit-api>=1.0.7,<2.0" \
    "psycopg[binary]>=3.1,<4.0" \
    "python-dotenv>=1.0,<2.0" \
    "sqlalchemy>=2.0,<3.0" \
    "uvicorn>=0.35,<1.0"

# Install the API package itself (skip deps, all already installed)
RUN pip install --no-cache-dir --no-deps .

# --- Stage 2: Production ---
FROM python:3.12-slim AS runner
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY apps/api/ ./apps/api/
COPY packages/ordering/ ./packages/ordering/

WORKDIR /app/apps/api

# Create .voixai directory for SQLite
RUN mkdir -p /app/.voixai

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
