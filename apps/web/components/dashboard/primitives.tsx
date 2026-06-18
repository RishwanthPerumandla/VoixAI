'use client';

import type { ReactNode } from 'react';
import { cn } from '@/lib/shadcn/utils';

export function Panel({
  children,
  className,
  title,
  subtitle,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <section
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
      className={cn(
        'rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-5',
        className
      )}
    >
      {(title || action) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && (
              <h2 className="text-sm font-semibold tracking-wide text-[var(--voix-text-primary)]">
                {title}
              </h2>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-[var(--voix-text-muted)]">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export interface KpiSegment {
  label: string;
  value: number;
  color: string;
}

export function KpiCard({
  label,
  value,
  delta,
  hint,
  accent,
  icon,
  segments,
  children,
}: {
  label: string;
  value: ReactNode;
  delta?: { value: string; positive: boolean };
  hint?: string;
  accent?: string;
  icon?: ReactNode;
  segments?: KpiSegment[];
  children?: ReactNode;
}) {
  const accentColor = accent ?? 'var(--voix-accent)';
  return (
    <div
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
      className="group relative overflow-hidden rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-5 transition-shadow"
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-[var(--voix-text-muted)] uppercase">
          {label}
        </p>
        {icon && (
          <span
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{
              background: `color-mix(in oklab, ${accentColor} 12%, transparent)`,
              color: accentColor,
            }}
          >
            {icon}
          </span>
        )}
      </div>
      <div className="mt-2.5 flex items-end gap-2">
        <span className="text-[2rem] leading-none font-semibold text-[var(--voix-text-primary)]">
          {value}
        </span>
        {delta && (
          <span
            className="mb-0.5 inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-semibold"
            style={{
              color: delta.positive ? 'var(--voix-success)' : 'var(--voix-danger)',
              background: `color-mix(in oklab, ${delta.positive ? 'var(--voix-success)' : 'var(--voix-danger)'} 12%, transparent)`,
            }}
          >
            {delta.positive ? '↑' : '↓'} {delta.value}
          </span>
        )}
      </div>
      {hint && <p className="mt-1.5 text-xs text-[var(--voix-text-muted)]">{hint}</p>}
      {segments && segments.length > 0 && <SegmentBars segments={segments} />}
      {children && <div className="mt-3">{children}</div>}
    </div>
  );
}

function SegmentBars({ segments }: { segments: KpiSegment[] }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <div
      className="mt-4 grid gap-2.5"
      style={{ gridTemplateColumns: `repeat(${segments.length}, minmax(0,1fr))` }}
    >
      {segments.map((seg) => (
        <div key={seg.label}>
          <p className="mb-1.5 truncate text-[11px] font-medium text-[var(--voix-text-secondary)]">
            {seg.label}
          </p>
          <div className="h-1.5 overflow-hidden rounded-full bg-[var(--voix-bg-subtle)]">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.max(6, (seg.value / total) * 100)}%`,
                background: `linear-gradient(90deg, ${seg.color}, color-mix(in oklab, ${seg.color} 55%, white))`,
              }}
            />
          </div>
          <p className="mt-1 text-[11px] text-[var(--voix-text-muted)] tabular-nums">{seg.value}</p>
        </div>
      ))}
    </div>
  );
}

export function Badge({ label, color, bg }: { label: string; color: string; bg?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ color, backgroundColor: bg ?? 'rgba(255,255,255,0.06)' }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

export function SentimentBar({ value }: { value: number | null }) {
  if (value == null) {
    return <span className="text-xs text-[var(--voix-text-muted)]">—</span>;
  }
  const pct = Math.round(value * 100);
  const color =
    value >= 0.66
      ? 'var(--voix-success)'
      : value >= 0.4
        ? 'var(--voix-warning)'
        : 'var(--voix-danger)';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--voix-bg-subtle)]">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs tabular-nums" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-[var(--voix-border-subtle)] py-12 text-center">
      <p className="text-sm font-medium text-[var(--voix-text-secondary)]">{title}</p>
      {hint && <p className="max-w-sm text-xs text-[var(--voix-text-muted)]">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-[var(--voix-danger)]/30 bg-[var(--voix-danger)]/5 py-10 text-center">
      <p className="text-sm font-medium text-[var(--voix-danger)]">Could not reach the API</p>
      <p className="max-w-md text-xs text-[var(--voix-text-muted)]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-full border border-[var(--voix-border-strong)] px-4 py-1.5 text-xs font-medium text-[var(--voix-text-primary)] transition hover:bg-[var(--voix-bg-subtle)]"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-28 animate-pulse rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)]"
        />
      ))}
    </div>
  );
}
