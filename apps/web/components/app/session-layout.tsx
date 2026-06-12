'use client';

import { useState } from 'react';
import {
  useAgent,
  useChat,
  useSessionContext,
  useSessionMessages,
  useTrackVolume,
  useVoiceAssistant,
} from '@livekit/components-react';
import type { ReceivedMessage } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { AssistantStage } from '@/components/app/assistant-stage';
import { ConversationTranscript } from '@/components/app/conversation-transcript';
import { DeveloperDetails } from '@/components/app/developer-details';
import {
  getSessionStatusTone,
  getSessionStatusContent,
} from '@/components/app/session-status';
import type { ChannelConfig } from '@/lib/channel-config';
import { resolveScenarioCopy } from '@/lib/scenario-config';
import { VoiceControls } from '@/components/app/voice-controls';
import { useInputControls } from '@/hooks/agents-ui/use-agent-control-bar';
import { useVoicePresenceState } from '@/hooks/useVoicePresenceState';
import type { ScenarioConfig } from '@/lib/scenario-config';
import type { RuntimeConfig } from '@/lib/runtime-config';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';

interface SessionLayoutProps {
  scenario: ScenarioConfig;
  channel: ChannelConfig;
  runtimeConfig: RuntimeConfig | null;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  developerMode: boolean;
  onEndSession: () => void;
}

function getLatestAssistantMessage(messages: ReceivedMessage[]) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (!messages[index].from?.isLocal) {
      return messages[index].message;
    }
  }
  return null;
}

