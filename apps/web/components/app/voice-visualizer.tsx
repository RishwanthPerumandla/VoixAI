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
      <div className="absolute inset-[18px] rounded-full border border-white/10" />
      <div className="absolute inset-[34px] rounded-full border border-white/8" />

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

      {/* Core orb */}
      <motion.div
        className="relative z-10 flex h-[188px] w-[188px] items-center justify-center overflow-hidden rounded-full border border-white/12 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.18),rgba(255,255,255,0.04)_28%,rgba(7,17,31,0.12)_62%,rgba(7,17,31,0.92)_100%)] md:h-[220px] md:w-[220px]"
        style={{ boxShadow: `0 0 60px -12px ${accent}66, 0 30px 120px rgba(0,0,0,0.45)` }}
        animate={reduceMotion ? undefined : { scale: isActive ? [1, 1.025, 1] : 1 }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
      >
        {showVisualizer ? (
          <AudioVisualizer
            isChatOpen={false}
            audioVisualizerType="bar"
            audioVisualizerBarCount={5}
            audioVisualizerColor={accent as `#${string}`}
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
