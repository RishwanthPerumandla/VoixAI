'use client';

import { type ReactNode } from 'react';
import {
  type UserFacingSessionState,
  getSessionStatusContent,
} from '@/components/app/session-status';
import { VoiceVisualizer } from '@/components/app/voice-visualizer';
import { cn } from '@/lib/shadcn/utils';

interface AssistantStageProps {
  state: UserFacingSessionState;
  latestAssistantPrompt?: string | null;
  children?: ReactNode;
  className?: string;
}

export function AssistantStage({
  state,
  latestAssistantPrompt,
  children,
  className,
}: AssistantStageProps) {
  const copy = getSessionStatusContent(state);

  return (
    <section
      aria-live="polite"
      className={cn(
        'relative overflow-hidden rounded-[32px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6 md:p-8',
        className
      )}
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.08),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(139,92,246,0.07),transparent_24%)]" />
      <div className="relative flex flex-col items-center text-center">
        <div className="inline-flex rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-4 py-1.5 text-xs font-medium tracking-[0.16em] text-[var(--voix-text-muted)]">
          VoixAI realtime stage
        </div>
        <VoiceVisualizer state={state} className="mt-6" />
        <p className="mt-7 text-3xl font-semibold tracking-tight text-[var(--voix-text-primary)] md:text-[2.15rem]">
          {copy.label}
        </p>
        <p className="mt-3 max-w-xl text-base leading-7 text-[var(--voix-text-secondary)]">
          {state === 'listening' || state === 'userSpeaking'
            ? 'Speak naturally. This shared voice session can support different workflows.'
            : copy.helper}
        </p>

        {latestAssistantPrompt && (
          <div className="mt-8 w-full max-w-2xl rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-5 py-4 text-left">
            <p className="text-sm font-medium text-[var(--voix-text-muted)]">Latest prompt</p>
            <p className="mt-2 line-clamp-2 text-base leading-7 text-[var(--voix-text-primary)]">
              {latestAssistantPrompt}
            </p>
          </div>
        )}

        {children && <div className="mt-6 w-full max-w-2xl">{children}</div>}
      </div>
    </section>
  );
}
