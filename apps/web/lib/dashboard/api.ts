'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// The dashboard reads directly from the VoixAI API. Same base URL the live
// voice client uses for token issuance.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';

// --- API response types (mirror apps/api/main.py) --------------------------

export interface CallSummary {
  call_id: string;
  room_name: string;
  scenario: string;
  channel: string;
  voice_provider: string;
  llm_model: string;
  status: 'in_progress' | 'completed' | 'failed';
  outcome: 'order_placed' | 'info_only' | 'transfer' | 'abandoned' | 'unknown';
  started_at: number;
  ended_at: number | null;
  duration_seconds: number | null;
  turn_count: number;
  sentiment: number | null;
  language: string;
  order_number: string | null;
  guardrail_violations: number;
}

export interface TranscriptTurn {
  role: string;
  text: string;
  ts: number | null;
}

export interface CallDetail extends CallSummary {
  transcript: TranscriptTurn[];
  error: string | null;
}

export interface CallListResponse {
  calls: CallSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface TimeBucket {
  label: string;
  start: number;
  calls: number;
  orders: number;
  completed: number;
}

export interface AnalyticsOverview {
  window_hours: number;
  total_calls: number;
  completed_calls: number;
  in_progress_calls: number;
  failed_calls: number;
  success_rate: number;
  containment_rate: number;
  orders_placed: number;
  revenue_total: string;
  avg_duration_seconds: number;
  avg_turns: number;
  avg_sentiment: number | null;
  transfers: number;
  abandoned: number;
  outcomes: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  series: TimeBucket[];
}

export interface OrderListItem {
  order_number: string;
  room_name: string;
  status: string;
  customer_name: string;
  item_count: number;
  item_summary: string[];
  subtotal: string;
  tax: string;
  total: string;
  eta_minutes: number;
  order_type: string | null;
  created_at: number;
}

export interface OrderListResponse {
  orders: OrderListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthComponent {
  name: string;
  status: 'operational' | 'degraded' | 'down';
  detail: string;
}

export interface ObservabilitySnapshot {
  status: 'operational' | 'degraded' | 'down';
  uptime_seconds: number;
  components: HealthComponent[];
  total_calls: number;
  failed_calls: number;
  error_rate: number;
  orders_total: number;
  avg_duration_seconds: number;
  p95_duration_seconds: number;
  guardrail_violations: number;
}

// --- fetchers --------------------------------------------------------------

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    signal,
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}) for ${path}`);
  }
  return (await res.json()) as T;
}

export const dashboardApi = {
  overview: (windowHours: number, signal?: AbortSignal) =>
    getJson<AnalyticsOverview>(
      `/api/analytics/overview?window_hours=${windowHours}&buckets=12`,
      signal
    ),
  calls: (
    params: { limit?: number; offset?: number; status?: string; outcome?: string; search?: string },
    signal?: AbortSignal
  ) => {
    const q = new URLSearchParams();
    q.set('limit', String(params.limit ?? 50));
    q.set('offset', String(params.offset ?? 0));
    if (params.status) q.set('status', params.status);
    if (params.outcome) q.set('outcome', params.outcome);
    if (params.search) q.set('search', params.search);
    return getJson<CallListResponse>(`/api/calls?${q.toString()}`, signal);
  },
  call: (callId: string, signal?: AbortSignal) =>
    getJson<CallDetail>(`/api/calls/${callId}`, signal),
  orders: (limit = 50, signal?: AbortSignal) =>
    getJson<OrderListResponse>(`/api/orders?limit=${limit}`, signal),
  health: (signal?: AbortSignal) =>
    getJson<ObservabilitySnapshot>(`/api/observability/health`, signal),
};

// --- polling hook ----------------------------------------------------------

export interface PollState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  lastUpdated: number | null;
  refresh: () => void;
}

/**
 * Fetch `fetcher` on mount and every `intervalMs`. Re-runs when `deps` change.
 * Keeps the previous data visible while refetching so the UI never flickers
 * back to a loading state on each poll.
 */
export function usePoll<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  intervalMs: number,
  deps: ReadonlyArray<unknown> = []
): PollState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [nonce, setNonce] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const run = async () => {
      try {
        const result = await fetcherRef.current(controller.signal);
        if (!active) return;
        setData(result);
        setError(null);
        setLastUpdated(Date.now());
      } catch (err) {
        if (!active || controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        if (active) setLoading(false);
      }
    };

    run();
    const id = window.setInterval(run, intervalMs);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, nonce, ...deps]);

  return { data, error, loading, lastUpdated, refresh };
}
