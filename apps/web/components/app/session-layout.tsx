'use client';

import { useEffect, useRef, useState } from 'react';
import {
  useAgent,
  useChat,
  useSessionContext,
  useSessionMessages,
  useTrackVolume,
} from '@livekit/components-react';
import type { ReceivedMessage } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { CallHeader } from '@/components/app/call-header';
import { ConversationFeed } from '@/components/app/conversation-feed';
import { DeveloperDetails } from '@/components/app/developer-details';
import { IntelligencePanel } from '@/components/app/intelligence-panel';
import { LiveOrderSummary } from '@/components/app/live-order-summary';
import { LiveTranscriptLine } from '@/components/app/live-transcript-line';
import { MinimalControls } from '@/components/app/minimal-controls';
import { VoiceVisualizer } from '@/components/app/voice-visualizer';
import { Button } from '@/components/ui/button';
import { useInputControls } from '@/hooks/agents-ui/use-agent-control-bar';
import { synthesizeConfirmationSnapshot, useRoomOrder } from '@/hooks/useRoomOrder';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { useVoicePresenceState } from '@/hooks/useVoicePresenceState';
import { useIntelligence } from '@/lib/intelligence';
import type { IntelligenceEvent } from '@/lib/intelligence/types';
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

function buildTranscriptEntries(
  sessionMessages: ReceivedMessage[],
  telemetrySnapshot: SessionTelemetrySnapshot | null
): Array<{ id: string; role: 'assistant' | 'user'; message: string }> {
  if (sessionMessages.length > 0) {
    return sessionMessages.map((entry) => ({
      id: entry.id,
      role: entry.from?.isLocal ? 'user' as const : 'assistant' as const,
      message: entry.message,
    }));
  }

  return (telemetrySnapshot?.transcript ?? []).map((entry, index) => ({
    id: `${entry.role}-${entry.ts}-${index}`,
    role: entry.role,
    message: entry.text,
  }));
}

function getLatestEventForFeed(events: IntelligenceEvent[]): IntelligenceEvent | undefined {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.kind === 'intent_detected' || e.kind === 'entity_extracted' || e.kind === 'validation_error') {
      return e;
    }
  }
  return undefined;
}

