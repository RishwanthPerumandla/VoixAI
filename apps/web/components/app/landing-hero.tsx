'use client';

import { type ReactNode, useState } from 'react';
import { CaretDownIcon, CaretUpIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import type { RuntimeConfig } from '@/lib/runtime-config';
import type { ChannelConfig } from '@/lib/channel-config';
import { resolveScenarioCopy, type ScenarioConfig } from '@/lib/scenario-config';
import { VoiceModeSelector } from '@/components/app/voice-mode-selector';
import { DeveloperDetails } from '@/components/app/developer-details';

interface LandingHeroProps {
  scenario: ScenarioConfig;
  channel: ChannelConfig;
  onStartCall: () => void;
  onUseText: () => void;
  runtimeConfig: RuntimeConfig;
  onRuntimeConfigChange: (config: RuntimeConfig) => void;
  developerDetails?: ReactNode;
}

export function LandingHero({
  scenario,
  channel,
  onStartCall,
  onUseText,
  runtimeConfig,
  onRuntimeConfigChange,
  developerDetails,
}: LandingHeroProps) {
  const [howItWorksOpen, setHowItWorksOpen] = useState(false);

  return (
    <section className="mx-auto flex min-h-[calc(100svh-7rem)] w-full max-w-6xl items-center px-6 pb-10 pt-24 md:px-10">
      <div className="grid w-full gap-10 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-center">
        <div className="max-w-3xl">
          <div className="inline-flex rounded-full border border-teal-400/20 bg-teal-400/10 px-4 py-2 text-xs font-medium text-teal-200">
            {scenario.platformLabel}
          </div>
          <h1 className="mt-6 max-w-3xl text-balance text-4xl font-semibold tracking-tight text-slate-50 md:text-6xl">
            Run realtime voice workflows
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
            {resolveScenarioCopy(scenario.landing.summary, channel)}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.045] px-4 py-2 text-sm text-slate-200">
              <span className="text-slate-400">Scenario</span>
              <span className="font-medium text-slate-50">{scenario.landing.name}</span>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.045] px-4 py-2 text-sm text-slate-200">
              <span className="text-slate-400">Channel</span>
              <span className="font-medium text-slate-50">{channel.label}</span>
            </div>
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              size="lg"
              onClick={onStartCall}
              className="h-12 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-[color:var(--voix-accent-foreground)] hover:bg-[color:var(--voix-accent-hover)]"
            >
              {scenario.landing.primaryActionLabel}
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={onUseText}
              className="h-12 rounded-full border-white/12 bg-white/5 px-7 text-sm font-medium text-slate-100 hover:bg-white/10"
            >
              {scenario.landing.secondaryActionLabel}
            </Button>
          </div>

          <p className="mt-4 text-sm text-slate-400">
            {resolveScenarioCopy(scenario.landing.helper, channel)}
          </p>

          <div className="mt-8 rounded-[20px] border border-white/10 bg-white/5 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-200">
                  Voice mode: <span className="font-medium text-slate-50">{runtimeConfig.presetLabel}</span>
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  Choose how this session should sound before you start.
                </p>
              </div>
            </div>

            <div className="mt-4">
              <VoiceModeSelector config={runtimeConfig} onConfigChange={onRuntimeConfigChange} />
            </div>
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
                <p className="mt-1 text-sm text-slate-400">
                  {resolveScenarioCopy(scenario.landing.howItWorksDescription, channel)}
                </p>
              </div>
              {howItWorksOpen ? <CaretUpIcon size={16} /> : <CaretDownIcon size={16} />}
            </button>

            {howItWorksOpen && (
              <ol className="mt-4 space-y-3 text-sm text-slate-300">
                {(resolveScenarioCopy(scenario.landing.howItWorksSteps, channel) as string[]).map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            )}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/20">
            <p className="text-sm font-semibold text-slate-50">Coming next</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              {resolveScenarioCopy(scenario.landing.comingNextDescription, channel)}
            </p>
          </section>

          {developerDetails}
        </aside>
      </div>
    </section>
  );
}
