'use client';

import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import { useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { useSessionTelemetry } from '@/hooks/useSessionTelemetry';

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
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { connectionState, isConnected, room, start } = useSessionContext();
  const agent = useAgent();
  const telemetrySnapshot = useSessionTelemetry();
  const { resolvedTheme } = useTheme();
  const connectionStatusLabel =
    connectionState === 'connected'
      ? 'Connected'
      : connectionState === 'connecting'
        ? 'Connecting'
        : connectionState === 'reconnecting' || connectionState === 'signalReconnecting'
          ? 'Reconnecting'
          : 'Disconnected';
  const hasAgentTelemetry = telemetrySnapshot !== null;
  const isAgentActive =
    agent.state === 'listening' || agent.state === 'thinking' || agent.state === 'speaking';
  let agentStatusLabel = 'Agent offline';

  if (agent.state === 'failed') {
    agentStatusLabel = 'Agent connection failed';
  } else if (hasAgentTelemetry) {
    agentStatusLabel = 'Agent ready';
  } else if (isAgentActive) {
    agentStatusLabel = 'Agent initializing';
  } else if (connectionState === 'connecting') {
    agentStatusLabel = 'Starting session';
  } else if (
    connectionState === 'reconnecting' ||
    connectionState === 'signalReconnecting'
  ) {
    agentStatusLabel = 'Reconnecting agent';
  } else if (isConnected) {
    agentStatusLabel = 'Waiting for agent';
  }
  const preConnectMessage = isConnected
    ? `Connected to ${room.name || appConfig.roomName}. Ask for a recap when you are ready to review the order.`
    : `Ready to join ${appConfig.roomName}.`;

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
          roomName={appConfig.roomName}
          connectionStatusLabel={connectionStatusLabel}
          onStartCall={start}
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
          roomName={room.name || appConfig.roomName}
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
