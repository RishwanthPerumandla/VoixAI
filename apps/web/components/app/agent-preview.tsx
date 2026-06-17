'use client';

import { Check, Phone } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';

/**
 * A self-contained, decorative "live call" preview for the marketing hero.
 *
 * Intentionally does NOT depend on LiveKit/AudioVisualizer — it animates on its
 * own so the landing page always shows a lively product shot, even before a
 * session is connected.
 */
export function AgentPreview() {
  const reduceMotion = useReducedMotion();
  const bars = [0.45, 0.8, 0.35, 0.95, 0.6, 0.85, 0.4];

  return (
    <div className="relative">
      {/* Ambient glow behind the device */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-6 rounded-[44px] opacity-70 blur-2xl"
        style={{
          background:
            'radial-gradient(60% 60% at 30% 20%, rgba(99,102,241,0.35), transparent 70%), radial-gradient(50% 50% at 90% 90%, rgba(139,92,246,0.30), transparent 70%)',
        }}
      />

      <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-gradient-to-b from-[#0d1526] to-[#0a1019] p-5 shadow-[0_40px_120px_-30px_rgba(15,23,42,0.55)]">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-300">
              <Phone size={16} />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-100">Voix Wings · Downtown</p>
              <p className="text-[11px] text-slate-400">Inbound call · auto-answered</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/12 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </span>
            Live
          </span>
        </div>

        {/* Orb */}
        <div className="relative my-6 flex h-40 items-center justify-center">
          {!reduceMotion &&
            [0, 1, 2].map((i) => (
              <motion.span
                key={i}
                aria-hidden="true"
                className="absolute rounded-full border border-indigo-400/30"
                style={{ width: 96, height: 96 }}
                initial={{ scale: 0.85, opacity: 0.5 }}
                animate={{ scale: 1.9, opacity: 0 }}
                transition={{ duration: 2.4, repeat: Infinity, ease: 'easeOut', delay: i * 0.7 }}
              />
            ))}
          <motion.div
            className="relative flex h-24 w-24 items-center justify-center rounded-full"
            style={{
              background:
                'radial-gradient(circle at 32% 28%, #a5b4fc, #6366f1 42%, #4338ca 72%, #312e81)',
              boxShadow:
                '0 0 50px -8px rgba(99,102,241,0.7), inset 0 2px 12px rgba(255,255,255,0.35)',
            }}
            animate={reduceMotion ? undefined : { scale: [1, 1.05, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            <div className="flex items-end gap-1">
              {bars.map((h, i) => (
                <motion.span
                  key={i}
                  className="w-1 rounded-full bg-white/90"
                  style={{ height: 10 + h * 22 }}
                  animate={reduceMotion ? undefined : { scaleY: [0.5, 1, 0.6, 0.95, 0.5] }}
                  transition={{
                    duration: 1.1,
                    repeat: Infinity,
                    ease: 'easeInOut',
                    delay: i * 0.09,
                  }}
                />
              ))}
            </div>
          </motion.div>
        </div>

        {/* Faux transcript */}
        <div className="space-y-2">
          <div className="max-w-[82%] rounded-2xl rounded-tl-sm bg-white/[0.06] px-3.5 py-2 text-[13px] text-slate-200">
            Thanks for calling Voix Wings! What can I get started for you?
          </div>
          <div className="ml-auto max-w-[82%] rounded-2xl rounded-tr-sm bg-indigo-500/90 px-3.5 py-2 text-[13px] text-white">
            Ten boneless, garlic parmesan, and a large fry.
          </div>
        </div>

        {/* Order confirmation chip */}
        <div className="mt-4 flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.04] px-3.5 py-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-400/15 text-emerald-300">
              <Check size={15} />
            </span>
            <div>
              <p className="text-[13px] font-semibold text-slate-100">Order #MOCK-4821 placed</p>
              <p className="text-[11px] text-slate-400">Validated by backend · idempotent</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-slate-100">$24.50</p>
            <p className="text-[11px] text-slate-400">ETA 18 min</p>
          </div>
        </div>
      </div>
    </div>
  );
}
