'use client';

import { type ReactNode } from 'react';
import Link from 'next/link';
import { ArrowRight, BarChart3, Globe2, PhoneCall, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { ChartLineUpIcon, MicrophoneIcon } from '@phosphor-icons/react';
import { AgentPreview } from '@/components/app/agent-preview';
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

const FEATURES = [
  {
    icon: Zap,
    title: 'Real-time conversation',
    body: 'Sub-second responses with natural turn-taking. Customers talk to it like a person, not a phone tree.',
  },
  {
    icon: ShieldCheck,
    title: 'Orders you can trust',
    body: 'Every order is validated and persisted by the backend, and idempotent by design — never a double charge.',
  },
  {
    icon: BarChart3,
    title: 'Full observability',
    body: 'Every call is logged with transcript, sentiment, outcome and linked order. Reliability you can see.',
  },
  {
    icon: Globe2,
    title: 'Any voice engine',
    body: 'Switch between a classic STT-LLM-TTS pipeline, OpenAI Realtime, or Gemini Live — no code changes.',
  },
];

const STATS = [
  { value: '< 1s', label: 'Median response latency' },
  { value: '92%', label: 'Calls handled without a human' },
  { value: '24/7', label: 'Always answering, never on hold' },
  { value: '3', label: 'Swappable voice engines' },
];

export function LandingHero({
  scenario,
  channel,
  onStartCall,
  onUseText,
  runtimeConfig,
  onRuntimeConfigChange,
  developerDetails,
}: LandingHeroProps) {
  const steps = resolveScenarioCopy(scenario.landing.howItWorksSteps, channel) as string[];

  return (
    <div className="dashboard-light relative min-h-svh w-full overflow-hidden bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
      {/* Ambient backdrop */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(1100px circle at 8% -10%, rgba(99,102,241,0.12), transparent 50%), radial-gradient(900px circle at 100% -5%, rgba(139,92,246,0.10), transparent 45%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(15,23,42,0.05) 1px, transparent 0)',
          backgroundSize: '32px 32px',
          maskImage: 'linear-gradient(180deg, black, transparent 70%)',
          WebkitMaskImage: 'linear-gradient(180deg, black, transparent 70%)',
        }}
      />

      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-[var(--voix-border-subtle)] bg-[var(--voix-topbar-bg)] backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6 md:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--voix-accent)] text-base font-bold text-white shadow-sm">
              V
            </span>
            <span className="text-base font-semibold tracking-tight">VoixAI</span>
          </Link>
          <div className="hidden items-center gap-8 text-sm text-[var(--voix-text-secondary)] md:flex">
            <a href="#features" className="transition hover:text-[var(--voix-text-primary)]">
              Features
            </a>
            <a href="#how" className="transition hover:text-[var(--voix-text-primary)]">
              How it works
            </a>
            <a href="#try" className="transition hover:text-[var(--voix-text-primary)]">
              Try it live
            </a>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="hidden h-9 items-center gap-1.5 rounded-full px-4 text-sm font-medium text-[var(--voix-text-secondary)] transition hover:bg-[var(--voix-bg-subtle)] sm:inline-flex"
            >
              <ChartLineUpIcon size={16} weight="bold" />
              Dashboard
            </Link>
            <Button
              onClick={onStartCall}
              className="h-9 rounded-full bg-[color:var(--voix-accent)] px-4 text-sm font-semibold text-white shadow-sm hover:bg-[color:var(--voix-accent-hover)]"
            >
              Start demo
            </Button>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative mx-auto max-w-6xl px-6 pt-16 pb-20 md:px-8 md:pt-24">
        <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,460px)]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-3.5 py-1.5 text-xs font-medium text-[var(--voix-text-secondary)] shadow-sm">
              <Sparkles size={13} className="text-[var(--voix-accent)]" />
              {scenario.platformLabel}
            </div>

            <h1 className="mt-6 text-[2.6rem] leading-[1.05] font-semibold tracking-tight text-balance md:text-6xl">
              Answer every call.
              <br />
              <span className="bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-500 bg-clip-text text-transparent">
                Take every order.
              </span>{' '}
              Automatically.
            </h1>

            <p className="mt-5 max-w-xl text-lg leading-8 text-[var(--voix-text-secondary)]">
              {resolveScenarioCopy(scenario.landing.summary, channel)}
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button
                size="lg"
                onClick={onStartCall}
                className="h-12 gap-2 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-white shadow-[0_8px_24px_-8px_rgba(99,102,241,0.7)] transition hover:bg-[color:var(--voix-accent-hover)]"
              >
                <MicrophoneIcon size={18} weight="fill" />
                {scenario.landing.primaryActionLabel}
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={onUseText}
                className="h-12 rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] px-7 text-sm font-medium text-[var(--voix-text-secondary)] shadow-sm transition hover:bg-[var(--voix-bg-subtle)]"
              >
                {scenario.landing.secondaryActionLabel}
              </Button>
            </div>

            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-6">
              {STATS.slice(0, 3).map((stat) => (
                <div key={stat.label}>
                  <dt className="text-2xl font-semibold text-[var(--voix-text-primary)]">
                    {stat.value}
                  </dt>
                  <dd className="mt-1 text-xs leading-snug text-[var(--voix-text-muted)]">
                    {stat.label}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <AgentPreview />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative mx-auto max-w-6xl px-6 py-16 md:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold tracking-[0.18em] text-[var(--voix-accent)] uppercase">
            Why VoixAI
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            A voice agent built like production software
          </h2>
          <p className="mt-3 text-[var(--voix-text-secondary)]">
            Not a demo bot. Every order is validated, every call is observable, and the backend is
            always the source of truth.
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6 transition hover:-translate-y-0.5"
                style={{ boxShadow: 'var(--voix-card-shadow)' }}
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--voix-accent-soft)] text-[var(--voix-accent-hover)]">
                  <Icon size={20} />
                </span>
                <h3 className="mt-4 text-base font-semibold text-[var(--voix-text-primary)]">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[var(--voix-text-muted)]">
                  {feature.body}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Stats band */}
      <section className="relative mx-auto max-w-6xl px-6 py-8 md:px-8">
        <div
          className="grid grid-cols-2 gap-px overflow-hidden rounded-3xl border border-[var(--voix-border-subtle)] bg-[var(--voix-border-subtle)] md:grid-cols-4"
          style={{ boxShadow: 'var(--voix-card-shadow)' }}
        >
          {STATS.map((stat) => (
            <div key={stat.label} className="bg-[var(--voix-bg-elevated)] px-6 py-8 text-center">
              <p className="text-3xl font-semibold tracking-tight text-[var(--voix-text-primary)]">
                {stat.value}
              </p>
              <p className="mt-1.5 text-xs text-[var(--voix-text-muted)]">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Try it live */}
      <section id="try" className="relative mx-auto max-w-6xl px-6 py-16 md:px-8">
        <div
          className="overflow-hidden rounded-3xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)]"
          style={{ boxShadow: 'var(--voix-card-shadow)' }}
        >
          <div className="grid gap-8 p-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] md:p-10">
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--voix-accent)] uppercase">
                Try it live
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight md:text-3xl">
                Start talking with Gemini
              </h2>
              <p className="mt-3 text-sm leading-6 text-[var(--voix-text-secondary)]">
                {resolveScenarioCopy(scenario.landing.helper, channel)}
              </p>
              <p className="mt-4 text-sm text-[var(--voix-text-muted)]">
                Powered by:{' '}
                <span className="font-semibold text-[var(--voix-accent-hover)]">
                  Google Gemini Live
                </span>
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button
                  size="lg"
                  onClick={onStartCall}
                  className="h-12 gap-2 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-white shadow-sm hover:bg-[color:var(--voix-accent-hover)]"
                >
                  <PhoneCall size={17} />
                  {scenario.landing.primaryActionLabel}
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={onUseText}
                  className="h-12 rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] px-7 text-sm font-medium text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
                >
                  {scenario.landing.secondaryActionLabel}
                </Button>
              </div>
            </div>

            <div className="flex items-center justify-center rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-8">
              <div className="text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100">
                  <Sparkles size={28} className="text-indigo-600" />
                </div>
                <p className="mt-4 text-lg font-semibold text-[var(--voix-text-primary)]">
                  Gemini Live
                </p>
                <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
                  Native speech-to-speech
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="relative mx-auto max-w-6xl px-6 py-16 md:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold tracking-[0.18em] text-[var(--voix-accent)] uppercase">
            How it works
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            {resolveScenarioCopy(scenario.landing.howItWorksDescription, channel)}
          </h2>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => (
            <div
              key={step}
              className="relative rounded-2xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--voix-accent)] text-sm font-semibold text-white">
                {i + 1}
              </span>
              <p className="mt-4 text-sm leading-6 text-[var(--voix-text-secondary)]">{step}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center gap-5 rounded-3xl border border-[var(--voix-border-subtle)] bg-gradient-to-br from-[var(--voix-accent-soft)] to-[var(--voix-bg-elevated)] px-8 py-12 text-center">
          <h3 className="max-w-2xl text-2xl font-semibold tracking-tight md:text-3xl">
            See it answer a call in under a minute
          </h3>
          <p className="max-w-xl text-sm text-[var(--voix-text-secondary)]">
            Start the demo, place a quick order, then open the dashboard to watch the call,
            transcript and order appear in real time.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button
              size="lg"
              onClick={onStartCall}
              className="h-12 gap-2 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-white shadow-sm hover:bg-[color:var(--voix-accent-hover)]"
            >
              <MicrophoneIcon size={18} weight="fill" />
              {scenario.landing.primaryActionLabel}
            </Button>
            <Link
              href="/dashboard"
              className="inline-flex h-12 items-center gap-2 rounded-full border border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] px-7 text-sm font-medium text-[var(--voix-text-secondary)] transition hover:bg-[var(--voix-bg-subtle)]"
            >
              Open dashboard <ArrowRight size={16} />
            </Link>
          </div>
        </div>

        {developerDetails && <div className="mt-10">{developerDetails}</div>}
      </section>

      {/* Footer */}
      <footer className="relative border-t border-[var(--voix-border-subtle)]">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-[var(--voix-text-muted)] md:flex-row md:px-8">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--voix-accent)] text-xs font-bold text-white">
              V
            </span>
            <span className="font-medium text-[var(--voix-text-secondary)]">VoixAI</span>
            <span className="text-[var(--voix-text-muted)]">· Voice AI for inbound calls</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#features" className="transition hover:text-[var(--voix-text-secondary)]">
              Features
            </a>
            <Link href="/dashboard" className="transition hover:text-[var(--voix-text-secondary)]">
              Dashboard
            </Link>
            <span>© {new Date().getFullYear()} VoixAI</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
