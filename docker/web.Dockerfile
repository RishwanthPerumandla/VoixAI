FROM node:20-bookworm-slim AS deps

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

COPY apps/web/package.json apps/web/pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

FROM node:20-bookworm-slim AS build

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./

ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

FROM node:20-bookworm-slim AS runtime

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

COPY --from=build /app ./

EXPOSE 3000

CMD ["pnpm", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
