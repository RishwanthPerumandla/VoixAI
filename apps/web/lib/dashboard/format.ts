export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem.toString().padStart(2, '0')}s`;
}

export function formatClock(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function formatTimeAgo(epochSeconds: number): string {
  const diff = Date.now() / 1000 - epochSeconds;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function formatPercent(ratio: number, digits = 1): string {
  return `${(ratio * 100).toFixed(digits)}%`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

export const OUTCOME_META: Record<string, { label: string; color: string; bg: string }> = {
  order_placed: {
    label: 'Order placed',
    color: 'var(--voix-success)',
    bg: 'rgba(52,211,153,0.12)',
  },
  info_only: { label: 'Info / FAQ', color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  transfer: { label: 'Transferred', color: 'var(--voix-warning)', bg: 'rgba(245,196,81,0.12)' },
  abandoned: { label: 'Abandoned', color: 'var(--voix-danger)', bg: 'rgba(251,113,133,0.12)' },
  unknown: { label: 'In progress', color: 'var(--voix-text-muted)', bg: 'rgba(148,163,184,0.12)' },
};

export const STATUS_META: Record<string, { label: string; color: string }> = {
  completed: { label: 'Completed', color: 'var(--voix-success)' },
  in_progress: { label: 'Live', color: 'var(--voix-accent)' },
  failed: { label: 'Failed', color: 'var(--voix-danger)' },
};

export function sentimentMeta(value: number | null): { label: string; color: string } {
  if (value == null) return { label: '—', color: 'var(--voix-text-muted)' };
  if (value >= 0.66) return { label: 'Positive', color: 'var(--voix-success)' };
  if (value >= 0.4) return { label: 'Neutral', color: 'var(--voix-warning)' };
  return { label: 'Negative', color: 'var(--voix-danger)' };
}

export function providerLabel(provider: string): string {
  switch (provider) {
    case 'classic':
      return 'Classic pipeline';
    case 'openai_realtime':
      return 'OpenAI Realtime';
    case 'gemini_live':
      return 'Gemini Live';
    default:
      return provider || '—';
  }
}
