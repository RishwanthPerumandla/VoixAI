'use client';

import { useCallback } from 'react';
import { CheckCircle2, ShieldCheck, Timer, Zap } from 'lucide-react';
import {
  EmptyState,
  ErrorState,
  KpiCard,
  Panel,
  SkeletonGrid,
} from '@/components/dashboard/primitives';
import { dashboardApi, usePoll } from '@/lib/dashboard/api';
import { formatDuration, formatPercent } from '@/lib/dashboard/format';

const STATUS_COLORS: Record<string, string> = {
  operational: 'var(--voix-success)',
  degraded: 'var(--voix-warning)',
  down: 'var(--voix-danger)',
};

const STATUS_LABELS: Record<string, string> = {
  operational: 'Operational',
  degraded: 'Degraded',
  down: 'Down',
};

const RELIABILITY_GUARANTEES = [
  {
    icon: ShieldCheck,
    title: 'Idempotent order placement',
    detail:
      'Every order submit is keyed; retries and network hiccups replay the original order instead of double-charging the customer.',
  },
  {
    icon: CheckCircle2,
    title: 'Backend is the source of truth',
    detail:
      'The agent can never confirm an order the backend has not validated and persisted — the submit gate re-runs server-side.',
  },
  {
    icon: Timer,
    title: 'Durable persistence',
    detail:
      'Orders and call telemetry are written to a WAL-backed store and survive restarts; no in-memory-only state for placed orders.',
  },
  {
    icon: Zap,
    title: 'Best-effort telemetry',
    detail:
      'Call recording is fully decoupled — a telemetry failure can never slow down or break a live customer call.',
  },
];

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400)
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

export default function ObservabilityPage() {
  const health = usePoll(
    useCallback((signal) => dashboardApi.health(signal), []),
    10000
  );

  const data = health.data;
  const uptimePct = data ? Math.max(0, 1 - data.error_rate) : 1;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Observability</h1>
          <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
            Live system health and the reliability guarantees behind every call.
          </p>
        </div>
        {data && (
          <div
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold"
            style={{
              color: STATUS_COLORS[data.status],
              backgroundColor: `color-mix(in oklab, ${STATUS_COLORS[data.status]} 14%, transparent)`,
            }}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: STATUS_COLORS[data.status] }}
            />
            All systems {STATUS_LABELS[data.status].toLowerCase()}
          </div>
        )}
      </div>

      {health.error && !data ? (
        <ErrorState message={health.error} onRetry={health.refresh} />
      ) : !data ? (
        <SkeletonGrid />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Call success"
              value={formatPercent(uptimePct, 2)}
              accent="var(--voix-success)"
              hint={`${data.failed_calls} failed of ${data.total_calls} (7d)`}
            />
            <KpiCard
              label="Service uptime"
              value={formatUptime(data.uptime_seconds)}
              hint="Since last API start"
            />
            <KpiCard
              label="P95 handle time"
              value={formatDuration(data.p95_duration_seconds)}
              accent="var(--voix-warning)"
              hint={`${formatDuration(data.avg_duration_seconds)} average`}
            />
            <KpiCard
              label="Guardrail flags"
              value={data.guardrail_violations}
              accent={data.guardrail_violations > 0 ? 'var(--voix-warning)' : 'var(--voix-success)'}
              hint="Caught assistant responses (7d)"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel title="Component health" subtitle="Polled every 10 seconds">
              {data.components.length === 0 ? (
                <EmptyState title="No components reported" />
              ) : (
                <div className="space-y-2.5">
                  {data.components.map((c) => (
                    <div
                      key={c.name}
                      className="flex items-center justify-between rounded-xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-4 py-3"
                    >
                      <div>
                        <p className="text-sm font-medium text-[var(--voix-text-primary)]">
                          {c.name}
                        </p>
                        <p className="text-xs text-[var(--voix-text-muted)]">{c.detail}</p>
                      </div>
                      <span
                        className="flex items-center gap-1.5 text-xs font-semibold"
                        style={{ color: STATUS_COLORS[c.status] }}
                      >
                        <span
                          className="h-1.5 w-1.5 rounded-full"
                          style={{ background: STATUS_COLORS[c.status] }}
                        />
                        {STATUS_LABELS[c.status]}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Panel>

            <Panel title="Reliability guarantees" subtitle="How this system stays trustworthy">
              <div className="space-y-3">
                {RELIABILITY_GUARANTEES.map((g) => {
                  const Icon = g.icon;
                  return (
                    <div key={g.title} className="flex gap-3">
                      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--voix-accent)]/12">
                        <Icon size={16} style={{ color: 'var(--voix-accent)' }} />
                      </span>
                      <div>
                        <p className="text-sm font-medium text-[var(--voix-text-primary)]">
                          {g.title}
                        </p>
                        <p className="text-xs leading-relaxed text-[var(--voix-text-muted)]">
                          {g.detail}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
