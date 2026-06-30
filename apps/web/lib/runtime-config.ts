'use client';

export type VoiceEngine =
  | 'pipeline'
  | 'openai_realtime'
  | 'gemini_live'
  | 'openai_realtime_text'
  | 'gemini_live_text';

export interface RuntimeConfig {
  voiceEngine: VoiceEngine;
  requestedVoiceEngine?: string | null;
  llmModel: string;
  sttModel: string;
  ttsModel: string;
  openaiRealtimeModel: string;
  openaiRealtimeVoice: string;
  openaiRealtimeEagerness: string;
  googleRealtimeModel: string;
  googleRealtimeVoice: string;
  realtimeTemperature: number;
  realtimeEnableAffectiveDialog: boolean;
  realtimeEnableProactivity: boolean;
  presetId: string;
  presetLabel: string;
  comparisonLabel: string;
  fallbackReason?: string | null;
}

export interface RuntimePreset {
  id: string;
  label: string;
  description: string;
  config: RuntimeConfig;
}

export const VOICE_ENGINE_OPTIONS: Array<{
  value: VoiceEngine;
  label: string;
  description: string;
}> = [
  {
    value: 'pipeline',
    label: 'Classic Voice',
    description: 'Separate speech recognition, reasoning, and voice synthesis for the most proven path.',
  },
  {
    value: 'openai_realtime',
    label: 'OpenAI Realtime',
    description: 'Native OpenAI speech-to-speech for the fastest conversational feel.',
  },
  {
    value: 'gemini_live',
    label: 'Gemini Live',
    description: 'Native Gemini speech-to-speech with realtime audio and expressive turn taking.',
  },
];

export const PIPELINE_LLM_OPTIONS = [
  'openai/gpt-5.3-chat-latest',
  'google/gemini-2.5-flash',
] as const;

export const STT_MODEL_OPTIONS = ['deepgram/flux-general', 'deepgram/nova-3'] as const;

export const TTS_MODEL_OPTIONS = ['cartesia/sonic-3'] as const;

export const OPENAI_REALTIME_MODEL_OPTIONS = ['gpt-realtime-2'] as const;

export const GOOGLE_REALTIME_MODEL_OPTIONS = ['gemini-3.1-flash-live-preview'] as const;

export const OPENAI_REALTIME_VOICE_OPTIONS = ['marin'] as const;

export const GOOGLE_REALTIME_VOICE_OPTIONS = ['Achernar', 'Achird', 'Sulafat', 'Kore'] as const;

const buildConfig = (config: RuntimeConfig): RuntimeConfig => config;

export const RUNTIME_PRESETS: RuntimePreset[] = [
  {
    id: 'pipeline-fast',
    label: 'Classic Voice',
    description: 'Best when you want the most established multi-stage voice path.',
    config: buildConfig({
      voiceEngine: 'pipeline',
      llmModel: 'openai/gpt-5.3-chat-latest',
      sttModel: 'deepgram/flux-general',
      ttsModel: 'cartesia/sonic-3',
      openaiRealtimeModel: 'gpt-realtime-2',
      openaiRealtimeVoice: 'marin',
      openaiRealtimeEagerness: 'medium',
      googleRealtimeModel: 'gemini-2.5-flash',
      googleRealtimeVoice: 'Achernar',
      realtimeTemperature: 0.6,
      realtimeEnableAffectiveDialog: false,
      realtimeEnableProactivity: false,
      presetId: 'pipeline-fast',
      presetLabel: 'Classic Voice',
      comparisonLabel: 'Deepgram, text reasoning, and Cartesia speech',
    }),
  },
  {
    id: 'openai-realtime-voice',
    label: 'OpenAI Realtime',
    description: 'Best fit when you want the fastest native OpenAI voice path.',
    config: buildConfig({
      voiceEngine: 'openai_realtime',
      llmModel: 'openai/gpt-5.3-chat-latest',
      sttModel: 'deepgram/flux-general',
      ttsModel: 'cartesia/sonic-3',
      openaiRealtimeModel: 'gpt-realtime-2',
      openaiRealtimeVoice: 'marin',
      openaiRealtimeEagerness: 'medium',
      googleRealtimeModel: 'gemini-2.5-flash',
      googleRealtimeVoice: 'Achernar',
      realtimeTemperature: 0.6,
      realtimeEnableAffectiveDialog: false,
      realtimeEnableProactivity: false,
      presetId: 'openai-realtime-voice',
      presetLabel: 'OpenAI Realtime',
      comparisonLabel: 'Native OpenAI speech to speech',
    }),
  },
  {
    id: 'gemini-live-voice',
    label: 'Gemini Live',
    description: 'Best fit when you want the latest Gemini Live audio-to-audio path.',
    config: buildConfig({
      voiceEngine: 'gemini_live',
      llmModel: 'openai/gpt-5.3-chat-latest',
      sttModel: 'deepgram/flux-general',
      ttsModel: 'cartesia/sonic-3',
      openaiRealtimeModel: 'gpt-realtime-2',
      openaiRealtimeVoice: 'marin',
      openaiRealtimeEagerness: 'medium',
      googleRealtimeModel: 'gemini-3.1-flash-live-preview',
      googleRealtimeVoice: 'Achernar',
      realtimeTemperature: 0.6,
      realtimeEnableAffectiveDialog: false,
      realtimeEnableProactivity: false,
      presetId: 'gemini-live-voice',
      presetLabel: 'Gemini Live',
      comparisonLabel: 'Native Gemini speech to speech',
    }),
  },
];