export function SessionLayout({
  scenario,
  channel,
  runtimeConfig,
  telemetrySnapshot,
  developerMode,
  onEndSession,
}: SessionLayoutProps) {
  const { connectionState, isConnected, room } = useSessionContext();
  const { messages } = useSessionMessages();
  const { send } = useChat();
  const agent = useAgent();
  const apiRoomOrder = useRoomOrder(room?.name, isConnected && !telemetrySnapshot?.mock_order);
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

  const {
    events,
    workflowSteps,
    stage,
    stageLabel,
    quoteSnapshot,
    eventCount,
  } = useIntelligence(telemetrySnapshot);

  const transcriptEntries = buildTranscriptEntries(messages, telemetrySnapshot);
  const ScenarioWorkspace = scenario.WorkspaceComponent;
  const ScenarioConfirmation = scenario.ConfirmationComponent;

  const [escalated, setEscalated] = useState(false);
  const escalationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (escalated) return;
    if (!telemetrySnapshot) return;
    const reason = telemetrySnapshot.reason;
    if (reason === 'escalation' || reason === 'handoff_required') {
      setEscalated(true);
      escalationTimerRef.current = setTimeout(() => {
        onEndSession();
      }, 3000);
    }
  }, [telemetrySnapshot, onEndSession, escalated]);

  useEffect(() => {
    return () => {
      if (escalationTimerRef.current) {
        clearTimeout(escalationTimerRef.current);
      }
    };
  }, []);

  const handleEditOrder = async () => {
    await send('I want to change my order.');
  };

  const handleConfirmOrder = async () => {
    await send('confirm');
  };

  const confirmationSnapshot = telemetrySnapshot?.mock_order
    ? telemetrySnapshot
    : apiRoomOrder
      ? synthesizeConfirmationSnapshot(apiRoomOrder, telemetrySnapshot)
      : null;

  if (confirmationSnapshot) {
    return (
      <div className="dashboard-light min-h-svh w-full bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
        <ScenarioConfirmation
          telemetrySnapshot={confirmationSnapshot}
          onStartNewFlow={onEndSession}
          onBackToDemo={onEndSession}
        />
      </div>
    );
  }

  if (escalated) {
    return (
      <div className="dashboard-light min-h-svh w-full bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
        <section className="mx-auto flex min-h-svh w-full max-w-[1440px] flex-col items-center justify-center px-4">
          <div
            className="w-full max-w-md rounded-[28px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-8 text-center"
            style={{ boxShadow: 'var(--voix-card-shadow-hover)' }}
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-amber-100">
              <WarningIcon size={32} className="text-amber-600" />
            </div>
            <h2 className="mt-6 text-xl font-semibold text-[var(--voix-text-primary)]">
              Call Escalated
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--voix-text-secondary)]">
              Your call is being transferred to a manager. Please hold while we connect you.
            </p>
            <p className="mt-4 text-xs text-[var(--voix-text-muted)]">
              This window will close automatically...
            </p>
          </div>
        </section>
      </div>
    );
  }

  const latestEvent = getLatestEventForFeed(events);

  return (
    <div className="dashboard-light relative min-h-svh w-full bg-[var(--voix-bg-primary)] text-[var(--voix-text-primary)]">
      <section className="mx-auto flex min-h-svh w-full max-w-[1440px] flex-col px-4 pt-6 pb-8 md:px-6">
        {/* Call Header */}
        <CallHeader
          state={userFacingState}
          onEndCall={() => setConfirmEnd(true)}
        />

        {/* Two-Panel Layout */}
        <div className="mt-4 grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_380px]">
          {/* Left Panel: Voice Experience */}
          <main className="flex min-h-0 flex-col gap-4">
            {/* Voice Visualizer */}
            <div
              className="flex items-center justify-center rounded-[28px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] py-8"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <VoiceVisualizer state={userFacingState} />
            </div>

            {/* Live Transcript Line - shows latest message below visualizer */}
            <LiveTranscriptLine
              messages={transcriptEntries}
              state={userFacingState}
            />

            {deviceError && (
              <div className="rounded-[20px] border border-amber-200 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-800">Microphone access needed</p>
                <p className="mt-1 text-xs leading-5 text-amber-700">
                  {resolveScenarioCopy(scenario.session.permissionPrompt, channel)}
                </p>
                <div className="mt-3 flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => void microphoneToggle.toggle(true)}
                    className="rounded-full bg-[color:var(--voix-accent)] text-white hover:bg-[color:var(--voix-accent-hover)]"
                  >
                    Enable microphone
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => void send('')}
                    className="rounded-full border-[var(--voix-border-strong)] text-[var(--voix-text-secondary)]"
                  >
                    Use text instead
                  </Button>
                </div>
              </div>
            )}

            {/* Live Order Summary */}
            <LiveOrderSummary
              order={telemetrySnapshot?.order ?? null}
              priceQuote={telemetrySnapshot?.price_quote ?? null}
            />

            {/* Conversation Feed - Full scrollable history */}
            <div
              className="flex min-h-[300px] flex-1 flex-col rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)]"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <div className="border-b border-[var(--voix-border-subtle)] px-4 py-3">
                <p className="text-xs font-semibold text-[var(--voix-text-muted)] uppercase">
                  Conversation
                </p>
              </div>
              <ConversationFeed
                messages={transcriptEntries}
                state={userFacingState}
                latestEvent={latestEvent}
              />
              <div className="border-t border-[var(--voix-border-subtle)] px-4 py-3">
                <MinimalControls
                  microphoneEnabled={microphoneToggle.enabled}
                  microphonePending={microphoneToggle.pending}
                  onToggleMicrophone={microphoneToggle.toggle}
                />
              </div>
            </div>
          </main>

          {/* Right Panel: Intelligence */}
          <aside className="flex min-h-0 flex-col gap-4 lg:sticky lg:top-6 lg:self-start">
            <IntelligencePanel
              events={events}
              workflowSteps={workflowSteps}
              stage={stage}
              stageLabel={stageLabel}
              eventCount={eventCount}
            />

            {/* Scenario Workspace */}
            <section
              className="rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-4"
              style={{ boxShadow: 'var(--voix-card-shadow)' }}
            >
              <div className="mb-3">
                <p className="text-xs font-semibold text-[var(--voix-text-muted)] uppercase">
                  {scenario.session.workspaceEyebrow}
                </p>
                <p className="mt-1 text-xs text-[var(--voix-text-secondary)]">
                  {scenario.session.workspaceTitle}
                </p>
                <p className="mt-0.5 text-[10px] tracking-wide text-[var(--voix-text-muted)]">
                  {channel.shortLabel}
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
          </aside>
        </div>

        {/* End Call Dialog */}
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
