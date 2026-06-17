'use client';

import { type ReactNode, useState } from 'react';
import { CaretDownIcon, CaretUpIcon, ChartLineUpIcon, MicrophoneIcon } from '@phosphor-icons/react';
import { VoiceModeSelector } from '@/components/app/voice-mode-selector';
import { Button } from '@/components/ui/button';
import type { ChannelConfig } from '@/lib/channel-config';
import type { RuntimeConfig } from '@/lib/runtime-config';
import { type ScenarioConfig, resolveScenarioCopy } from '@/lib/scenario-config';

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
    <div className="dashboard-light relative min-h-svh w-full overflow-hidden bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
      {/* Soft ambient backdrop */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(900px circle at 12% -5%, rgba(99,102,241,0.10), transparent 55%), radial-gradient(700px circle at 100% 0%, rgba(16,185,129,0.08), transparent 50%)',
        }}
      />

      <section className="relative mx-auto flex min-h-svh w-full max-w-6xl items-center px-6 pt-24 pb-12 md:px-10">
        <div className="grid w-full gap-10 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-center">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-accent-soft)] px-4 py-1.5 text-xs font-semibold text-[var(--voix-accent-hover)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--voix-accent)]" />
              {scenario.platformLabel}
            </div>

            <h1 className="mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-balance text-[var(--voix-text-primary)] md:text-6xl">
              Run realtime{' '}
              <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
                voice workflows
              </span>
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--voix-text-secondary)]">
              {resolveScenarioCopy(scenario.landing.summary, channel)}
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-4 py-2 text-sm shadow-sm">
                <span className="text-[var(--voix-text-muted)]">Scenario</span>
                <span className="font-medium text-[var(--voix-text-primary)]">
                  {scenario.landing.name}
                </span>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-4 py-2 text-sm shadow-sm">
                <span className="text-[var(--voix-text-muted)]">Channel</span>
                <span className="font-medium text-[var(--voix-text-primary)]">{channel.label}</span>
              </div>
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Button
                size="lg"
                onClick={onStartCall}
                className="h-12 gap-2 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-[color:var(--voix-accent-foreground)] shadow-sm hover:bg-[color:var(--voix-accent-hover)]"
              >
                <MicrophoneIcon size={18} weight="fill" />
                {scenario.landing.primaryActionLabel}
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={onUseText}
                className="h-12 rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] px-7 text-sm font-medium text-[var(--voix-text-secondary)] shadow-sm hover:bg-[var(--voix-bg-subtle)]"
              >
                {scenario.landing.secondaryActionLabel}
              </Button>
              <a
                href="/dashboard"
                className="inline-flex h-12 items-center gap-2 rounded-full px-5 text-sm font-medium text-[var(--voix-text-secondary)] transition hover:bg-[var(--voix-bg-subtle)]"
              >
                <ChartLineUpIcon size={18} weight="bold" />
                View dashboard
              </a>
            </div>

            <p className="mt-4 text-sm text-[var(--voix-text-muted)]">
              {resolveScenarioCopy(scenario.landing.helper, channel)}
            </p>

            <div
              className="mt-8 rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-5"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-[var(--voix-text-primary)]">
                    Voice mode:{' '}
                    <span className="font-semibold text-[var(--voix-accent-hover)]">
                      {runtimeConfig.presetLabel}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
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
            <section
              className="rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <button
                type="button"
                onClick={() => setHowItWorksOpen((value) => !value)}
                aria-expanded={howItWorksOpen}
                className="flex w-full items-center justify-between gap-3 text-left"
              >
                <div>
                  <p className="text-sm font-semibold text-[var(--voix-text-primary)]">
                    How it works
                  </p>
                  <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
                    {resolveScenarioCopy(scenario.landing.howItWorksDescription, channel)}
                  </p>
                </div>
                <span className="text-[var(--voix-text-muted)]">
                  {howItWorksOpen ? <CaretUpIcon size={16} /> : <CaretDownIcon size={16} />}
                </span>
              </button>

              {howItWorksOpen && (
                <ol className="mt-4 space-y-3 text-sm text-[var(--voix-text-secondary)]">
                  {(resolveScenarioCopy(scenario.landing.howItWorksSteps, channel) as string[]).map(
                    (step, i) => (
                      <li key={step} className="flex gap-3">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--voix-accent-soft)] text-[11px] font-semibold text-[var(--voix-accent-hover)]">
                          {i + 1}
                        </span>
                        {step}
                      </li>
                    )
                  )}
                </ol>
              )}
            </section>

            <section
              className="rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <p className="text-sm font-semibold text-[var(--voix-text-primary)]">Coming next</p>
              <p className="mt-2 text-sm leading-6 text-[var(--voix-text-muted)]">
                {resolveScenarioCopy(scenario.landing.comingNextDescription, channel)}
              </p>
            </section>

            {developerDetails}
          </aside>
        </div>
      </section>
    </div>
  );
}