export const DEFAULT_RUNTIME_CONFIG = RUNTIME_PRESETS[0].config;

export function getDefaultRuntimeConfig(voiceMode?: string | null): RuntimeConfig {
  const normalized = voiceMode?.trim().toLowerCase();

  if (normalized === 'openai_realtime' || normalized === 'openai_realtime_text') {
    return RUNTIME_PRESETS.find((preset) => preset.id === 'openai-realtime-voice')?.config ?? DEFAULT_RUNTIME_CONFIG;
  }

  if (normalized === 'gemini_live' || normalized === 'gemini_live_text') {
    return RUNTIME_PRESETS.find((preset) => preset.id === 'gemini-live-voice')?.config ?? DEFAULT_RUNTIME_CONFIG;
  }

  return DEFAULT_RUNTIME_CONFIG;
}

export function getRuntimePresetById(presetId: string): RuntimePreset | undefined {
  return RUNTIME_PRESETS.find((preset) => preset.id === presetId);
}

export function buildRuntimeConfigSummary(config: RuntimeConfig) {
  return {
    engine:
      VOICE_ENGINE_OPTIONS.find((option) => option.value === config.voiceEngine)?.label ??
      config.voiceEngine,
    llm:
      config.voiceEngine === 'pipeline'
        ? config.llmModel
        : config.voiceEngine.startsWith('openai')
          ? config.openaiRealtimeModel
          : config.googleRealtimeModel,
    stt: config.voiceEngine === 'pipeline' ? config.sttModel : 'Native realtime',
    tts:
      config.voiceEngine === 'pipeline' || config.voiceEngine.endsWith('_text')
        ? config.ttsModel
        : config.voiceEngine === 'openai_realtime'
          ? config.openaiRealtimeVoice
          : config.googleRealtimeVoice,
  };
}

export function toApiRuntimeConfig(config: RuntimeConfig) {
  return {
    voice_engine: config.voiceEngine,
    llm_model: config.llmModel,
    stt_model: config.sttModel,
    tts_model: config.ttsModel,
    openai_realtime_model: config.openaiRealtimeModel,
    openai_realtime_voice: config.openaiRealtimeVoice,
    openai_realtime_eagerness: config.openaiRealtimeEagerness,
    google_realtime_model: config.googleRealtimeModel,
    google_realtime_voice: config.googleRealtimeVoice,
    realtime_temperature: config.realtimeTemperature,
    realtime_enable_affective_dialog: config.realtimeEnableAffectiveDialog,
    realtime_enable_proactivity: config.realtimeEnableProactivity,
    preset_id: config.presetId,
    preset_label: config.presetLabel,
    comparison_label: config.comparisonLabel,
  };
}
