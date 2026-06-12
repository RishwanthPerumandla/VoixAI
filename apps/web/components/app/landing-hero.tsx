'use client';

import { type ReactNode, useState } from 'react';
import { CaretDownIcon, CaretUpIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import type { RuntimeConfig } from '@/lib/runtime-config';
import { VoiceModeSelector } from '@/components/app/voice-mode-selector';
import { DeveloperDetails } from '@/components/app/developer-details';

interface LandingHeroProps {
  onStartCall: () => void;
  onUseText: () => void;
  runtimeConfig: RuntimeConfig;
  onRuntimeConfigChange: (config: RuntimeConfig) => void;
  developerDetails?: ReactNode;
}

export function LandingHero({
  onStartCall,
  onUseText,
  runtimeConfig,
  onRuntimeConfigChange,
  developerDetails,
}: LandingHeroProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [howItWorksOpen, setHowItWorksOpen] = useState(false);

  return (
    <section className="mx-auto flex min-h-[calc(100svh-7rem)] w-full max-w-6xl items-center px-6 pb-10 pt-24 md:px-10">
      <div className="grid w-full gap-10 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-center">
        <div className="max-w-3xl">
          <div className="inline-flex rounded-full border border-teal-400/20 bg-teal-400/10 px-4 py-2 text-xs font-medium text-teal-200">
            Voice-first ordering
          </div>
          <h1 className="mt-6 max-w-3xl text-balance text-4xl font-semibold tracking-tight text-slate-50 md:text-6xl">
            Place an order by voice
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
            Speak naturally, make changes, and confirm your mock order in seconds.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              size="lg"
              onClick={onStartCall}
              className="h-12 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-[color:var(--voix-accent-foreground)] hover:bg-[color:var(--voix-accent-hover)]"
            >
              Start voice order
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={onUseText}
              className="h-12 rounded-full border-white/12 bg-white/5 px-7 text-sm font-medium text-slate-100 hover:bg-white/10"
            >
              Use text instead
            </Button>
          </div>

          <p className="mt-4 text-sm text-slate-400">
            You can edit or confirm before checkout.
          </p>

          <div className="mt-8 rounded-[20px] border border-white/10 bg-white/5 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-slate-300">
                  Voice mode: <span className="font-medium text-slate-50">{runtimeConfig.presetLabel}</span>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSettingsOpen((value) => !value)}
                aria-expanded={settingsOpen}
                className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-sm text-slate-200 hover:bg-white/6"
              >
                Change
                {settingsOpen ? <CaretUpIcon size={14} /> : <CaretDownIcon size={14} />}
              </button>
            </div>

            {settingsOpen && (
              <div className="mt-4 space-y-4">
                <VoiceModeSelector config={runtimeConfig} onConfigChange={onRuntimeConfigChange} />
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl border border-white/8 bg-slate-950/35 p-4">
                    <p className="text-sm font-medium text-slate-50">Classic Voice</p>
                    <p className="mt-1 text-sm text-slate-400">Stable multi-step ordering</p>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-slate-950/35 p-4">
                    <p className="text-sm font-medium text-slate-50">OpenAI Realtime</p>
                    <p className="mt-1 text-sm text-slate-400">Fast native conversation</p>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-slate-950/35 p-4">
                    <p className="text-sm font-medium text-slate-50">Gemini Live</p>
                    <p className="mt-1 text-sm text-slate-400">Latest Gemini live audio path</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <section className="rounded-[28px] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/20">
            <button
              type="button"
              onClick={() => setHowItWorksOpen((value) => !value)}
              aria-expanded={howItWorksOpen}
              className="flex w-full items-center justify-between gap-3 text-left"
            >
              <div>
                <p className="text-sm font-semibold text-slate-50">How it works</p>
                <p className="mt-1 text-sm text-slate-400">A simple three-step voice ordering flow.</p>
              </div>
              {howItWorksOpen ? <CaretUpIcon size={16} /> : <CaretDownIcon size={16} />}
            </button>

            {howItWorksOpen && (
              <ol className="mt-4 space-y-3 text-sm text-slate-300">
                <li>1. Start a voice order</li>
                <li>2. Tell the assistant what you want</li>
                <li>3. Review and confirm</li>
              </ol>
            )}
          </section>

          {developerDetails}
        </aside>
      </div>
    </section>
  );
}
