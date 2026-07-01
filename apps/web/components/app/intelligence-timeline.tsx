'use client';

import { motion, AnimatePresence } from 'motion/react';
import type { IntelligenceEvent } from '@/lib/intelligence/types';
import { cn } from '@/lib/shadcn/utils';

const STATUS_STYLES: Record<string, { dot: string; bg: string; text: string }> = {
  active: {
    dot: 'bg-indigo-500',
    bg: 'bg-indigo-50 border-indigo-200',
    text: 'text-indigo-700',
  },
  completed: {
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50 border-emerald-200',
    text: 'text-emerald-700',
  },
  failed: {
    dot: 'bg-rose-500',
    bg: 'bg-rose-50 border-rose-200',
    text: 'text-rose-700',
  },
  info: {
    dot: 'bg-sky-500',
    bg: 'bg-sky-50 border-sky-200',
    text: 'text-sky-700',
  },
};

const KIND_ICONS: Partial<Record<string, string>> = {
  intent_detected: ' ',
  entity_extracted: '✏️',
  tool_called: '⚡',
  tool_completed: '✅',
  state_changed: ' ',
  validation_error: '⚠️',
  order_updated: ' ',
  quote_received: ' ',
  guardrail_triggered: ' ',
  system_message: ' ',
};

interface EventItemProps {
  event: IntelligenceEvent;
  isLatest: boolean;
}

function EventItem({ event, isLatest }: EventItemProps) {
  const styles = STATUS_STYLES[event.status] ?? STATUS_STYLES.info;
  const icon = KIND_ICONS[event.kind] ?? '•';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      tabIndex={0}
      role="article"
      aria-label={`${event.label}: ${event.detail ?? ''}`}
      className={cn(
        'relative rounded-[14px] border px-3 py-2.5 outline-none',
        styles.bg,
        isLatest && 'ring-2 ring-indigo-200/50',
        'focus-visible:border-[color:var(--voix-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--voix-accent)]/30'
      )}
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 text-sm" aria-hidden="true">{icon}</span>
        <div className="min-w-0 flex-1">
          <p className={cn('text-xs font-semibold', styles.text)}>{event.label}</p>
          {event.detail && (
            <p className="mt-0.5 truncate text-xs text-[var(--voix-text-muted)]">{event.detail}</p>
          )}
        </div>
        <span className={cn('h-2 w-2 shrink-0 rounded-full', styles.dot)} aria-hidden="true" />
      </div>
    </motion.div>
  );
}

interface IntelligenceTimelineProps {
  events: IntelligenceEvent[];
  className?: string;
  maxVisible?: number;
}

export function IntelligenceTimeline({
  events,
  className,
  maxVisible = 12,
}: IntelligenceTimelineProps) {
  const visibleEvents = events.slice(-maxVisible);
  const latestId = visibleEvents[visibleEvents.length - 1]?.id;

  return (
    <div
      className={cn('space-y-2', className)}
      role="log"
      aria-label="Intelligence events"
      aria-live="polite"
    >
      <AnimatePresence mode="popLayout">
        {visibleEvents.map((event) => (
          <EventItem
            key={event.id}
            event={event}
            isLatest={event.id === latestId}
          />
        ))}
      </AnimatePresence>

      {events.length === 0 && (
        <div className="rounded-[14px] border border-dashed border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4 text-center">
          <p className="text-xs text-[var(--voix-text-muted)]">
            Intelligence events will appear here
          </p>
        </div>
      )}
    </div>
  );
}
