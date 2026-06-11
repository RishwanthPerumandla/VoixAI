'use client';

import * as React from 'react';
import { useSessionContext } from '@livekit/components-react';
import { RoomEvent } from 'livekit-client';

export const VOIXAI_TELEMETRY_TOPIC = 'voixai.telemetry';

export interface TelemetryOrderState {
  pickup_or_delivery: string | null;
  items: string[];
  flavor: string | null;
  classic_or_boneless: string | null;
  drink: string | null;
  pickup_time: string | null;
  confirmed: boolean;
}

export interface TelemetryMockOrder {
  order_number: string;
  total: string;
  summary: string;
}

export interface TelemetryUserTurnMetrics {
  transcription_delay: number | null;
  end_of_turn_delay: number | null;
  on_user_turn_completed_delay: number | null;
}

export interface TelemetryAssistantTurnMetrics {
  llm_ttft: number | null;
  tts_ttfb: number | null;
  e2e_latency: number | null;
  started_speaking_at: number | null;
  stopped_speaking_at: number | null;
}

export interface TelemetryRuntimeProfile {
  voice_engine: string;
  requested_voice_engine: string | null;
  llm_model: string;
  stt_model: string;
  tts_model: string;
  openai_realtime_model: string;
  openai_realtime_voice: string;
  openai_realtime_eagerness: string;
  google_realtime_model: string;
  google_realtime_voice: string;
  realtime_temperature: number;
  realtime_enable_affective_dialog: boolean;
  realtime_enable_proactivity: boolean;
  preset_id: string | null;
  preset_label: string | null;
  comparison_label: string | null;
  fallback_reason: string | null;
}

export interface SessionTelemetrySnapshot {
  type: 'session_snapshot';
  reason: string;
  timestamp: number;
  target_e2e_latency_ms: number;
  acceptable_e2e_latency_ms: number;
  turn_count: number;
  order: TelemetryOrderState;
  mock_order: TelemetryMockOrder | null;
  runtime_profile: TelemetryRuntimeProfile | null;
  user_turn_metrics: TelemetryUserTurnMetrics | null;
  assistant_turn_metrics: TelemetryAssistantTurnMetrics | null;
}

function isTelemetrySnapshot(value: unknown): value is SessionTelemetrySnapshot {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const candidate = value as Partial<SessionTelemetrySnapshot>;
  return candidate.type === 'session_snapshot' && typeof candidate.timestamp === 'number';
}

export function useSessionTelemetry() {
  const { room } = useSessionContext();
  const [snapshot, setSnapshot] = React.useState<SessionTelemetrySnapshot | null>(null);

  React.useEffect(() => {
    const decoder = new TextDecoder();

    const handleDataReceived = (
      payload: Uint8Array,
      _participant?: unknown,
      _kind?: unknown,
      topic?: string
    ) => {
      if (topic !== VOIXAI_TELEMETRY_TOPIC) {
        return;
      }

      try {
        const parsed = JSON.parse(decoder.decode(payload)) as unknown;
        if (isTelemetrySnapshot(parsed)) {
          setSnapshot(parsed);
        }
      } catch (error) {
        console.warn('Failed to parse VoixAI telemetry payload', error);
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);
    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);

  return snapshot;
}
