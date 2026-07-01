'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
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

export function LiveTranscriptLine({ messages, state, className }: LiveTranscriptLineProps) {
  const latest = getLatestMessage(messages);
  const stateLabel = getStateLabel(state);
  const prevMessageRef = useRef<string>('');

  const displayText = latest?.message ?? '';
  const isStale = state === 'listening' || state === 'idle' || state === 'complete';
  const isAssistant = latest?.role === 'assistant';

  return (
    <div
      className={cn(
        'rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-5 py-4',
        className
      )}
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
      aria-live="polite"
      aria-atomic="true"
    >
      <AnimatePresence mode="wait">
        {stateLabel && !displayText && (
          <motion.div
            key="state"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="flex items-center gap-2"
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
            <span className="text-sm text-[var(--voix-text-muted)]">{stateLabel}</span>
          </motion.div>
        )}

        {displayText && (
          <motion.div
            key={displayText.slice(0, 30)}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="flex items-start gap-2.5"
          >
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
          </motion.div>
        )}

        {!displayText && !stateLabel && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center"
          >
            <p className="text-sm text-[var(--voix-text-muted)]">
              Start speaking to begin your order...
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
