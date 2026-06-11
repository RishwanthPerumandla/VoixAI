'use client';

import { type ReactNode } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import { useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { RuntimeConfigPanel } from '@/components/app/runtime-config-panel';
import { WelcomeView } from '@/components/app/welcome-view';
import { useSessionTelemetry } from '@/hooks/useSessionTelemetry';
import { type RuntimeConfig } from '@/lib/runtime-config';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
  runtimeConfig: RuntimeConfig;
  onRuntimeConfigChange: (config: RuntimeConfig) => void;
}

function buildActiveRuntimeConfig(
  runtimeConfig: RuntimeConfig,
  telemetrySnapshot: ReturnType<typeof useSessionTelemetry>
) {
  const profile = telemetrySnapshot?.runtime_profile;
  if (!profile) {
    return null;
  }

  return {
    ...runtimeConfig,
    voiceEngine: profile.voice_engine as RuntimeConfig['voiceEngine'],
    llmModel: profile.llm_model,
    sttModel: profile.stt_model ?? runtimeConfig.sttModel,
    ttsModel: profile.tts_model ?? runtimeConfig.ttsModel,
    openaiRealtimeModel: profile.openai_realtime_model,
    openaiRealtimeVoice: profile.openai_realtime_voice,
    openaiRealtimeEagerness: profile.openai_realtime_eagerness,
    googleRealtimeModel: profile.google_realtime_model,
    googleRealtimeVoice: profile.google_realtime_voice,
    realtimeTemperature: profile.realtime_temperature,
    realtimeEnableAffectiveDialog: profile.realtime_enable_affective_dialog,
    realtimeEnableProactivity: profile.realtime_enable_proactivity,
    presetId: profile.preset_id ?? runtimeConfig.presetId,
    presetLabel: profile.preset_label ?? runtimeConfig.presetLabel,
    comparisonLabel: profile.comparison_label ?? runtimeConfig.comparisonLabel,
    fallbackReason: profile.fallback_reason,
    requestedVoiceEngine: profile.requested_voice_engine,
  };
}

export function ViewController({
  appConfig,
  runtimeConfig,
  onRuntimeConfigChange,
}: ViewControllerProps) {
  const { connectionState, isConnected, room, start } = useSessionContext();
  const agent = useAgent();
  const telemetrySnapshot = useSessionTelemetry();
  const { resolvedTheme } = useTheme();
  const activeRuntimeConfig = buildActiveRuntimeConfig(runtimeConfig, telemetrySnapshot);
  const connectionStatusLabel =
    connectionState === 'connected'
      ? 'Live'
      : connectionState === 'connecting'
        ? 'Starting'
        : connectionState === 'reconnecting' || connectionState === 'signalReconnecting'
          ? 'Reconnecting'
          : 'Ready';
  const hasAgentTelemetry = telemetrySnapshot !== null;
  const isAgentActive =
    agent.state === 'listening' || agent.state === 'thinking' || agent.state === 'speaking';
  let agentStatusLabel = 'Assistant offline';

  if (agent.state === 'failed') {
    agentStatusLabel = 'Assistant unavailable';
  } else if (hasAgentTelemetry) {
    agentStatusLabel = 'Assistant ready';
  } else if (isAgentActive) {
    agentStatusLabel = 'Assistant joining';
  } else if (connectionState === 'connecting') {
    agentStatusLabel = 'Starting session';
  } else if (
    connectionState === 'reconnecting' ||
    connectionState === 'signalReconnecting'
  ) {
    agentStatusLabel = 'Reconnecting';
  } else if (isConnected) {
    agentStatusLabel = 'Waiting for assistant';
  }
  const preConnectMessage = isConnected
    ? 'Ask for a recap whenever you want to review the latest order details.'
    : 'Allow the microphone, say your order naturally, and make one correction to test the flow.';

  const runtimePanel: ReactNode = (
    <RuntimeConfigPanel
      config={runtimeConfig}
      activeConfig={activeRuntimeConfig}
      connected={isConnected}
      compact={isConnected}
      onConfigChange={onRuntimeConfigChange}
    />
  );

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          pageTitle={appConfig.pageTitle}
          pageDescription={appConfig.pageDescription}
          startButtonText={appConfig.startButtonText}
          connectionStatusLabel={connectionStatusLabel}
          onStartCall={start}
          runtimePanel={runtimePanel}
        />
      )}
      {/* Session view */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
          preConnectMessage={preConnectMessage}
          connectionStatusLabel={connectionStatusLabel}
          agentStatusLabel={agentStatusLabel}
          runtimePanel={runtimePanel}
          audioVisualizerType={appConfig.audioVisualizerType}
          audioVisualizerColor={
            resolvedTheme === 'dark'
              ? appConfig.audioVisualizerColorDark
              : appConfig.audioVisualizerColor
          }
          audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
          audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
          audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
          audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
          audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
          className="w-full"
        />
      )}
    </AnimatePresence>
  );
}
