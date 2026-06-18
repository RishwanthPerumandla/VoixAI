'use client';

import { useCallback, useEffect, useState } from 'react';
import { Search, X } from 'lucide-react';
import {
  Badge,
  EmptyState,
  ErrorState,
  Panel,
  SentimentBar,
} from '@/components/dashboard/primitives';
import { type CallDetail, type CallSummary, dashboardApi, usePoll } from '@/lib/dashboard/api';
import {
  OUTCOME_META,
  STATUS_META,
  formatClock,
  formatDuration,
  providerLabel,
} from '@/lib/dashboard/format';

const OUTCOME_FILTERS = [
  { key: '', label: 'All' },
  { key: 'order_placed', label: 'Orders' },
  { key: 'info_only', label: 'Info' },
  { key: 'transfer', label: 'Transfers' },
  { key: 'abandoned', label: 'Abandoned' },
];

const PAGE_SIZE = 25;

export default function CallsPage() {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [outcome, setOutcome] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(search), 300);
    return () => window.clearTimeout(id);
  }, [search]);

  useEffect(() => setOffset(0), [debounced, outcome]);

  const list = usePoll(
    useCallback(
      (signal) =>
        dashboardApi.calls(
          {
            limit: PAGE_SIZE,
            offset,
            outcome: outcome || undefined,
            search: debounced || undefined,
          },
          signal
        ),
      [offset, outcome, debounced]
    ),
    15000,
    [offset, outcome, debounced]
  );

  const data = list.data;
  const total = data?.total ?? 0;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Call logs</h1>
        <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
          Every call the agent has handled, with full transcript replay.
        </p>
      </div>

      <Panel>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <Search
              size={15}
              className="absolute top-1/2 left-3 -translate-y-1/2 text-[var(--voix-text-muted)]"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search room, order #, or transcript…"
              className="w-full rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] py-2 pr-3 pl-9 text-sm text-[var(--voix-text-primary)] transition outline-none placeholder:text-[var(--voix-text-muted)] focus:border-[var(--voix-accent)]"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {OUTCOME_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setOutcome(f.key)}
                className="rounded-full px-3 py-1.5 text-xs font-medium transition"
                style={
                  outcome === f.key
                    ? { background: 'var(--voix-accent)', color: 'var(--voix-accent-foreground)' }
                    : {
                        color: 'var(--voix-text-muted)',
                        border: '1px solid var(--voix-border-subtle)',
                      }
                }
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {list.error && !data ? (
          <ErrorState message={list.error} onRetry={list.refresh} />
        ) : data && data.calls.length === 0 ? (
          <EmptyState
            title="No calls match these filters"
            hint="Adjust the filters, or seed demo data with scripts/seed_dashboard.py"
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse">
              <thead>
                <tr className="text-left text-[11px] tracking-wide text-[var(--voix-text-muted)] uppercase">
                  <th className="px-3 py-2 font-medium">Started</th>
                  <th className="px-3 py-2 font-medium">Channel</th>
                  <th className="px-3 py-2 font-medium">Voice mode</th>
                  <th className="px-3 py-2 font-medium">Outcome</th>
                  <th className="px-3 py-2 font-medium">Duration</th>
                  <th className="px-3 py-2 font-medium">Turns</th>
                  <th className="px-3 py-2 font-medium">Sentiment</th>
                  <th className="px-3 py-2 font-medium">Order</th>
                </tr>
              </thead>
              <tbody>
                {(data?.calls ?? []).map((call: CallSummary) => {
                  const meta = OUTCOME_META[call.outcome] ?? OUTCOME_META.unknown;
                  return (
                    <tr
                      key={call.call_id}
                      onClick={() => setSelected(call.call_id)}
                      className="cursor-pointer border-t border-[var(--voix-border-subtle)] text-sm transition hover:bg-[var(--voix-bg-subtle)]"
                    >
                      <td className="px-3 py-3 text-[var(--voix-text-secondary)]">
                        {formatClock(call.started_at)}
                      </td>
                      <td className="px-3 py-3 text-[var(--voix-text-muted)] capitalize">
                        {call.channel || '—'}
                      </td>
                      <td className="px-3 py-3 text-[var(--voix-text-muted)]">
                        {providerLabel(call.voice_provider)}
                      </td>
                      <td className="px-3 py-3">
                        <Badge label={meta.label} color={meta.color} bg={meta.bg} />
                      </td>
                      <td className="px-3 py-3 text-[var(--voix-text-secondary)] tabular-nums">
                        {formatDuration(call.duration_seconds)}
                      </td>
                      <td className="px-3 py-3 text-[var(--voix-text-muted)] tabular-nums">
                        {call.turn_count}
                      </td>
                      <td className="px-3 py-3">
                        <SentimentBar value={call.sentiment} />
                      </td>
                      <td className="px-3 py-3 font-mono text-xs text-[var(--voix-text-muted)]">
                        {call.order_number ?? '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {total > PAGE_SIZE && (
          <div className="mt-4 flex items-center justify-between text-xs text-[var(--voix-text-muted)]">
            <span>
              {pageStart}–{pageEnd} of {total}
            </span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                className="rounded-full border border-[var(--voix-border-subtle)] px-3 py-1.5 font-medium transition enabled:hover:bg-[var(--voix-bg-subtle)] disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={pageEnd >= total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                className="rounded-full border border-[var(--voix-border-subtle)] px-3 py-1.5 font-medium transition enabled:hover:bg-[var(--voix-bg-subtle)] disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Panel>

      {selected && <CallDrawer callId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function CallDrawer({ callId, onClose }: { callId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<CallDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setDetail(null);
    setError(null);
    dashboardApi
      .call(callId, controller.signal)
      .then(setDetail)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Failed');
      });
    return () => controller.abort();
  }, [callId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const meta = detail ? (OUTCOME_META[detail.outcome] ?? OUTCOME_META.unknown) : null;
  const statusMeta = detail ? STATUS_META[detail.status] : null;

  return (
    <div className="fixed inset-0 z-[80] flex justify-end">
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col border-l border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] shadow-2xl">
        <header className="flex items-start justify-between border-b border-[var(--voix-border-subtle)] p-5">
          <div>
            <p className="text-xs text-[var(--voix-text-muted)]">Call detail</p>
            <p className="mt-0.5 font-mono text-sm text-[var(--voix-text-primary)]">{callId}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-[var(--voix-text-muted)] transition hover:bg-[var(--voix-bg-subtle)] hover:text-[var(--voix-text-primary)]"
          >
            <X size={18} />
          </button>
        </header>

        {error ? (
          <div className="p-5">
            <ErrorState message={error} />
          </div>
        ) : !detail ? (
          <div className="flex flex-1 items-center justify-center text-sm text-[var(--voix-text-muted)]">
            Loading transcript…
          </div>
        ) : (
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className="grid grid-cols-2 gap-3 border-b border-[var(--voix-border-subtle)] p-5 text-sm">
              <Field label="Outcome">
                {meta && <Badge label={meta.label} color={meta.color} bg={meta.bg} />}
              </Field>
              <Field label="Status">
                <span style={{ color: statusMeta?.color }}>
                  {statusMeta?.label ?? detail.status}
                </span>
              </Field>
              <Field label="Started">{formatClock(detail.started_at)}</Field>
              <Field label="Duration">{formatDuration(detail.duration_seconds)}</Field>
              <Field label="Channel">
                <span className="capitalize">{detail.channel || '—'}</span>
              </Field>
              <Field label="Voice mode">{providerLabel(detail.voice_provider)}</Field>
              <Field label="Turns">{detail.turn_count}</Field>
              <Field label="Sentiment">
                <SentimentBar value={detail.sentiment} />
              </Field>
              {detail.order_number && (
                <Field label="Linked order">
                  <span className="font-mono text-xs text-[var(--voix-accent)]">
                    {detail.order_number}
                  </span>
                </Field>
              )}
              {detail.guardrail_violations > 0 && (
                <Field label="Guardrail flags">
                  <span className="text-[var(--voix-warning)]">{detail.guardrail_violations}</span>
                </Field>
              )}
            </div>

            <div className="flex items-center justify-between px-5 pt-4 pb-2">
              <p className="text-xs font-semibold tracking-wide text-[var(--voix-text-muted)] uppercase">
                Transcript
              </p>
              <span className="text-xs text-[var(--voix-text-muted)]">
                {detail.transcript.length} messages
              </span>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto px-5 pb-6">
              {detail.transcript.length === 0 ? (
                <EmptyState title="No transcript captured for this call" />
              ) : (
                detail.transcript.map((turn, i) => {
                  const isAgent = turn.role === 'assistant';
                  return (
                    <div key={i} className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
                      <div
                        className="max-w-[85%] rounded-2xl px-3.5 py-2 text-sm"
                        style={{
                          background: isAgent ? 'var(--voix-bg-subtle)' : 'var(--voix-accent)',
                          color: isAgent
                            ? 'var(--voix-text-secondary)'
                            : 'var(--voix-accent-foreground)',
                        }}
                      >
                        <p className="mb-0.5 text-[10px] font-semibold uppercase opacity-70">
                          {isAgent ? 'Agent' : 'Caller'}
                        </p>
                        {turn.text}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] tracking-wide text-[var(--voix-text-muted)] uppercase">{label}</p>
      <div className="mt-1 text-[var(--voix-text-primary)]">{children}</div>
    </div>
  );
}
