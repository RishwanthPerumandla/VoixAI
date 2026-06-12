export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;
  activeScenarioId: string;
  activeChannelId: string;
  roomName: string;
  participantName: string;
  apiBaseUrl: string;
  defaultVoiceMode: string;

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
  pageTitle: 'VoixAI Voice AI System',
  pageDescription:
    'VoixAI is a core voice AI system. The current live scenario is Wingstop inbound ordering.',
  activeScenarioId:
    process.env.NEXT_PUBLIC_ACTIVE_SCENARIO_ID ?? 'wingstop_inbound_ordering',
  activeChannelId: process.env.NEXT_PUBLIC_ACTIVE_CHANNEL_ID ?? 'web',
  roomName: process.env.NEXT_PUBLIC_LIVEKIT_ROOM_NAME ?? 'voixai-mvp-demo',
  participantName: process.env.NEXT_PUBLIC_PARTICIPANT_NAME ?? 'web-user',
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000',
  defaultVoiceMode:
    process.env.NEXT_PUBLIC_DEFAULT_VOICE_MODE ??
    process.env.VOICE_PROVIDER ??
    process.env.VOICE_ENGINE ??
    'classic',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/favicon.ico',
  accent: '#c8642a',
  logoDark: '/favicon.ico',
  accentDark: '#ff9254',
  startButtonText: 'Start demo',

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
