'use client';

import { memo } from 'react';
import { Check, Sparkles, TriangleAlert } from 'lucide-react';
import { useReducedMotion } from 'motion/react';
import { AudioVisualizer } from '@/components/agents-ui/blocks/agent-session-view-01/components/audio-visualizer';
import type { UserFacingSessionState } from '@/components/app/session-status';
import { cn } from '@/lib/shadcn/utils';

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

export const VoiceVisualizer = memo(function VoiceVisualizer({ state, className }: VoiceVisualizerProps) {
  const reduceMotion = useReducedMotion();
  const accent = getStateAccent(state);

  const isActive =
    state === 'listening' ||
    state === 'userSpeaking' ||
    state === 'assistantSpeaking' ||
    state === 'thinking' ||
    state === 'connecting';
  const showVisualizer = isActive;
  const isAgentDriving = state === 'assistantSpeaking' || state === 'thinking';
  const isSpinning = state === 'thinking' || state === 'connecting';

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
      {/* Breathing ambient glow — CSS animation */}
      <div
        aria-hidden="true"
        className={cn(
          'absolute inset-0 rounded-full blur-3xl',
          !reduceMotion && isActive && 'animate-pulse'
        )}
        style={{
          background: `radial-gradient(circle, ${accent}38 0%, rgba(7,17,31,0) 68%)`,
          animationDuration: isActive ? '2.4s' : '4s',
        }}
      />

      {/* Expanding ripple rings — CSS only, max 2 for perf */}
      {isActive && !reduceMotion && (
        <>
          <div
            aria-hidden="true"
            className="absolute rounded-full border animate-ping"
            style={{
              width: 188,
              height: 188,
              borderColor: `${accent}66`,
              animationDuration: isAgentDriving ? '2.2s' : '2.8s',
            }}
          />
          <div
            aria-hidden="true"
            className="absolute rounded-full border animate-ping"
            style={{
              width: 188,
              height: 188,
              borderColor: `${accent}44`,
              animationDuration: isAgentDriving ? '2.2s' : '2.8s',
              animationDelay: '0.6s',
            }}
          />
        </>
      )}

      {/* Static guide rings */}
      <div className="absolute inset-[18px] rounded-full border border-slate-900/10" />
      <div className="absolute inset-[34px] rounded-full border border-slate-900/[0.06]" />

      {/* Rotating gradient halo — CSS animation */}
      {isSpinning && !reduceMotion && (
        <div
          aria-hidden="true"
          className="absolute inset-[10px] rounded-full animate-spin"
          style={{
            background: `conic-gradient(from 0deg, transparent 0deg, ${accent}00 200deg, ${accent}aa 320deg, transparent 360deg)`,
            maskImage:
              'radial-gradient(circle, transparent 60%, black 62%, black 72%, transparent 74%)',
            WebkitMaskImage:
              'radial-gradient(circle, transparent 60%, black 62%, black 72%, transparent 74%)',
            animationDuration: '3.2s',
          }}
        />
      )}

      {/* Core orb */}
      <div
        className={cn(
          'relative z-10 flex h-[188px] w-[188px] items-center justify-center overflow-hidden rounded-full md:h-[220px] md:w-[220px]',
          !reduceMotion && isActive && 'animate-pulse'
        )}
        style={{
          background: `radial-gradient(circle at 32% 26%, rgba(255,255,255,0.92), ${accent} 46%, color-mix(in oklab, ${accent} 78%, black) 100%)`,
          boxShadow: `0 0 70px -10px ${accent}88, inset 0 3px 18px rgba(255,255,255,0.45), inset 0 -10px 24px rgba(0,0,0,0.18)`,
          animationDuration: '1.8s',
        }}
      >
        {showVisualizer ? (
          <AudioVisualizer
            isChatOpen={false}
            audioVisualizerType="bar"
            audioVisualizerBarCount={5}
            audioVisualizerColor={'#ffffff'}
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
});
