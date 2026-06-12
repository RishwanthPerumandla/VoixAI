'use client';

import { useMemo, useState } from 'react';
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
import { ConfirmationScreen } from '@/components/app/confirmation-screen';
import { ConversationTranscript } from '@/components/app/conversation-transcript';
import { DeveloperDetails } from '@/components/app/developer-details';
import { OrderSummaryPanel, type OrderSummaryItem } from '@/components/app/order-summary-panel';
import {
  getSessionStatusTone,
  getSessionStatusContent,
} from '@/components/app/session-status';
import { VoiceControls } from '@/components/app/voice-controls';
import { useInputControls } from '@/hooks/agents-ui/use-agent-control-bar';
import { useVoicePresenceState } from '@/hooks/useVoicePresenceState';
import type { RuntimeConfig } from '@/lib/runtime-config';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';

interface SessionLayoutProps {
  runtimeConfig: RuntimeConfig | null;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  developerMode: boolean;
  onEndSession: () => void;
}

function toTitleCase(value: string) {
  return value
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function getLatestAssistantMessage(messages: ReceivedMessage[]) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (!messages[index].from?.isLocal) {
      return messages[index].message;
    }
  }
  return null;
}

function buildOrderItems(snapshot: SessionTelemetrySnapshot | null): OrderSummaryItem[] {
  const order = snapshot?.order;
  if (!order || order.items.length === 0) {
    return [];
  }

  return order.items.map((item) => ({
    name: toTitleCase(item),
    flavor: order.flavor,
    style: order.classic_or_boneless,
  }));
}

function buildMissingDetails(snapshot: SessionTelemetrySnapshot | null) {
  const order = snapshot?.order;
  if (!order) {
    return ['Service', 'Items', 'Pickup time'];
  }

  const missing: string[] = [];
  if (!order.pickup_or_delivery) missing.push('Service');
  if (order.items.length === 0) missing.push('Items');
  if (!order.drink) missing.push('Drink');
  if (!order.pickup_time) missing.push('Pickup time');
  if (!order.classic_or_boneless && order.items.some((item) => item.toLowerCase().includes('wings'))) {
    missing.push('Style');
  }
  return missing;
}

export function SessionLayout({
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
  const orderItems = useMemo(() => buildOrderItems(telemetrySnapshot), [telemetrySnapshot]);
  const missingDetails = useMemo(() => buildMissingDetails(telemetrySnapshot), [telemetrySnapshot]);
  const confirmDisabled =
    userFacingState === 'complete' ||
    missingDetails.length > 0 ||
    orderItems.length === 0 ||
    !isConnected;
  const confirmHelperText =
    missingDetails.length > 0
      ? `Add ${missingDetails.join(', ').toLowerCase()} before confirming.`
      : orderItems.length === 0
        ? 'Add at least one item before confirming.'
        : null;

  const handleEditOrder = async () => {
    await send('I want to change my order.');
  };

  const handleConfirmOrder = async () => {
    await send('confirm');
  };

  if (telemetrySnapshot?.mock_order) {
    return (
      <ConfirmationScreen
        service={telemetrySnapshot.order.pickup_or_delivery}
        items={telemetrySnapshot.order.items.map(toTitleCase)}
        pickupTime={telemetrySnapshot.order.pickup_time}
        total={telemetrySnapshot.mock_order.total}
        orderNumber={telemetrySnapshot.mock_order.order_number}
        onStartNewOrder={onEndSession}
        onBackToDemo={onEndSession}
      />
    );
  }

  return (
    <section className="mx-auto flex min-h-[calc(100svh-5rem)] w-full max-w-7xl flex-col px-4 pb-6 pt-20 md:px-6 xl:px-8">
      <header className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,17,30,0.92),rgba(10,18,31,0.82))] px-5 py-4 shadow-[0_24px_80px_rgba(0,0,0,0.18)]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-50">Voice order in progress</p>
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
                  Allow microphone access to start your voice order.
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
          <OrderSummaryPanel
            service={telemetrySnapshot?.order.pickup_or_delivery ?? null}
            items={orderItems}
            pickupTime={telemetrySnapshot?.order.pickup_time ?? null}
            drink={telemetrySnapshot?.order.drink ?? null}
            total={telemetrySnapshot?.mock_order?.total ?? null}
            missingDetails={missingDetails}
            isConfirmed={Boolean(telemetrySnapshot?.order.confirmed)}
            onEditOrder={handleEditOrder}
            onConfirmOrder={handleConfirmOrder}
            confirmDisabled={confirmDisabled}
            confirmHelperText={confirmHelperText}
          />

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
                  End this order?
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Your current mock order will be discarded.
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
                Keep ordering
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={onEndSession}
                className="rounded-full"
              >
                End order
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
