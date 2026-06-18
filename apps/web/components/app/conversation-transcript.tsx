'use client';

import { type ReactNode, useEffect, useRef } from 'react';
import { type UserFacingSessionState } from '@/components/app/session-status';
import { TranscriptMessage } from '@/components/app/transcript-message';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

export interface ConversationEntry {
  id: string;
  role: 'assistant' | 'user';
  message: string;
}

interface ConversationTranscriptProps {
  messages: ConversationEntry[];
  state: UserFacingSessionState;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  footer?: ReactNode;
  className?: string;
}

export function ConversationTranscript({
  messages,
  state,
  collapsed = false,
  onToggleCollapsed,
  footer,
  className,
}: ConversationTranscriptProps) {
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!bodyRef.current || collapsed) {
      return;
    }

    bodyRef.current.scrollTo({
      top: bodyRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [collapsed, messages.length]);

  return (
    <section
      className={cn(
        'overflow-hidden rounded-[30px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)]',
        className
      )}
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
    >
      <div className="flex items-start justify-between gap-4 border-b border-[var(--voix-border-subtle)] px-5 py-4 md:px-6">
        <div>
          <h2 className="text-base font-semibold text-[var(--voix-text-primary)]">Conversation</h2>
          <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
            {messages.length > 0
              ? 'Follow the conversation as your order takes shape.'
              : state === 'listening' || state === 'userSpeaking'
                ? 'Your conversation will appear here once you start talking.'
                : 'The conversation timeline will appear once the session is active.'}
          </p>
        </div>
        {onToggleCollapsed && (
          <Button
            type="button"
            variant="ghost"
            onClick={onToggleCollapsed}
            className="rounded-full px-4 text-sm text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)] hover:text-[var(--voix-text-primary)]"
          >
            {collapsed ? 'Show' : 'Hide'}
          </Button>
        )}
      </div>

      {!collapsed && (
        <div
          ref={bodyRef}
          aria-live="polite"
          className="max-h-[440px] space-y-4 overflow-y-auto px-4 py-5 [scrollbar-width:thin] md:px-6"
        >
          {messages.length > 0 ? null : (
            <div className="rounded-[22px] border border-dashed border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-5 py-8 text-center text-sm leading-7 text-[var(--voix-text-muted)]">
              Your conversation will appear here once you start talking.
            </div>
          )}

          {messages.map((entry) => (
            <TranscriptMessage
              key={entry.id}
              role={entry.role}
              message={entry.message}
            />
          ))}
        </div>
      )}

      {footer && (
        <div className="border-t border-[var(--voix-border-subtle)] px-4 py-4 md:px-6">
          {footer}
        </div>
      )}
    </section>
  );
}
