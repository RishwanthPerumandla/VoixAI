'use client';

import { Track } from 'livekit-client';
import { useChat } from '@livekit/components-react';
import { MicIcon, MicOffIcon, PhoneOffIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentTrackToggle } from '@/components/agents-ui/agent-track-toggle';
import { TextFallbackInput } from '@/components/app/text-fallback-input';
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
            'h-11 min-w-[9rem] rounded-full border border-white/10 px-4 text-sm font-medium',
            microphoneEnabled
              ? 'bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/20'
              : 'bg-white/6 text-slate-100 hover:bg-white/10'
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
          className="h-11 rounded-full border-white/10 bg-transparent px-5 text-sm text-slate-100 hover:bg-white/8"
        >
          <PhoneOffIcon />
          End order
        </Button>
      </div>
    </div>
  );
}
