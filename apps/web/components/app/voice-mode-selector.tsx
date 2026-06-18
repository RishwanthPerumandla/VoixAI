'use client';

import type { RuntimeConfig } from '@/lib/runtime-config';
import { RUNTIME_PRESETS, getRuntimePresetById } from '@/lib/runtime-config';
import { cn } from '@/lib/shadcn/utils';

interface VoiceModeSelectorProps {
  config: RuntimeConfig;
  disabled?: boolean;
  onConfigChange: (config: RuntimeConfig) => void;
}

export function VoiceModeSelector({
  config,
  disabled = false,
  onConfigChange,
}: VoiceModeSelectorProps) {
  return (
    <div className="grid gap-3 md:grid-cols-3" role="radiogroup" aria-label="Choose voice mode">
      {RUNTIME_PRESETS.map((preset) => {
        const isSelected = preset.id === config.presetId;

        return (
          <button
            key={preset.id}
            type="button"
            role="radio"
            aria-checked={isSelected}
            disabled={disabled}
            onClick={() => {
              const nextPreset = getRuntimePresetById(preset.id);
              if (nextPreset) onConfigChange(nextPreset.config);
            }}
            className={cn(
              'rounded-[22px] border p-4 text-left transition focus-visible:ring-2 focus-visible:ring-[color:var(--voix-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--voix-bg-elevated)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60',
              isSelected
                ? 'border-[color:var(--voix-accent)] bg-[color:color-mix(in_srgb,var(--voix-accent)_12%,transparent)] shadow-[0_0_0_1px_color-mix(in_srgb,var(--voix-accent)_30%,transparent)]'
                : 'border-[color:var(--voix-border-subtle)] bg-[color:var(--voix-bg-subtle)] hover:border-[color:var(--voix-border-strong)]'
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-[color:var(--voix-text-primary)]">
                  {preset.label}
                </p>
                <p className="mt-2 text-sm leading-6 text-[color:var(--voix-text-muted)]">
                  {preset.description}
                </p>
              </div>
              <span
                className={cn(
                  'mt-0.5 h-4 w-4 shrink-0 rounded-full border',
                  isSelected
                    ? 'border-[color:var(--voix-accent)] bg-[color:var(--voix-accent)]'
                    : 'border-[color:var(--voix-border-strong)] bg-transparent'
                )}
                aria-hidden="true"
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}
