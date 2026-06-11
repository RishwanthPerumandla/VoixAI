'use client';

import {
  DEFAULT_RUNTIME_CONFIG,
  RUNTIME_PRESETS,
  buildRuntimeConfigSummary,
  type RuntimeConfig,
} from '@/lib/runtime-config';
import { cn } from '@/lib/shadcn/utils';

interface RuntimeConfigPanelProps {
  config: RuntimeConfig;
  activeConfig?: RuntimeConfig | null;
  connected?: boolean;
  compact?: boolean;
  className?: string;
  onConfigChange: (config: RuntimeConfig) => void;
}

function SummaryPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-muted/25 px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

export function RuntimeConfigPanel({
  config,
  activeConfig,
  connected = false,
  compact = false,
  className,
  onConfigChange,
}: RuntimeConfigPanelProps) {
  const appliedConfig = activeConfig ?? config ?? DEFAULT_RUNTIME_CONFIG;
  const selectedSummary = buildRuntimeConfigSummary(config);

  return (
    <section
      className={cn(
        'rounded-[28px] border border-border/70 bg-background/88 p-5 shadow-xl shadow-black/5 backdrop-blur',
        className
      )}
    >
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-foreground">
            Voice Mode
          </p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Pick how the next conversation should sound and respond.
          </p>
        </div>
        <div className="rounded-full border border-border/70 bg-muted/25 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
          {connected ? 'Switches on next call' : 'Ready for next call'}
        </div>
      </div>

      <div className={cn('mt-4 grid gap-3', compact ? 'md:grid-cols-3' : 'lg:grid-cols-3')}>
        {RUNTIME_PRESETS.map((preset) => {
          const isSelected = preset.id === config.presetId;
          const isActive = preset.id === appliedConfig.presetId;

          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => onConfigChange(preset.config)}
              className={cn(
                'rounded-[24px] border p-4 text-left transition-all',
                isSelected
                  ? 'border-primary bg-primary/8 shadow-md'
                  : 'border-border/70 bg-muted/15 hover:border-primary/40 hover:bg-primary/5'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-foreground">{preset.label}</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {preset.description}
                  </p>
                </div>
                <span
                  className={cn(
                    'rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em]',
                    isSelected
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-background text-muted-foreground'
                  )}
                >
                  {isActive ? 'Live' : 'Ready'}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      <div className={cn('mt-4 grid gap-3', compact ? 'sm:grid-cols-3' : 'md:grid-cols-3')}>
        <SummaryPill label="Mode" value={selectedSummary.engine} />
        <SummaryPill label="Model" value={selectedSummary.llm} />
        <SummaryPill label="Speech" value={`${selectedSummary.stt} / ${selectedSummary.tts}`} />
      </div>

      {appliedConfig.fallbackReason && (
        <p className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm leading-6 text-amber-800 dark:text-amber-200">
          {appliedConfig.fallbackReason}
        </p>
      )}
    </section>
  );
}
