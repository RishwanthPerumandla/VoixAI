'use client';

import { useState } from 'react';
import { CaretDownIcon, CaretUpIcon } from '@phosphor-icons/react';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import type { RuntimeConfig } from '@/lib/runtime-config';
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
    <div className="flex items-start justify-between gap-4 border-t border-[var(--voix-border-subtle)] py-3 first:border-t-0 first:pt-0 last:pb-0">
      <dt className="text-xs text-[var(--voix-text-muted)]">{label}</dt>
      <dd className="max-w-[60%] text-right text-sm text-[var(--voix-text-primary)]">{value}</dd>
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
  const orderMetrics = telemetrySnapshot?.order.reliability_metrics;
  const lastEvent = telemetrySnapshot?.order.recent_events?.at(-1);

  return (
    <section
      className={cn(
        'rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-4',
        className
      )}
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div>
          <p className="text-sm font-medium text-[var(--voix-text-primary)]">Developer details</p>
          <p className="mt-1 text-xs text-[var(--voix-text-muted)]">
            Internal voice session details for demos and QA.
          </p>
        </div>
        <span className="text-[var(--voix-text-muted)]">
          {open ? <CaretUpIcon size={16} /> : <CaretDownIcon size={16} />}
        </span>
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
          <DetailRow
            label="Order status"
            value={telemetrySnapshot?.order.status ?? telemetrySnapshot?.order.phase ?? 'unknown'}
          />
          <DetailRow label="Turn count" value={String(turns)} />
          <DetailRow
            label="Latency"
            value={
              metrics?.e2e_latency !== null && metrics?.e2e_latency !== undefined
                ? `${Math.round(metrics.e2e_latency * 1000)} ms`
                : 'Unavailable'
            }
          />
          <DetailRow
            label="Corrections"
            value={String(orderMetrics?.correction_count ?? 0)}
          />
          <DetailRow
            label="Cancellations"
            value={String(orderMetrics?.cancellation_count ?? 0)}
          />
          <DetailRow
            label="Validation failures"
            value={String(orderMetrics?.validation_failure_count ?? 0)}
          />
          <DetailRow
            label="Clarifications"
            value={String(orderMetrics?.clarification_count ?? 0)}
          />
          <DetailRow
            label="Unknown items"
            value={String(orderMetrics?.unknown_item_count ?? 0)}
          />
          <DetailRow
            label="Duplicate submits"
            value={String(orderMetrics?.duplicate_confirmation_prevented ?? 0)}
          />
          <DetailRow
            label="Final status"
            value={orderMetrics?.final_status ?? 'unknown'}
          />
          <DetailRow
            label="Clarification"
            value={telemetrySnapshot?.order.last_clarification_question ?? 'None'}
          />
          <DetailRow
            label="Last reducer event"
            value={lastEvent ? `${lastEvent.type}: ${lastEvent.detail}` : 'None'}
          />
        </dl>
      )}
    </section>
  );
}
