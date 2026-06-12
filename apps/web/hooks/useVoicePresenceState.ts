'use client';

import { useEffect, useRef, useState } from 'react';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import type { UserFacingSessionState } from '@/components/app/session-status';

interface UseVoicePresenceStateArgs {
  agentState: string;
  connectionState: string;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  userLevel: number;
}

const START_THRESHOLD = 0.08;
const STOP_THRESHOLD = 0.045;
const START_DELAY_MS = 140;
const STOP_DELAY_MS = 680;

export function useVoicePresenceState({
  agentState,
  connectionState,
  telemetrySnapshot,
  userLevel,
}: UseVoicePresenceStateArgs): UserFacingSessionState {
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const startTimerRef = useRef<number | null>(null);
  const stopTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (startTimerRef.current) {
        window.clearTimeout(startTimerRef.current);
      }
      if (stopTimerRef.current) {
        window.clearTimeout(stopTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const isListening = agentState === 'listening';
    if (!isListening) {
      if (startTimerRef.current) {
        window.clearTimeout(startTimerRef.current);
      }
      if (stopTimerRef.current) {
        window.clearTimeout(stopTimerRef.current);
      }
      setIsUserSpeaking(false);
      return;
    }

    if (userLevel >= START_THRESHOLD && !isUserSpeaking && !startTimerRef.current) {
      startTimerRef.current = window.setTimeout(() => {
        setIsUserSpeaking(true);
        startTimerRef.current = null;
      }, START_DELAY_MS);
    }

    if (userLevel < START_THRESHOLD && startTimerRef.current) {
      window.clearTimeout(startTimerRef.current);
      startTimerRef.current = null;
    }

    if (userLevel <= STOP_THRESHOLD && isUserSpeaking && !stopTimerRef.current) {
      stopTimerRef.current = window.setTimeout(() => {
        setIsUserSpeaking(false);
        stopTimerRef.current = null;
      }, STOP_DELAY_MS);
    }

    if (userLevel > STOP_THRESHOLD && stopTimerRef.current) {
      window.clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }
  }, [agentState, isUserSpeaking, userLevel]);

  return mapSessionStateToVoicePresenceState({
    agentState,
    connectionState,
    telemetrySnapshot,
    isUserSpeaking,
  });
}

interface MapSessionStateArgs {
  agentState: string;
  connectionState: string;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  isUserSpeaking: boolean;
}

export function mapSessionStateToVoicePresenceState({
  agentState,
  connectionState,
  telemetrySnapshot,
  isUserSpeaking,
}: MapSessionStateArgs): UserFacingSessionState {
  if (telemetrySnapshot?.mock_order) {
    return 'complete';
  }

  if (agentState === 'failed') {
    return 'error';
  }

  if (
    connectionState === 'connecting' ||
    connectionState === 'reconnecting' ||
    connectionState === 'signalReconnecting'
  ) {
    return 'connecting';
  }

  if (agentState === 'speaking') {
    return 'assistantSpeaking';
  }

  if (agentState === 'thinking') {
    return 'thinking';
  }

  if (telemetrySnapshot?.order?.confirmed) {
    return 'readyToConfirm';
  }

  if (agentState === 'listening') {
    return isUserSpeaking ? 'userSpeaking' : 'listening';
  }

  return 'idle';
}
