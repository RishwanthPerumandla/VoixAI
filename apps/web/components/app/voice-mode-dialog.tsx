'use client';

import { X } from 'lucide-react';
import { MicrophoneIcon } from '@phosphor-icons/react';
import * as Dialog from '@radix-ui/react-dialog';
import { VoiceModeSelector } from '@/components/app/voice-mode-selector';
import { Button } from '@/components/ui/button';
import type { RuntimeConfig } from '@/lib/runtime-config';

interface VoiceModeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runtimeConfig: RuntimeConfig;
  onRuntimeConfigChange: (config: RuntimeConfig) => void;
  onStart: () => void;
  onUseText: () => void;
  startLabel: string;
  textLabel: string;
}

export function VoiceModeDialog({
  open,
  onOpenChange,
  runtimeConfig,
  onRuntimeConfigChange,
  onStart,
  onUseText,
  startLabel,
  textLabel,
}: VoiceModeDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-[90] bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content
          className="dashboard-light data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-1/2 left-1/2 z-[95] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6 text-[var(--voix-text-primary)] md:p-8"
          style={{ boxShadow: 'var(--voix-card-shadow-hover)' }}
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-xl font-semibold text-[var(--voix-text-primary)]">
                Choose a voice engine
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-[var(--voix-text-muted)]">
                Pick how the agent should sound and reason, then start the call. You can compare all
                three.
              </Dialog.Description>
            </div>
            <Dialog.Close className="rounded-full p-1.5 text-[var(--voix-text-muted)] transition hover:bg-[var(--voix-bg-subtle)] hover:text-[var(--voix-text-primary)]">
              <X size={18} />
            </Dialog.Close>
          </div>

          <div className="mt-5">
            <VoiceModeSelector config={runtimeConfig} onConfigChange={onRuntimeConfigChange} />
          </div>

          <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <Button
              variant="ghost"
              onClick={() => {
                onOpenChange(false);
                onUseText();
              }}
              className="h-11 rounded-full px-5 text-sm font-medium text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
            >
              {textLabel}
            </Button>
            <Button
              onClick={() => {
                onOpenChange(false);
                onStart();
              }}
              className="h-11 gap-2 rounded-full bg-[color:var(--voix-accent)] px-7 text-sm font-semibold text-white shadow-sm hover:bg-[color:var(--voix-accent-hover)]"
            >
              <MicrophoneIcon size={17} weight="fill" />
              {startLabel} · {runtimeConfig.presetLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
