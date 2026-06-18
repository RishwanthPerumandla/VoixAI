'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, Clock, Phone, ShieldCheck, ShoppingBag } from 'lucide-react';
import { AreaChart, BarPairChart, DonutChart } from '@/components/dashboard/charts';
import {
  Badge,
  EmptyState,
  ErrorState,
  KpiCard,
  Panel,
  SentimentBar,
  SkeletonGrid,
} from '@/components/dashboard/primitives';
import { dashboardApi, usePoll } from '@/lib/dashboard/api';
import { OUTCOME_META, formatDuration, formatPercent, formatTimeAgo } from '@/lib/dashboard/format';

const WINDOWS = [
  { label: '24h', hours: 24 },
  { label: '7d', hours: 24 * 7 },
  { label: '30d', hours: 24 * 30 },
];

export default function OverviewPage() {
  const [windowHours, setWindowHours] = useState(24);

  const overview = usePoll(
    useCallback((signal) => dashboardApi.overview(windowHours, signal), [windowHours]),
    15000,
    [windowHours]
  );
  const recent = usePoll(
    useCallback((signal) => dashboardApi.calls({ limit: 8 }, signal), []),
    15000
  );

  const data = overview.data;

  // Trend vs. the earlier half of the window — a lightweight period-over-period
  // delta so KPIs show direction without a second query.
  const trend = (
    key: 'calls' | 'orders' | 'completed'
  ): { value: string; positive: boolean } | undefined => {
    if (!data || data.series.length < 4) return undefined;
    const mid = Math.floor(data.series.length / 2);
    const first = data.series.slice(0, mid).reduce((s, b) => s + b[key], 0);
    const second = data.series.slice(mid).reduce((s, b) => s + b[key], 0);
    if (first === 0 && second === 0) return undefined;
    const pct = first === 0 ? 100 : Math.round(((second - first) / first) * 100);
    return { value: `${Math.abs(pct)}%`, positive: pct >= 0 };
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[1.7rem] font-semibold tracking-tight">Welcome back 👋</h1>
          <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
            Here&apos;s how your voice agent is performing · refreshes automatically
            {overview.lastUpdated && ` · updated ${formatTimeAgo(overview.lastUpdated / 1000)}`}
          </p>
        </div>
        <div className="flex rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.hours}
              onClick={() => setWindowHours(w.hours)}
              className="rounded-full px-4 py-1.5 text-xs font-medium transition"
              style={
                windowHours === w.hours
                  ? { background: 'var(--voix-accent)', color: 'var(--voix-accent-foreground)' }
                  : { color: 'var(--voix-text-muted)' }
              }
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {overview.error && !data ? (
        <ErrorState message={overview.error} onRetry={overview.refresh} />
      ) : !data ? (
        <SkeletonGrid />
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Calls handled"
              value={data.total_calls}
              delta={trend('calls')}
              icon={<Phone size={16} />}
              hint="Across all channels this window"
              segments={[
                { label: 'Completed', value: data.completed_calls, color: 'var(--voix-success)' },
                { label: 'Live now', value: data.in_progress_calls, color: 'var(--voix-accent)' },
                { label: 'Failed', value: data.failed_calls, color: 'var(--voix-danger)' },
              ]}
            />
            <KpiCard
              label="Containment rate"
              value={formatPercent(data.containment_rate, 1)}
              accent="var(--voix-success)"
              icon={<ShieldCheck size={16} />}
              hint={`${data.transfers} transferred to staff`}
            />
            <KpiCard
              label="Orders placed"
              value={data.orders_placed}
              delta={trend('orders')}
              accent="var(--voix-info)"
              icon={<ShoppingBag size={16} />}
              hint={`${data.revenue_total} captured revenue`}
            />
            <KpiCard
              label="Avg handle time"
              value={formatDuration(data.avg_duration_seconds)}
              accent="var(--voix-warning)"
              icon={<Clock size={16} />}
              hint={`${data.avg_turns} turns per call avg`}
            />
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Panel
              title="Call volume"
              subtitle="Calls received over the selected window"
              className="lg:col-span-2"
            >
              <div className="h-56">
                {data.series.some((s) => s.calls > 0) ? (
                  <AreaChart data={data.series.map((s) => ({ label: s.label, value: s.calls }))} />
                ) : (
                  <EmptyState title="No calls in this window yet" />
                )}
              </div>
              <div className="mt-2 flex justify-between text-[10px] text-[var(--voix-text-muted)]">
                {data.series
                  .filter((_, i) => i % 2 === 0)
                  .map((s) => (
                    <span key={s.start}>{s.label}</span>
                  ))}
              </div>
            </Panel>

            <Panel title="Call outcomes" subtitle="How each conversation resolved">
              {data.total_calls > 0 ? (
                <DonutChart
                  slices={Object.entries(data.outcomes).map(([key, value]) => ({
                    label: OUTCOME_META[key]?.label ?? key,
                    value,
                    color: OUTCOME_META[key]?.color ?? 'var(--voix-text-muted)',
                  }))}
                />
              ) : (
                <EmptyState title="No outcomes yet" />
              )}
            </Panel>
          </div>

          {/* Secondary row */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Panel
              title="Calls vs. orders"
              subtitle="Conversion of conversations into placed orders"
              className="lg:col-span-2"
            >
              <div className="h-52">
                <BarPairChart
                  data={data.series.map((s) => ({ label: s.label, a: s.calls, b: s.orders }))}
                />
              </div>
              <div className="mt-3 flex gap-5 text-xs text-[var(--voix-text-muted)]">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-[var(--voix-accent)]" /> Calls
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-[var(--voix-success)]" /> Orders
                </span>
              </div>
            </Panel>

            <Panel title="Customer sentiment" subtitle="Inferred from conversation tone">
              <div className="space-y-4">
                <div className="flex items-end gap-2">
                  <span className="text-4xl font-semibold">
                    {data.avg_sentiment != null ? Math.round(data.avg_sentiment * 100) : '—'}
                  </span>
                  <span className="mb-1.5 text-sm text-[var(--voix-text-muted)]">
                    / 100 avg score
                  </span>
                </div>
                {(['positive', 'neutral', 'negative'] as const).map((bucket) => {
                  const count = data.sentiment_breakdown[bucket] ?? 0;
                  const total =
                    Object.values(data.sentiment_breakdown).reduce((a, b) => a + b, 0) || 1;
                  const color =
                    bucket === 'positive'
                      ? 'var(--voix-success)'
                      : bucket === 'neutral'
                        ? 'var(--voix-warning)'
                        : 'var(--voix-danger)';
                  return (
                    <div key={bucket}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span className="text-[var(--voix-text-secondary)] capitalize">
                          {bucket}
                        </span>
                        <span className="text-[var(--voix-text-muted)]">{count}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-[var(--voix-bg-subtle)]">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${(count / total) * 100}%`, backgroundColor: color }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          </div>

          {/* Recent calls */}
          <Panel
            title="Recent calls"
            subtitle="Latest conversations across all channels"
            action={
              <Link
                href="/dashboard/calls"
                className="flex items-center gap-1 text-xs font-medium text-[var(--voix-accent)] transition hover:opacity-80"
              >
                View all <ArrowUpRight size={13} />
              </Link>
            }
          >
            {recent.data && recent.data.calls.length > 0 ? (
              <div className="-mx-2 overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse">
                  <thead>
                    <tr className="text-left text-[11px] tracking-wide text-[var(--voix-text-muted)] uppercase">
                      <th className="px-2 py-2 font-medium">Time</th>
                      <th className="px-2 py-2 font-medium">Channel</th>
                      <th className="px-2 py-2 font-medium">Outcome</th>
                      <th className="px-2 py-2 font-medium">Duration</th>
                      <th className="px-2 py-2 font-medium">Sentiment</th>
                      <th className="px-2 py-2 font-medium">Order</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.data.calls.map((call) => {
                      const meta = OUTCOME_META[call.outcome] ?? OUTCOME_META.unknown;
                      return (
                        <tr
                          key={call.call_id}
                          className="border-t border-[var(--voix-border-subtle)] text-sm transition hover:bg-[var(--voix-bg-subtle)]"
                        >
                          <td className="px-2 py-2.5 text-[var(--voix-text-secondary)]">
                            {formatTimeAgo(call.started_at)}
                          </td>
                          <td className="px-2 py-2.5 text-[var(--voix-text-muted)] capitalize">
                            {call.channel || '—'}
                          </td>
                          <td className="px-2 py-2.5">
                            <Badge label={meta.label} color={meta.color} bg={meta.bg} />
                          </td>
                          <td className="px-2 py-2.5 text-[var(--voix-text-secondary)] tabular-nums">
                            {formatDuration(call.duration_seconds)}
                          </td>
                          <td className="px-2 py-2.5">
                            <SentimentBar value={call.sentiment} />
                          </td>
                          <td className="px-2 py-2.5 font-mono text-xs text-[var(--voix-text-muted)]">
                            {call.order_number ?? '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No calls recorded yet"
                hint="Start a session from the live agent, or seed demo data with scripts/seed_dashboard.py"
              />
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
