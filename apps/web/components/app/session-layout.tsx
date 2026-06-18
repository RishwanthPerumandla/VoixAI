'use client';

import { useState } from 'react';
import {
  useAgent,
  useChat,
  useSessionContext,
  useSessionMessages,
  useTrackVolume,
} from '@livekit/components-react';
import type { ReceivedMessage } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { AssistantStage } from '@/components/app/assistant-stage';
import { ConversationTranscript } from '@/components/app/conversation-transcript';
import { DeveloperDetails } from '@/components/app/developer-details';
import { getSessionStatusContent, getSessionStatusTone } from '@/components/app/session-status';
import { VoiceControls } from '@/components/app/voice-controls';
import { Button } from '@/components/ui/button';
import { useInputControls } from '@/hooks/agents-ui/use-agent-control-bar';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { useVoicePresenceState } from '@/hooks/useVoicePresenceState';
import type { ChannelConfig } from '@/lib/channel-config';
import type { RuntimeConfig } from '@/lib/runtime-config';
import { resolveScenarioCopy } from '@/lib/scenario-config';
import type { ScenarioConfig } from '@/lib/scenario-config';

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

const STATUS_TONE_CLASSES: Record<string, string> = {
  teal: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  blue: 'border-sky-200 bg-sky-50 text-sky-700',
  violet: 'border-indigo-200 bg-indigo-50 text-indigo-700',
  amber: 'border-amber-200 bg-amber-50 text-amber-700',
  green: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  rose: 'border-rose-200 bg-rose-50 text-rose-700',
  slate:
    'border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] text-[var(--voix-text-secondary)]',
};

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
      <div className="dashboard-light min-h-svh w-full bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
        <ScenarioConfirmation
          telemetrySnapshot={telemetrySnapshot}
          onStartNewFlow={onEndSession}
          onBackToDemo={onEndSession}
        />
      </div>
    );
  }

  return (
    <div className="dashboard-light relative min-h-svh w-full bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
      <section className="mx-auto flex min-h-svh w-full max-w-7xl flex-col px-4 pt-8 pb-10 md:px-6 xl:px-8">
        <header
          className="rounded-[28px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-5 py-4"
          style={{ boxShadow: 'var(--voix-card-shadow)' }}
        >
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-[var(--voix-text-primary)]">
                VoixAI session in progress
              </p>
              <p className="text-sm text-[var(--voix-text-secondary)]">
                {resolveScenarioCopy(scenario.session.headerSubtitle, channel)}
              </p>
              <p className="mt-1 text-sm text-[var(--voix-text-muted)]">{statusCopy.helper}</p>
            </div>
            <div className="flex items-center gap-3">
              <span
                aria-live="polite"
                className={[
                  'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors',
                  STATUS_TONE_CLASSES[statusTone] ?? STATUS_TONE_CLASSES.slate,
                ].join(' ')}
              >
                <span className="h-2 w-2 rounded-full bg-current" />
                {statusCopy.label}
              </span>
              <Button
                type="button"
                variant="outline"
                onClick={() => setConfirmEnd(true)}
                className="rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
              >
                End order
              </Button>
            </div>
          </div>
        </header>

        <div className="mt-4 grid flex-1 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="flex min-h-0 flex-col gap-4">
            <AssistantStage state={userFacingState} latestAssistantPrompt={latestAssistantPrompt}>
              {deviceError && (
                <div className="w-full rounded-[24px] border border-amber-200 bg-amber-50 p-4 text-left">
                  <p className="text-base font-semibold text-amber-800">Microphone access needed</p>
                  <p className="mt-2 text-sm leading-6 text-amber-700">
                    {resolveScenarioCopy(scenario.session.permissionPrompt, channel)}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button
                      type="button"
                      onClick={() => void microphoneToggle.toggle(true)}
                      className="rounded-full bg-[color:var(--voix-accent)] text-white hover:bg-[color:var(--voix-accent-hover)]"
                    >
                      Enable microphone
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowTranscript(true)}
                      className="rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
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

          <div className="space-y-4 xl:sticky xl:top-6 xl:self-start">
            <section
              className="rounded-[28px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-4"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <div className="px-2 pb-4">
                <p className="text-sm font-semibold text-[var(--voix-text-primary)]">
                  {scenario.session.workspaceEyebrow}
                </p>
                <p className="mt-1 text-sm text-[var(--voix-text-secondary)]">
                  {scenario.session.workspaceTitle}
                </p>
                <p className="mt-1 text-xs tracking-[0.16em] text-[var(--voix-text-muted)] uppercase">
                  Channel: {channel.shortLabel}
                </p>
                <p className="mt-2 text-sm leading-6 text-[var(--voix-text-muted)]">
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
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="end-order-title"
          >
            <div
              className="w-full max-w-md rounded-[28px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6"
              style={{ boxShadow: 'var(--voix-card-shadow-hover)' }}
            >
              <div className="flex items-start gap-3">
                <WarningIcon size={24} className="mt-1 text-amber-500" />
                <div>
                  <h2
                    id="end-order-title"
                    className="text-lg font-semibold text-[var(--voix-text-primary)]"
                  >
                    {scenario.session.endDialogTitle}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--voix-text-muted)]">
                    {scenario.session.endDialogDescription}
                  </p>
                </div>
              </div>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setConfirmEnd(false)}
                  className="rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
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
    </div>
  );
}
