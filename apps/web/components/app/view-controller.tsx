'use client';

import { useSessionContext } from '@livekit/components-react';
import { useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { DeveloperDetails } from '@/components/app/developer-details';
import { LandingHero } from '@/components/app/landing-hero';
import { SessionLayout } from '@/components/app/session-layout';
import { useSessionTelemetry } from '@/hooks/useSessionTelemetry';
import { getChannelConfig } from '@/lib/channel-config';
import { getScenarioConfig } from '@/lib/scenario-config';
import { type RuntimeConfig } from '@/lib/runtime-config';

interface ViewControllerProps {
  appConfig: AppConfig;
  runtimeConfig: RuntimeConfig;
  onRuntimeConfigChange: (config: RuntimeConfig) => void;
  onSessionEnded: () => void;
}

function buildActiveRuntimeConfig(
  runtimeConfig: RuntimeConfig,
  telemetrySnapshot: ReturnType<typeof useSessionTelemetry>
) {
  const profile = telemetrySnapshot?.runtime_profile;
  if (!profile) {
    return runtimeConfig;
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
  onSessionEnded,
}: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const agent = useAgent();
  const telemetrySnapshot = useSessionTelemetry();
  const developerMode = process.env.NEXT_PUBLIC_DEVELOPER_MODE === 'true';
  const activeRuntimeConfig = buildActiveRuntimeConfig(runtimeConfig, telemetrySnapshot);
  const scenario = getScenarioConfig(appConfig.activeScenarioId);
  const channel = getChannelConfig(appConfig.activeChannelId);

  const handleEndSession = async () => {
    await end();
    onSessionEnded();
  };

  if (!isConnected) {
    return (
      <LandingHero
        scenario={scenario}
        channel={channel}
        onStartCall={start}
        onUseText={start}
        runtimeConfig={runtimeConfig}
        onRuntimeConfigChange={onRuntimeConfigChange}
        developerDetails={
          <DeveloperDetails
            enabled={developerMode}
            runtimeConfig={runtimeConfig}
            telemetrySnapshot={telemetrySnapshot}
            rawState={agent.state}
          />
        }
      />
    );
  }

  return (
    <SessionLayout
      scenario={scenario}
      channel={channel}
      runtimeConfig={activeRuntimeConfig}
      telemetrySnapshot={telemetrySnapshot}
      developerMode={developerMode}
      onEndSession={handleEndSession}
    />
  );
}
