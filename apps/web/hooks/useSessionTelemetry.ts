'use client';

import * as React from 'react';
import { useSessionContext } from '@livekit/components-react';
import { RoomEvent } from 'livekit-client';

export const VOIXAI_TELEMETRY_TOPIC = 'voixai.telemetry';

export interface TelemetryOrderState {
  pickup_or_delivery: string | null;
  items: string[];
  phase?: string | null;
  line_items?: Array<{
    line_id: string;
    item_id: string;
    name: string;
    category: string;
    quantity: number;
    flavors: string[];
    modifiers: string[];
    notes: string | null;
    style: string | null;
  }>;
  modifiers?: string[];
  quantity?: number;
  order_type?: string | null;
  customer_name?: string | null;
  phone?: string | null;
  notes?: string | null;
  status?: string | null;
  flavor: string | null;
  classic_or_boneless: string | null;
  drink: string | null;
  pickup_time: string | null;
  confirmed: boolean;
  total_shown?: boolean;
  recap_readback?: boolean;
  pos_validation_passed?: boolean;
  validation_errors?: string[];
  last_clarification_question?: string | null;
  archived_order_count?: number;
  reliability_metrics?: {
    correction_count: number;
    cancellation_count: number;
    validation_failure_count: number;
    clarification_count: number;
    unknown_item_count: number;
    handoff_required_count: number;
    duplicate_confirmation_prevented: number;
    final_status: string;
  };
  recent_events?: Array<{
    type: string;
    detail: string;
    data: Record<string, unknown>;
  }>;
}

export interface TelemetryMockOrder {
  order_number: string;
  total: string;
  summary: string;
  kitchen_ticket?: string;
}

export interface TelemetryPriceQuote {
  subtotal: string;
  tax: string;
  total: string;
  eta_minutes: number;
  pricing_source: string;
  line_items: Array<{
    line_id: string;
    name: string;
    quantity: number;
    unit_price: string;
    line_subtotal: string;
    breakdown: string[];
  }>;
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
  scenario_id?: string;
  channel_id?: string;
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
  scenario_id?: string;
  channel_id?: string;
  reason: string;
  timestamp: number;
  target_e2e_latency_ms: number;
  acceptable_e2e_latency_ms: number;
  turn_count: number;
  order: TelemetryOrderState;
  price_quote?: TelemetryPriceQuote | null;
  mock_order: TelemetryMockOrder | null;
  runtime_profile: TelemetryRuntimeProfile | null;
  user_turn_metrics: TelemetryUserTurnMetrics | null;
  assistant_turn_metrics: TelemetryAssistantTurnMetrics | null;
  assistant_guardrail_violations?: string[];
  transcript?: Array<{
    role: 'user' | 'assistant';
    text: string;
    ts: number;
  }>;
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
  const prevSnapshotRef = React.useRef<string>('');

  React.useEffect(() => {
    setSnapshot(null);
    prevSnapshotRef.current = '';

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
          const serialized = JSON.stringify({
            r: parsed.reason,
            o: parsed.order,
            p: parsed.price_quote,
            m: parsed.mock_order,
            t: parsed.timestamp,
          });
          if (serialized !== prevSnapshotRef.current) {
            prevSnapshotRef.current = serialized;
            setSnapshot(parsed);
          }
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
