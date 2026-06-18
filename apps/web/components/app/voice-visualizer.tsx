'use client';

import { Check, Sparkles, TriangleAlert } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
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

export function VoiceVisualizer({ state, className }: VoiceVisualizerProps) {
  const reduceMotion = useReducedMotion();
  const accent = getStateAccent(state);

  const isActive =
    state === 'listening' ||
    state === 'userSpeaking' ||
    state === 'assistantSpeaking' ||
    state === 'thinking' ||
    state === 'connecting';
  const showVisualizer = isActive;
  // The agent driving the conversation gets a livelier ripple than idle listening.
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
      {/* Breathing ambient glow */}
      <motion.div
        aria-hidden="true"
        className="absolute inset-0 rounded-full blur-3xl"
        style={{ background: `radial-gradient(circle, ${accent}38 0%, rgba(7,17,31,0) 68%)` }}
        animate={
          reduceMotion
            ? undefined
            : {
                scale: isActive ? [1, 1.12, 1] : [1, 1.04, 1],
                opacity: isActive ? [0.7, 1, 0.7] : [0.5, 0.7, 0.5],
              }
        }
        transition={{ duration: isActive ? 2.4 : 4, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Expanding ripple rings — only while a turn is in progress */}
      {isActive &&
        !reduceMotion &&
        [0, 1, 2].map((i) => (
          <motion.div
            key={i}
            aria-hidden="true"
            className="absolute rounded-full border"
            style={{ width: 188, height: 188, borderColor: `${accent}66` }}
            initial={{ scale: 0.82, opacity: 0.55 }}
            animate={{ scale: 1.55, opacity: 0 }}
            transition={{
              duration: isAgentDriving ? 2.2 : 2.8,
              repeat: Infinity,
              ease: 'easeOut',
              delay: i * (isAgentDriving ? 0.55 : 0.75),
            }}
          />
        ))}

      {/* Static guide rings */}
      <div className="absolute inset-[18px] rounded-full border border-slate-900/10" />
      <div className="absolute inset-[34px] rounded-full border border-slate-900/[0.06]" />

      {/* Slowly rotating gradient halo for thinking/connecting */}
      {isSpinning && !reduceMotion && (
        <motion.div
          aria-hidden="true"
          className="absolute inset-[10px] rounded-full"
          style={{
            background: `conic-gradient(from 0deg, transparent 0deg, ${accent}00 200deg, ${accent}aa 320deg, transparent 360deg)`,
            maskImage:
              'radial-gradient(circle, transparent 60%, black 62%, black 72%, transparent 74%)',
            WebkitMaskImage:
              'radial-gradient(circle, transparent 60%, black 62%, black 72%, transparent 74%)',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 3.2, repeat: Infinity, ease: 'linear' }}
        />
      )}

      {/* Core orb — a glossy, state-tinted sphere that reads on a light stage */}
      <motion.div
        className="relative z-10 flex h-[188px] w-[188px] items-center justify-center overflow-hidden rounded-full md:h-[220px] md:w-[220px]"
        style={{
          background: `radial-gradient(circle at 32% 26%, rgba(255,255,255,0.92), ${accent} 46%, color-mix(in oklab, ${accent} 78%, black) 100%)`,
          boxShadow: `0 0 70px -10px ${accent}88, inset 0 3px 18px rgba(255,255,255,0.45), inset 0 -10px 24px rgba(0,0,0,0.18)`,
        }}
        animate={reduceMotion ? undefined : { scale: isActive ? [1, 1.025, 1] : 1 }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
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
      </motion.div>
    </div>
  );
}
