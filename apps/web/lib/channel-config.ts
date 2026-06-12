export interface ChannelConfig {
  id: string;
  label: string;
  shortLabel: string;
  landingDescription: string;
  sessionDescription: string;
}

const WEB_CHANNEL: ChannelConfig = {
  id: 'web',
  label: 'Web voice session',
  shortLabel: 'Web',
  landingDescription: 'The current channel is the web voice demo with live transcript and workflow UI.',
  sessionDescription: 'This session is running in the web channel with a live workspace and transcript.',
};

const PHONE_CHANNEL: ChannelConfig = {
  id: 'phone',
  label: 'Inbound phone call',
  shortLabel: 'Phone',
  landingDescription: 'This channel is designed for screenless inbound calls and voice-only guidance.',
  sessionDescription: 'This session is running in the phone channel with screenless-first behavior.',
};

export const CHANNEL_REGISTRY: Record<string, ChannelConfig> = {
  [WEB_CHANNEL.id]: WEB_CHANNEL,
  [PHONE_CHANNEL.id]: PHONE_CHANNEL,
};

export const DEFAULT_CHANNEL_ID = WEB_CHANNEL.id;

export function getChannelConfig(channelId: string | null | undefined): ChannelConfig {
  if (!channelId) {
    return WEB_CHANNEL;
  }

  return CHANNEL_REGISTRY[channelId] ?? WEB_CHANNEL;
}
