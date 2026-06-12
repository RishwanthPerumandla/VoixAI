'use client';

import { useState } from 'react';
import { CaretDownIcon, CaretUpIcon } from '@phosphor-icons/react';
import type { RuntimeConfig } from '@/lib/runtime-config';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { cn } from '@/lib/shadcn/utils';

interface DeveloperDetailsProps {
  enabled: boolean;
  runtimeConfig: RuntimeConfig | null;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  rawState?: string | null;
  className?: string;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-t border-white/8 py-3 first:border-t-0 first:pt-0 last:pb-0">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="max-w-[60%] text-right text-sm text-slate-100">{value}</dd>
    </div>
  );
}

export function DeveloperDetails({
  enabled,
  runtimeConfig,
  telemetrySnapshot,
  rawState,
  className,
}: DeveloperDetailsProps) {
  const [open, setOpen] = useState(false);

  if (!enabled || !runtimeConfig) {
    return null;
  }

  const metrics = telemetrySnapshot?.assistant_turn_metrics;
  const turns = telemetrySnapshot?.turn_count ?? 0;

  return (
    <section
      className={cn(
        'rounded-[20px] border border-white/10 bg-slate-950/70 p-4 shadow-lg shadow-black/10',
        className
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div>
          <p className="text-sm font-medium text-slate-50">Developer details</p>
          <p className="mt-1 text-xs text-slate-400">Internal voice session details for demos and QA.</p>
        </div>
        {open ? <CaretUpIcon size={16} /> : <CaretDownIcon size={16} />}
      </button>

      {open && (
        <dl className="mt-4">
          <DetailRow label="Mode" value={runtimeConfig.presetLabel} />
          <DetailRow
            label="Model"
            value={
              runtimeConfig.voiceEngine === 'pipeline'
                ? runtimeConfig.llmModel
                : runtimeConfig.voiceEngine.startsWith('openai')
                  ? runtimeConfig.openaiRealtimeModel
                  : runtimeConfig.googleRealtimeModel
            }
          />
          <DetailRow label="Raw state" value={rawState ?? 'unknown'} />
          <DetailRow label="Turn count" value={String(turns)} />
          <DetailRow
            label="Latency"
            value={
              metrics?.e2e_latency !== null && metrics?.e2e_latency !== undefined
                ? `${Math.round(metrics.e2e_latency * 1000)} ms`
                : 'Unavailable'
            }
          />
        </dl>
      )}
    </section>
  );
}
