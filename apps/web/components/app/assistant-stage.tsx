'use client';

import { type ReactNode } from 'react';
import { VoiceVisualizer } from '@/components/app/voice-visualizer';
import {
  getSessionStatusContent,
  type UserFacingSessionState,
} from '@/components/app/session-status';
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
        'relative overflow-hidden rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,15,28,0.96),rgba(13,23,39,0.92))] p-6 shadow-[0_30px_120px_rgba(0,0,0,0.35)] md:p-8',
        className
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(75,175,255,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(48,201,182,0.10),transparent_22%)]" />
      <div className="relative flex flex-col items-center text-center">
        <div className="inline-flex rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium tracking-[0.16em] text-slate-300">
          Realtime voice stage
        </div>
        <VoiceVisualizer state={state} className="mt-6" />
        <p className="mt-7 text-3xl font-semibold tracking-tight text-slate-50 md:text-[2.15rem]">
          {copy.label}
        </p>
        <p className="mt-3 max-w-xl text-base leading-7 text-slate-300">
          {state === 'listening' || state === 'userSpeaking'
            ? 'Speak naturally. You can change anything before confirming.'
            : copy.helper}
        </p>

        {latestAssistantPrompt && (
          <div className="mt-8 w-full max-w-2xl rounded-[24px] border border-white/10 bg-white/[0.045] px-5 py-4 text-left backdrop-blur-sm">
            <p className="text-sm font-medium text-slate-200">Latest prompt</p>
            <p className="mt-2 line-clamp-2 text-base leading-7 text-slate-100">
              {latestAssistantPrompt}
            </p>
          </div>
        )}

        {children && <div className="mt-6 w-full max-w-2xl">{children}</div>}
      </div>
    </section>
  );
}
