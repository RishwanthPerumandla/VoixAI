'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import type { UserFacingSessionState } from '@/components/app/session-status';
import { TranscriptMessage } from '@/components/app/transcript-message';
import { cn } from '@/lib/shadcn/utils';
import type { IntelligenceEvent } from '@/lib/intelligence/types';

export interface ConversationEntry {
  id: string;
  role: 'assistant' | 'user';
  message: string;
}

interface ConversationFeedProps {
  messages: ConversationEntry[];
  state: UserFacingSessionState;
  latestEvent?: IntelligenceEvent;
  className?: string;
}

function StateIndicator({ state }: { state: UserFacingSessionState }) {
  const labels: Partial<Record<UserFacingSessionState, string>> = {
    thinking: 'Mia is thinking...',
    connecting: 'Connecting...',
  };

  const label = labels[state];
  if (!label) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="flex items-center gap-2 px-4 py-2"
    >
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-[color:var(--voix-accent)]"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </div>
      <span className="text-xs text-[var(--voix-text-muted)]">{label}</span>
    </motion.div>
  );
}

function EventIndicator({ event }: { event: IntelligenceEvent }) {
  if (event.kind === 'intent_detected' || event.kind === 'entity_extracted') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mx-4 flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
        <span className="text-xs font-medium text-indigo-700">
          {event.label}: {event.detail}
        </span>
      </motion.div>
    );
  }

  if (event.kind === 'validation_error') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mx-4 flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        <span className="text-xs font-medium text-amber-700">{event.detail}</span>
      </motion.div>
    );
  }

  return null;
}

export function ConversationFeed({
  messages,
  state,
  latestEvent,
  className,
}: ConversationFeedProps) {
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!bodyRef.current) return;
    bodyRef.current.scrollTo({
      top: bodyRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages.length, state]);

  return (
    <div
      ref={bodyRef}
      className={cn(
        'flex-1 space-y-3 overflow-y-auto px-2 py-4 [scrollbar-width:thin]',
        className
      )}
      role="log"
      aria-label="Conversation"
      aria-live="polite"
    >
      {messages.length === 0 && state === 'listening' && (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-[var(--voix-text-muted)]">
            Speak to start your order...
          </p>
        </div>
      )}

      {messages.map((entry) => (
        <TranscriptMessage
          key={entry.id}
          role={entry.role}
          message={entry.message}
        />
      ))}

      <StateIndicator state={state} />

      {latestEvent && <EventIndicator event={latestEvent} />}
    </div>
  );
}
