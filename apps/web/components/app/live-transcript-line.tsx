'use client';

import { memo, useRef } from 'react';
import type { UserFacingSessionState } from '@/components/app/session-status';
import type { ConversationEntry } from '@/components/app/conversation-feed';
import { cn } from '@/lib/shadcn/utils';

interface LiveTranscriptLineProps {
  messages: ConversationEntry[];
  state: UserFacingSessionState;
  className?: string;
}

function getLatestMessage(messages: ConversationEntry[]): ConversationEntry | null {
  if (messages.length === 0) return null;
  return messages[messages.length - 1];
}

function getStateLabel(state: UserFacingSessionState): string | null {
  switch (state) {
    case 'assistantSpeaking':
      return 'Mia is speaking...';
    case 'userSpeaking':
      return 'You are speaking...';
    case 'thinking':
      return 'Mia is thinking...';
    case 'connecting':
      return 'Connecting...';
    default:
      return null;
  }
}

export const LiveTranscriptLine = memo(function LiveTranscriptLine({ messages, state, className }: LiveTranscriptLineProps) {
  const latest = getLatestMessage(messages);
  const stateLabel = getStateLabel(state);

  const displayText = latest?.message ?? '';
  const isStale = state === 'listening' || state === 'idle' || state === 'complete';
  const isAssistant = latest?.role === 'assistant';

  return (
    <div
      className={cn(
        'rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-5 py-4 transition-opacity',
        className
      )}
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
      aria-live="polite"
      aria-atomic="true"
    >
      {stateLabel && !displayText && (
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-[color:var(--voix-accent)] animate-pulse"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
          <span className="text-sm text-[var(--voix-text-muted)]">{stateLabel}</span>
        </div>
      )}

      {displayText && (
        <div className="flex items-start gap-2.5">
          <span
            className={cn(
              'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
              isAssistant
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-[color:var(--voix-accent)] text-white'
            )}
          >
            {isAssistant ? 'M' : 'Y'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium text-[var(--voix-text-muted)]">
              {isAssistant ? 'Mia' : 'You'}
            </p>
            <p
              className={cn(
                'mt-0.5 line-clamp-2 text-sm leading-6',
                isStale
                  ? 'text-[var(--voix-text-secondary)]'
                  : 'text-[var(--voix-text-primary)]'
              )}
            >
              {displayText}
            </p>
          </div>
        </div>
      )}

      {!displayText && !stateLabel && (
        <p className="text-center text-sm text-[var(--voix-text-muted)]">
          Start speaking to begin your order...
        </p>
      )}
    </div>
  );
});