export function SessionLayout({
  scenario,
  channel,
  runtimeConfig,
  telemetrySnapshot,
  developerMode,
  onEndSession,
}: SessionLayoutProps) {
  const { connectionState, isConnected } = useSessionContext();
  const { messages } = useSessionMessages();
  const { send } = useChat();
  const agent = useAgent();
  const voiceAssistant = useVoiceAssistant();
  const [showTranscript, setShowTranscript] = useState(true);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [deviceError, setDeviceError] = useState<Error | null>(null);
  const { microphoneTrack, microphoneToggle } = useInputControls({
    onDeviceError: ({ error }) => setDeviceError(error),
  });
  const userLevel = useTrackVolume(microphoneTrack, {
    fftSize: 256,
    smoothingTimeConstant: 0.65,
  });
  const assistantLevel = useTrackVolume(voiceAssistant.audioTrack, {
    fftSize: 256,
    smoothingTimeConstant: 0.55,
  });
  const userFacingState = useVoicePresenceState({
    agentState: agent.state,
    connectionState,
    telemetrySnapshot,
    userLevel,
  });
  const statusCopy = getSessionStatusContent(userFacingState);
  const statusTone = getSessionStatusTone(userFacingState);
  const latestAssistantPrompt = getLatestAssistantMessage(messages);
  const ScenarioWorkspace = scenario.WorkspaceComponent;
  const ScenarioConfirmation = scenario.ConfirmationComponent;

  const handleEditOrder = async () => {
    await send('I want to change my order.');
  };

  const handleConfirmOrder = async () => {
    await send('confirm');
  };

  if (telemetrySnapshot?.mock_order) {
    return (
      <ScenarioConfirmation
        telemetrySnapshot={telemetrySnapshot}
        onStartNewFlow={onEndSession}
        onBackToDemo={onEndSession}
      />
    );
  }

  return (
    <section className="mx-auto flex min-h-[calc(100svh-5rem)] w-full max-w-7xl flex-col px-4 pb-6 pt-20 md:px-6 xl:px-8">
      <header className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,17,30,0.92),rgba(10,18,31,0.82))] px-5 py-4 shadow-[0_24px_80px_rgba(0,0,0,0.18)]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-50">VoixAI session in progress</p>
            <p className="text-sm text-slate-300">
              {resolveScenarioCopy(scenario.session.headerSubtitle, channel)}
            </p>
            <p className="mt-1 text-sm text-slate-400">{statusCopy.helper}</p>
          </div>
          <div className="flex items-center gap-3">
            <span
              aria-live="polite"
              className={[
                'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors',
                statusTone === 'teal' && 'border-teal-400/20 bg-teal-400/10 text-teal-200',
                statusTone === 'blue' && 'border-sky-400/20 bg-sky-400/10 text-sky-200',
                statusTone === 'violet' && 'border-indigo-400/20 bg-indigo-400/10 text-indigo-200',
                statusTone === 'amber' && 'border-amber-300/20 bg-amber-300/10 text-amber-100',
                statusTone === 'green' && 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200',
                statusTone === 'rose' && 'border-rose-400/20 bg-rose-400/10 text-rose-200',
                statusTone === 'slate' && 'border-white/10 bg-white/[0.04] text-slate-200',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <span className="h-2 w-2 rounded-full bg-current" />
              {statusCopy.label}
            </span>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmEnd(true)}
              className="rounded-full border-white/10 bg-transparent text-slate-100 hover:bg-white/8"
            >
              End order
            </Button>
          </div>
        </div>
      </header>

      <div className="mt-4 grid flex-1 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="flex min-h-0 flex-col gap-4">
          <AssistantStage
            state={userFacingState}
            latestAssistantPrompt={latestAssistantPrompt}
          >
            {deviceError && (
              <div className="w-full rounded-[24px] border border-amber-300/20 bg-amber-400/10 p-4 text-left">
                <p className="text-base font-semibold text-amber-100">Microphone access needed</p>
                <p className="mt-2 text-sm leading-6 text-amber-50/90">
                  {resolveScenarioCopy(scenario.session.permissionPrompt, channel)}
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button
                    type="button"
                    onClick={() => void microphoneToggle.toggle(true)}
                    className="rounded-full bg-[color:var(--voix-accent)] text-[color:var(--voix-accent-foreground)] hover:bg-[color:var(--voix-accent-hover)]"
                  >
                    Enable microphone
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowTranscript(true)}
                    className="rounded-full border-white/10 bg-transparent text-slate-100 hover:bg-white/8"
                  >
                    Use text instead
                  </Button>
                </div>
              </div>
            )}
          </AssistantStage>

          <div className="grid gap-4">
            <ConversationTranscript
              messages={messages}
              state={userFacingState}
              collapsed={!showTranscript}
              onToggleCollapsed={() => setShowTranscript((value) => !value)}
              footer={
                <VoiceControls
                  microphoneEnabled={microphoneToggle.enabled}
                  microphonePending={microphoneToggle.pending}
                  onToggleMicrophone={microphoneToggle.toggle}
                  onEndOrder={() => setConfirmEnd(true)}
                />
              }
            />
          </div>
        </main>

        <div className="space-y-4 xl:sticky xl:top-20 xl:self-start">
          <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,15,28,0.92),rgba(12,20,34,0.84))] p-4 shadow-[0_24px_90px_rgba(0,0,0,0.22)]">
            <div className="px-2 pb-4">
              <p className="text-sm font-semibold text-slate-50">
                {scenario.session.workspaceEyebrow}
              </p>
              <p className="mt-1 text-sm text-slate-300">{scenario.session.workspaceTitle}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                Channel: {channel.shortLabel}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                {resolveScenarioCopy(scenario.session.workspaceDescription, channel)}
              </p>
            </div>

            <ScenarioWorkspace
              telemetrySnapshot={telemetrySnapshot}
              userFacingState={userFacingState}
              isConnected={isConnected}
              onEditWorkflow={handleEditOrder}
              onConfirmWorkflow={handleConfirmOrder}
            />
          </section>

          <DeveloperDetails
            enabled={developerMode}
            runtimeConfig={runtimeConfig}
            telemetrySnapshot={telemetrySnapshot}
            rawState={agent.state}
          />
        </div>
      </div>

      {confirmEnd && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="end-order-title"
        >
          <div className="w-full max-w-md rounded-[28px] border border-white/10 bg-slate-950 p-6 shadow-2xl shadow-black/30">
            <div className="flex items-start gap-3">
              <WarningIcon size={24} className="mt-1 text-amber-300" />
              <div>
                <h2 id="end-order-title" className="text-lg font-semibold text-slate-50">
                  {scenario.session.endDialogTitle}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {scenario.session.endDialogDescription}
                </p>
              </div>
            </div>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => setConfirmEnd(false)}
                className="rounded-full border-white/10 bg-transparent text-slate-100 hover:bg-white/8"
              >
                {scenario.session.keepActionLabel}
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={onEndSession}
                className="rounded-full"
              >
                {scenario.session.endActionLabel}
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
