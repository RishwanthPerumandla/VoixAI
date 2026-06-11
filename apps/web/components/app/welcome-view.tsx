import { Button } from '@/components/ui/button';
import { type ReactNode } from 'react';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-fg0 size-12 shrink-0"
    >
      <path
        d="M15 24V40C15 40.7957 14.6839 41.5587 14.1213 42.1213C13.5587 42.6839 12.7956 43 12 43C11.2044 43 10.4413 42.6839 9.87868 42.1213C9.31607 41.5587 9 40.7957 9 40V24C9 23.2044 9.31607 22.4413 9.87868 21.8787C10.4413 21.3161 11.2044 21 12 21C12.7956 21 13.5587 21.3161 14.1213 21.8787C14.6839 22.4413 15 23.2044 15 24ZM22 5C21.2044 5 20.4413 5.31607 19.8787 5.87868C19.3161 6.44129 19 7.20435 19 8V56C19 56.7957 19.3161 57.5587 19.8787 58.1213C20.4413 58.6839 21.2044 59 22 59C22.7956 59 23.5587 58.6839 24.1213 58.1213C24.6839 57.5587 25 56.7957 25 56V8C25 7.20435 24.6839 6.44129 24.1213 5.87868C23.5587 5.31607 22.7956 5 22 5ZM32 13C31.2044 13 30.4413 13.3161 29.8787 13.8787C29.3161 14.4413 29 15.2044 29 16V48C29 48.7957 29.3161 49.5587 29.8787 50.1213C30.4413 50.6839 31.2044 51 32 51C32.7956 51 33.5587 50.6839 34.1213 50.1213C34.6839 49.5587 35 48.7957 35 48V16C35 15.2044 34.6839 14.4413 34.1213 13.8787C33.5587 13.3161 32.7956 13 32 13ZM42 21C41.2043 21 40.4413 21.3161 39.8787 21.8787C39.3161 22.4413 39 23.2044 39 24V40C39 40.7957 39.3161 41.5587 39.8787 42.1213C40.4413 42.6839 41.2043 43 42 43C42.7957 43 43.5587 42.6839 44.1213 42.1213C44.6839 41.5587 45 40.7957 45 40V24C45 23.2044 44.6839 22.4413 44.1213 21.8787C43.5587 21.3161 42.7957 21 42 21ZM52 17C51.2043 17 50.4413 17.3161 49.8787 17.8787C49.3161 18.4413 49 19.2044 49 20V44C49 44.7957 49.3161 45.5587 49.8787 46.1213C50.4413 46.6839 51.2043 47 52 47C52.7957 47 53.5587 46.6839 54.1213 46.1213C54.6839 45.5587 55 44.7957 55 44V20C55 19.2044 54.6839 18.4413 54.1213 17.8787C53.5587 17.3161 52.7957 17 52 17Z"
        fill="currentColor"
      />
    </svg>
  );
}

interface WelcomeViewProps {
  pageTitle: string;
  pageDescription: string;
  startButtonText: string;
  connectionStatusLabel: string;
  onStartCall: () => void;
  runtimePanel?: ReactNode;
}

export const WelcomeView = ({
  pageTitle,
  pageDescription,
  startButtonText,
  connectionStatusLabel,
  onStartCall,
  runtimePanel,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const demoSteps = [
    'Choose a voice mode before you begin.',
    'Start the call and allow microphone access.',
    'Place a short order, then change one detail.',
    'Ask for a recap and confirm the mock order.',
  ];

  return (
    <div ref={ref} className="relative min-h-svh overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,44,242,0.16),_transparent_38%),linear-gradient(180deg,_rgba(255,255,255,0.98),_rgba(243,244,246,0.92))] dark:bg-[radial-gradient(circle_at_top,_rgba(31,213,249,0.16),_transparent_35%),linear-gradient(180deg,_rgba(10,10,10,0.98),_rgba(17,24,39,0.94))]" />

      <section className="relative mx-auto flex min-h-svh max-w-6xl flex-col justify-center px-6 pb-24 pt-28 md:px-10">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(420px,520px)] xl:items-start">
          <div className="max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-3 rounded-full border bg-background/85 px-4 py-3 shadow-sm backdrop-blur">
              <WelcomeImage />
              <span className="text-muted-foreground font-mono text-[11px] tracking-[0.24em] uppercase">
                VoixAI Voice Demo
              </span>
            </div>

            <h1 className="text-foreground max-w-3xl text-balance text-4xl font-semibold tracking-tight md:text-6xl">
              {pageTitle}
            </h1>
            <p className="text-muted-foreground mt-5 max-w-2xl text-base leading-7 md:text-lg">
              {pageDescription}
            </p>

            <p className="mt-6 inline-flex rounded-full border bg-background/85 px-4 py-2 font-mono text-[11px] uppercase tracking-wide text-muted-foreground backdrop-blur">
              Status: {connectionStatusLabel}
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Button
                size="lg"
                onClick={onStartCall}
                className="h-14 min-w-64 rounded-full px-8 font-mono text-xs font-bold tracking-[0.24em] uppercase"
              >
                {startButtonText}
              </Button>
              <p className="text-muted-foreground max-w-sm text-sm leading-6">
                Speak naturally, make one correction, and confirm the mock order when it sounds right.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {runtimePanel}
            <aside className="rounded-[28px] border bg-background/88 p-6 shadow-xl shadow-black/5 backdrop-blur">
              <p className="text-foreground font-mono text-[11px] tracking-[0.24em] uppercase">
                Quick Flow
              </p>
              <ul className="mt-4 space-y-3">
                {demoSteps.map((step, index) => (
                  <li key={step} className="flex gap-3">
                    <span className="text-foreground mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border font-mono text-xs">
                      {index + 1}
                    </span>
                    <span className="text-muted-foreground text-sm leading-6">{step}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-6 rounded-2xl border bg-muted/35 p-4">
                <p className="text-foreground text-sm font-medium">Suggested opener</p>
                <p className="text-muted-foreground mt-2 text-sm leading-6">
                  "Hi, I want ten lemon pepper wings for pickup."
                </p>
              </div>
            </aside>
          </div>
        </div>
      </section>
    </div>
  );
};
