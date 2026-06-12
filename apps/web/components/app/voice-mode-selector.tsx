'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { RuntimeConfig } from '@/lib/runtime-config';
import { RUNTIME_PRESETS, getRuntimePresetById } from '@/lib/runtime-config';

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
    <Select
      value={config.presetId}
      onValueChange={(presetId) => {
        const preset = getRuntimePresetById(presetId);
        if (preset) onConfigChange(preset.config);
      }}
      disabled={disabled}
    >
      <SelectTrigger
        className="h-10 min-w-[188px] rounded-full border-white/10 bg-white/5 px-4 text-sm text-slate-50"
        aria-label="Choose voice mode"
      >
        <SelectValue placeholder="Choose voice mode" />
      </SelectTrigger>
      <SelectContent className="border-white/10 bg-slate-950 text-slate-50">
        {RUNTIME_PRESETS.map((preset) => (
          <SelectItem key={preset.id} value={preset.id} className="py-2.5">
            <div className="flex flex-col">
              <span className="text-sm font-medium">{preset.label}</span>
              <span className="text-xs text-slate-400">{preset.description}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
