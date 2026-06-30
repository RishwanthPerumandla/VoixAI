# Web app - Next.js 15
# Usage: docker build -f docker/web/Dockerfile .

# --- Stage 1: Dependencies ---
FROM node:22-slim AS deps
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
WORKDIR /app

# Copy only package files first for layer caching
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# --- Stage 2: Build ---
FROM node:22-slim AS builder
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .

# Build arguments for Next.js public env vars
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_LIVEKIT_ROOM_NAME=voixai-mvp-demo
ARG NEXT_PUBLIC_PARTICIPANT_NAME=web-user
ARG NEXT_PUBLIC_DEFAULT_VOICE_MODE=openai_realtime
ARG NEXT_PUBLIC_AGENT_NAME=my-agent

# Set environment variables for build
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_LIVEKIT_ROOM_NAME=$NEXT_PUBLIC_LIVEKIT_ROOM_NAME
ENV NEXT_PUBLIC_PARTICIPANT_NAME=$NEXT_PUBLIC_PARTICIPANT_NAME
ENV NEXT_PUBLIC_DEFAULT_VOICE_MODE=$NEXT_PUBLIC_DEFAULT_VOICE_MODE
ENV NEXT_PUBLIC_AGENT_NAME=$NEXT_PUBLIC_AGENT_NAME

# Next.js collects anonymous telemetry - disable during build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN pnpm build

# --- Stage 3: Production ---
FROM node:22-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
