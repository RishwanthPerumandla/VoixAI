'use client';

import { type ReactNode, useEffect, useRef } from 'react';
import { type ReceivedMessage } from '@livekit/components-react';
import { TranscriptMessage } from '@/components/app/transcript-message';
import { type UserFacingSessionState } from '@/components/app/session-status';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

interface ConversationTranscriptProps {
  messages: ReceivedMessage[];
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
        'overflow-hidden rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(11,18,32,0.92),rgba(9,15,27,0.98))] shadow-[0_26px_80px_rgba(0,0,0,0.24)]',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4 border-b border-white/8 px-5 py-4 md:px-6">
        <div>
          <h2 className="text-base font-semibold text-slate-50">Conversation</h2>
          <p className="mt-1 text-sm text-slate-400">
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
            className="rounded-full px-4 text-sm text-slate-300 hover:bg-white/8 hover:text-slate-50"
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
            <div className="rounded-[22px] border border-dashed border-white/10 bg-white/[0.025] px-5 py-8 text-center text-sm leading-7 text-slate-400">
              Your conversation will appear here once you start talking.
            </div>
          )}

          {messages.map((entry) => (
            <TranscriptMessage
              key={entry.id}
              role={entry.from?.isLocal ? 'user' : 'assistant'}
              message={entry.message}
            />
          ))}
        </div>
      )}

      {footer && <div className="border-t border-white/8 px-4 py-4 md:px-6">{footer}</div>}
    </section>
  );
}
