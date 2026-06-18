'use client';

import { Track } from 'livekit-client';
import { MicIcon, MicOffIcon, PhoneOffIcon } from 'lucide-react';
import { useChat } from '@livekit/components-react';
import { AgentTrackToggle } from '@/components/agents-ui/agent-track-toggle';
import { TextFallbackInput } from '@/components/app/text-fallback-input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

interface VoiceControlsProps {
  microphoneEnabled: boolean;
  microphonePending: boolean;
  onToggleMicrophone: (enabled: boolean) => Promise<unknown> | void;
  onEndOrder: () => void;
  className?: string;
}

export function VoiceControls({
  microphoneEnabled,
  microphonePending,
  onToggleMicrophone,
  onEndOrder,
  className,
}: VoiceControlsProps) {
  const { send } = useChat();

  return (
    <div className={cn('space-y-4', className)}>
      <TextFallbackInput onSend={send} />

      <div className="flex flex-wrap items-center gap-3">
        <AgentTrackToggle
          source={Track.Source.Microphone}
          pressed={microphoneEnabled}
          pending={microphonePending}
          onPressedChange={(enabled) => {
            void onToggleMicrophone(enabled);
          }}
          className={cn(
            'h-11 min-w-[9rem] rounded-full border px-4 text-sm font-medium transition',
            microphoneEnabled
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
              : 'border-[var(--voix-border-strong)] bg-[var(--voix-bg-subtle)] text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-inset)]'
          )}
          aria-label={microphoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
        >
          {microphoneEnabled ? <MicIcon /> : <MicOffIcon />}
          {microphoneEnabled ? 'Mute' : 'Unmute'}
        </AgentTrackToggle>

        <Button
          type="button"
          variant="outline"
          onClick={onEndOrder}
          className="h-11 rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] px-5 text-sm text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
        >
          <PhoneOffIcon />
          End order
        </Button>
      </div>
    </div>
  );
}
