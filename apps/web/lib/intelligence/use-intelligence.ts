'use client';

import { useEffect, useRef, useState } from 'react';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import type {
  BackendWorkflowStep,
  IntelligenceEvent,
  WorkflowStage,
} from './types';
import { parseTelemetryToEvents } from './telemetry-parser';
import {
  extractQuoteSnapshot,
  hasQuoteChanged,
  type QuoteSnapshot,
} from './quote-state-watcher';

const MAX_EVENTS = 30;
const MAX_EVENT_AGE_MS = 90_000;

export interface UseIntelligenceResult {
  events: IntelligenceEvent[];
  workflowSteps: BackendWorkflowStep[];
  stage: WorkflowStage;
  stageLabel: string;
  quoteSnapshot: QuoteSnapshot | null;
  quoteChanged: boolean;
  eventCount: number;
}

export function useIntelligence(
  telemetrySnapshot: SessionTelemetrySnapshot | null
): UseIntelligenceResult {
  const orderHashRef = useRef('');
  const prevQuoteRef = useRef<QuoteSnapshot | null>(null);
  const prevReasonRef = useRef('');
  const [events, setEvents] = useState<IntelligenceEvent[]>([]);
  const [workflowSteps, setWorkflowSteps] = useState<BackendWorkflowStep[]>([]);
  const [stage, setStage] = useState<WorkflowStage>('idle');
  const [quoteSnapshot, setQuoteSnapshot] = useState<QuoteSnapshot | null>(null);
  const [quoteChanged, setQuoteChanged] = useState(false);

  useEffect(() => {
    if (!telemetrySnapshot) return;

    const snapshotKey = `${telemetrySnapshot.reason}:${telemetrySnapshot.timestamp}`;
    if (snapshotKey === prevReasonRef.current) return;
    prevReasonRef.current = snapshotKey;

    const parsed = parseTelemetryToEvents(telemetrySnapshot, orderHashRef.current);
    orderHashRef.current = parsed.orderHash;

    const newQuote = extractQuoteSnapshot(telemetrySnapshot.price_quote);
    const quoteHasChanged = hasQuoteChanged(prevQuoteRef.current, newQuote);
    prevQuoteRef.current = newQuote;

    if (parsed.events.length > 0) {
      setEvents((prev) => {
        const merged = [...prev, ...parsed.events];
        const cutoff = Date.now() - MAX_EVENT_AGE_MS;
        return merged.filter((e) => e.timestamp >= cutoff).slice(-MAX_EVENTS);
      });
    }

    setWorkflowSteps(parsed.workflowSteps);
    setStage(parsed.stage);
    setQuoteSnapshot(newQuote);
    setQuoteChanged(quoteHasChanged);

    if (quoteHasChanged) {
      const timer = setTimeout(() => setQuoteChanged(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [telemetrySnapshot]);

  const stageLabel = getStageLabel(stage);

  return {
    events,
    workflowSteps,
    stage,
    stageLabel,
    quoteSnapshot,
    quoteChanged,
    eventCount: events.length,
  };
}

function getStageLabel(stage: WorkflowStage): string {
  const labels: Record<WorkflowStage, string> = {
    idle: 'Waiting',
    listening: 'Listening',
    processing: 'Processing',
    menu_lookup: 'Looking up menu',
    order_building: 'Building order',
    validation: 'Validating order',
    pricing: 'Calculating price',
    confirmation: 'Ready to confirm',
    placed: 'Order placed',
  };
  return labels[stage];
}
