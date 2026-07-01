'use client';

import { memo, useEffect, useRef } from 'react';
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
    <div className="flex items-center gap-2 px-4 py-2">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-[color:var(--voix-accent)] animate-pulse"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </div>
      <span className="text-xs text-[var(--voix-text-muted)]">{label}</span>
    </div>
  );
}

function EventIndicator({ event }: { event: IntelligenceEvent }) {
  if (event.kind === 'intent_detected' || event.kind === 'entity_extracted') {
    return (
      <div className="mx-4 flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
        <span className="text-xs font-medium text-indigo-700">
          {event.label}: {event.detail}
        </span>
      </div>
    );
  }

  if (event.kind === 'validation_error') {
    return (
      <div className="mx-4 flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        <span className="text-xs font-medium text-amber-700">{event.detail}</span>
      </div>
    );
  }

  return null;
}

export const ConversationFeed = memo(function ConversationFeed({
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
});
