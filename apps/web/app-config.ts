export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;
  roomName: string;
  participantName: string;
  apiBaseUrl: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  // agent dispatch configuration
  agentName?: string;

  // LiveKit Cloud Sandbox configuration
  sandboxId?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'VoixAI',
  pageTitle: 'VoixAI Voice Demo',
  pageDescription:
    'A streamlined voice demo where you can speak naturally, correct the order, and confirm a mock checkout.',
  roomName: process.env.NEXT_PUBLIC_LIVEKIT_ROOM_NAME ?? 'voixai-mvp-demo',
  participantName: process.env.NEXT_PUBLIC_PARTICIPANT_NAME ?? 'web-user',
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/favicon.ico',
  accent: '#c8642a',
  logoDark: '/favicon.ico',
  accentDark: '#ff9254',
  startButtonText: 'Start Conversation',

  // optional: audio visualization configuration
  // audioVisualizerType: 'bar',
  // audioVisualizerColor: '#002cf2',
  // audioVisualizerColorDark: '#1fd5f9',
  // audioVisualizerColorShift: 0.3,
  // audioVisualizerBarCount: 5,
  // audioVisualizerType: 'radial',
  // audioVisualizerRadialBarCount: 24,
  // audioVisualizerRadialRadius: 100,
  // audioVisualizerType: 'grid',
  // audioVisualizerGridRowCount: 25,
  // audioVisualizerGridColumnCount: 25,
  // audioVisualizerType: 'wave',
  // audioVisualizerWaveLineWidth: 3,
  // audioVisualizerType: 'aura',

  // agent dispatch configuration
  agentName: process.env.NEXT_PUBLIC_AGENT_NAME ?? 'my-agent',

  // LiveKit Cloud Sandbox configuration
  sandboxId: undefined,
};
