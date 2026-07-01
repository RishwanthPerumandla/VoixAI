'use client';

import type { BackendWorkflowStep, IntelligenceEvent, WorkflowStage } from '@/lib/intelligence/types';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { BackendWorkflowRail } from './backend-workflow-rail';
import { IntelligenceTimeline } from './intelligence-timeline';
import { LatencyStats } from './latency-indicator';
import { cn } from '@/lib/shadcn/utils';

interface IntelligencePanelProps {
  events: IntelligenceEvent[];
  workflowSteps: BackendWorkflowStep[];
  stage: WorkflowStage;
  stageLabel: string;
  eventCount: number;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  className?: string;
}

export function IntelligencePanel({
  events,
  workflowSteps,
  stage,
  stageLabel,
  eventCount,
  telemetrySnapshot,
  className,
}: IntelligencePanelProps) {
  return (
    <div
      className={cn(
        'flex h-full flex-col gap-4 overflow-hidden',
        className
      )}
    >
      {/* Latency Stats */}
      <section
        className="rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-4"
        style={{ boxShadow: 'var(--voix-card-shadow)' }}
      >
        <LatencyStats telemetrySnapshot={telemetrySnapshot} />
      </section>

      {/* Backend Pipeline */}
      <section
        className="rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-4"
        style={{ boxShadow: 'var(--voix-card-shadow)' }}
      >
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold tracking-wide text-[var(--voix-text-muted)] uppercase">
            Backend Pipeline
          </p>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-medium text-indigo-700">
            {stageLabel}
          </span>
        </div>
        <div className="mt-3">
          <BackendWorkflowRail steps={workflowSteps} />
        </div>
      </section>

      {/* Intelligence Timeline */}
      <section
        className="flex min-h-0 flex-1 flex-col rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-4"
        style={{ boxShadow: 'var(--voix-card-shadow)' }}
      >
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold tracking-wide text-[var(--voix-text-muted)] uppercase">
            Intelligence Feed
          </p>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
            {eventCount}
          </span>
        </div>
        <div className="mt-3 min-h-0 flex-1 overflow-y-auto [scrollbar-width:thin]">
          <IntelligenceTimeline events={events} />
        </div>
      </section>
    </div>
  );
}
