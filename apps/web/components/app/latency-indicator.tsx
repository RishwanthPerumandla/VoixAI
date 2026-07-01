'use client';

import { memo, useEffect, useState } from 'react';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { cn } from '@/lib/shadcn/utils';

interface LatencyIndicatorProps {
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  className?: string;
}

function getLatencyColor(ms: number): string {
  if (ms <= 800) return 'text-emerald-600 bg-emerald-50';
  if (ms <= 1200) return 'text-amber-600 bg-amber-50';
  return 'text-rose-600 bg-rose-50';
}

function getLatencyDotColor(ms: number): string {
  if (ms <= 800) return 'bg-emerald-500';
  if (ms <= 1200) return 'bg-amber-500';
  return 'bg-rose-500';
}

export const LatencyIndicator = memo(function LatencyIndicator({
  telemetrySnapshot,
  className,
}: LatencyIndicatorProps) {
  const latencyMs = telemetrySnapshot?.assistant_turn_metrics?.e2e_latency != null
    ? Math.round(telemetrySnapshot.assistant_turn_metrics.e2e_latency * 1000)
    : null;

  const targetMs = telemetrySnapshot?.target_e2e_latency_ms ?? 800;

  if (latencyMs === null) {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
          'bg-slate-100 text-slate-500',
          className
        )}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
        <span>Latency: --</span>
      </div>
    );
  }

  const colorClass = getLatencyColor(latencyMs);
  const dotColor = getLatencyDotColor(latencyMs);

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium tabular-nums',
        colorClass,
        className
      )}
      aria-label={`Response latency: ${latencyMs} milliseconds`}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', dotColor)} />
      <span>{latencyMs} ms</span>
    </div>
  );
});

interface LatencyStatsProps {
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  className?: string;
}

export const LatencyStats = memo(function LatencyStats({
  telemetrySnapshot,
  className,
}: LatencyStatsProps) {
  const metrics = telemetrySnapshot?.assistant_turn_metrics;
  const targetMs = telemetrySnapshot?.target_e2e_latency_ms ?? 800;
  const acceptableMs = telemetrySnapshot?.acceptable_e2e_latency_ms ?? 1500;

  const latencyMs = metrics?.e2e_latency != null
    ? Math.round(metrics.e2e_latency * 1000)
    : null;

  const llmMs = metrics?.llm_ttft != null
    ? Math.round(metrics.llm_ttft * 1000)
    : null;

  const ttsMs = metrics?.tts_ttfb != null
    ? Math.round(metrics.tts_ttfb * 1000)
    : null;

  return (
    <div className={cn('space-y-2', className)}>
      <p className="text-xs font-semibold text-[var(--voix-text-muted)] uppercase">
        Voice Latency
      </p>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-xl bg-[var(--voix-bg-subtle)] p-2.5 text-center">
          <p className={cn(
            'text-lg font-bold tabular-nums',
            latencyMs !== null
              ? latencyMs <= targetMs
                ? 'text-emerald-600'
                : latencyMs <= acceptableMs
                  ? 'text-amber-600'
                  : 'text-rose-600'
              : 'text-[var(--voix-text-muted)]'
          )}>
            {latencyMs !== null ? `${latencyMs}` : '--'}
          </p>
          <p className="text-[10px] text-[var(--voix-text-muted)]">E2E (ms)</p>
        </div>

        <div className="rounded-xl bg-[var(--voix-bg-subtle)] p-2.5 text-center">
          <p className="text-lg font-bold tabular-nums text-[var(--voix-text-primary)]">
            {llmMs !== null ? `${llmMs}` : '--'}
          </p>
          <p className="text-[10px] text-[var(--voix-text-muted)]">LLM (ms)</p>
        </div>

        <div className="rounded-xl bg-[var(--voix-bg-subtle)] p-2.5 text-center">
          <p className="text-lg font-bold tabular-nums text-[var(--voix-text-primary)]">
            {ttsMs !== null ? `${ttsMs}` : '--'}
          </p>
          <p className="text-[10px] text-[var(--voix-text-muted)]">TTS (ms)</p>
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px] text-[var(--voix-text-muted)]">
        <span>Target: {targetMs}ms</span>
        <span>Acceptable: {acceptableMs}ms</span>
      </div>
    </div>
  );
});
