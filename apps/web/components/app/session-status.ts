'use client';

export type UserFacingSessionState =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'userSpeaking'
  | 'thinking'
  | 'assistantSpeaking'
  | 'error'
  | 'readyToConfirm'
  | 'complete';

export interface SessionStatusContent {
  label: string;
  helper: string;
}

const SESSION_STATUS_COPY: Record<UserFacingSessionState, SessionStatusContent> = {
  idle: {
    label: 'Ready to start',
    helper: 'Start a voice order when you are ready.',
  },
  connecting: {
    label: 'Connecting',
    helper: 'Setting up your voice session...',
  },
  listening: {
    label: 'Listening',
    helper: "Speak naturally. I'm listening.",
  },
  userSpeaking: {
    label: 'I hear you',
    helper: 'Keep speaking naturally.',
  },
  thinking: {
    label: 'Thinking',
    helper: 'Checking your order details...',
  },
  assistantSpeaking: {
    label: 'Assistant speaking',
    helper: 'Assistant is responding...',
  },
  error: {
    label: 'Connection issue',
    helper: 'Something interrupted the voice session.',
  },
  readyToConfirm: {
    label: 'Review your order',
    helper: 'Review the details before confirming.',
  },
  complete: {
    label: 'Order confirmed',
    helper: 'Your mock order has been confirmed.',
  },
};

export function getSessionStatusContent(state: UserFacingSessionState): SessionStatusContent {
  return SESSION_STATUS_COPY[state];
}

export function getSessionStatusTone(state: UserFacingSessionState) {
  switch (state) {
    case 'userSpeaking':
    case 'listening':
      return 'teal';
    case 'assistantSpeaking':
      return 'blue';
    case 'thinking':
    case 'connecting':
      return 'violet';
    case 'readyToConfirm':
      return 'amber';
    case 'complete':
      return 'green';
    case 'error':
      return 'rose';
    default:
      return 'slate';
  }
}
