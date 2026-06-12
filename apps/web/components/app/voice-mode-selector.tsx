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
    <div
      className="grid gap-3 md:grid-cols-3"
      role="radiogroup"
      aria-label="Choose voice mode"
    >
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
              'rounded-[22px] border p-4 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--voix-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-60',
              isSelected
                ? 'border-[color:var(--voix-accent)] bg-[color:color-mix(in_srgb,var(--voix-accent)_14%,transparent)] shadow-[0_0_0_1px_color-mix(in_srgb,var(--voix-accent)_35%,transparent)]'
                : 'border-white/8 bg-slate-950/35 hover:border-white/16 hover:bg-white/[0.04]'
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-50">{preset.label}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{preset.description}</p>
              </div>
              <span
                className={cn(
                  'mt-0.5 h-4 w-4 rounded-full border',
                  isSelected
                    ? 'border-[color:var(--voix-accent)] bg-[color:var(--voix-accent)]'
                    : 'border-white/20 bg-transparent'
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
