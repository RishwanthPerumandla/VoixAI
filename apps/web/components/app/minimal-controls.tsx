'use client';

import { Track } from 'livekit-client';
import { MicIcon, MicOffIcon } from 'lucide-react';
import { useChat } from '@livekit/components-react';
import { AgentTrackToggle } from '@/components/agents-ui/agent-track-toggle';
import { TextFallbackInput } from '@/components/app/text-fallback-input';
import { cn } from '@/lib/shadcn/utils';

interface MinimalControlsProps {
  microphoneEnabled: boolean;
  microphonePending: boolean;
  onToggleMicrophone: (enabled: boolean) => Promise<unknown> | void;
  className?: string;
}

export function MinimalControls({
  microphoneEnabled,
  microphonePending,
  onToggleMicrophone,
  className,
}: MinimalControlsProps) {
  const { send } = useChat();

  return (
    <div className={cn('space-y-3', className)}>
      <TextFallbackInput onSend={send} />

      <div className="flex items-center gap-2">
        <AgentTrackToggle
          source={Track.Source.Microphone}
          pressed={microphoneEnabled}
          pending={microphonePending}
          onPressedChange={(enabled) => {
            void onToggleMicrophone(enabled);
          }}
          className={cn(
            'h-9 rounded-full border px-3 text-xs font-medium transition outline-none',
            microphoneEnabled
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
              : 'border-[var(--voix-border-strong)] bg-[var(--voix-bg-subtle)] text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-inset)]',
            'focus-visible:border-[color:var(--voix-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--voix-accent)]/30'
          )}
          aria-label={microphoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
        >
          {microphoneEnabled ? <MicIcon className="h-3.5 w-3.5" /> : <MicOffIcon className="h-3.5 w-3.5" />}
          {microphoneEnabled ? 'Mute' : 'Unmute'}
        </AgentTrackToggle>
      </div>
    </div>
  );
}
