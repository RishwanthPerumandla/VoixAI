'use client';

import { Check, Sparkles, TriangleAlert } from 'lucide-react';
import { useReducedMotion } from 'motion/react';
import { AudioVisualizer } from '@/components/agents-ui/blocks/agent-session-view-01/components/audio-visualizer';
import { cn } from '@/lib/shadcn/utils';
import type { UserFacingSessionState } from '@/components/app/session-status';

interface VoiceVisualizerProps {
  state: UserFacingSessionState;
  className?: string;
}

function getStateAccent(state: UserFacingSessionState) {
  switch (state) {
    case 'assistantSpeaking':
      return '#84c5ff';
    case 'thinking':
    case 'connecting':
      return '#a5b4fc';
    case 'readyToConfirm':
      return '#ffb77a';
    case 'complete':
      return '#8ae8bb';
    case 'error':
      return '#fb7185';
    case 'userSpeaking':
    case 'listening':
    default:
      return '#7ce9df';
  }
}

export function VoiceVisualizer({ state, className }: VoiceVisualizerProps) {
  const reduceMotion = useReducedMotion();
  const showVisualizer =
    state === 'listening' ||
    state === 'userSpeaking' ||
    state === 'assistantSpeaking' ||
    state === 'thinking' ||
    state === 'connecting';
  const overlayIcon =
    state === 'complete' ? (
      <Check className="h-8 w-8 text-white" />
    ) : state === 'error' ? (
      <TriangleAlert className="h-8 w-8 text-white" />
    ) : state === 'readyToConfirm' ? (
      <Sparkles className="h-7 w-7 text-white/90" />
    ) : null;

  return (
    <div
      className={cn(
        'relative flex h-[260px] w-[260px] items-center justify-center md:h-[320px] md:w-[320px]',
        className
      )}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 rounded-full blur-3xl"
        style={{
          background: `radial-gradient(circle, ${getStateAccent(state)}33 0%, rgba(7,17,31,0) 68%)`,
        }}
      />
      <div className="absolute inset-[18px] rounded-full border border-white/10" />
      <div className="absolute inset-[34px] rounded-full border border-white/8" />

      <div className="relative z-10 flex h-[188px] w-[188px] items-center justify-center overflow-hidden rounded-full border border-white/12 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.18),rgba(255,255,255,0.04)_28%,rgba(7,17,31,0.12)_62%,rgba(7,17,31,0.92)_100%)] shadow-[0_30px_120px_rgba(0,0,0,0.45)] md:h-[220px] md:w-[220px]">
        {showVisualizer ? (
          <AudioVisualizer
            isChatOpen={false}
            audioVisualizerType="bar"
            audioVisualizerBarCount={5}
            audioVisualizerColor={getStateAccent(state) as `#${string}`}
            className={cn(
              'pointer-events-none scale-[0.46] md:scale-[0.5]',
              reduceMotion && 'opacity-90'
            )}
          />
        ) : (
          <div className="flex items-center justify-center">{overlayIcon}</div>
        )}
      </div>
    </div>
  );
}
