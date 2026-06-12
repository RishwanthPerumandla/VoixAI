import type { ComponentType } from 'react';
import type { UserFacingSessionState } from '@/components/app/session-status';
import { WingstopScenarioConfirmation } from '@/components/app/scenarios/wingstop/wingstop-scenario-confirmation';
import { WingstopScenarioWorkspace } from '@/components/app/scenarios/wingstop/wingstop-scenario-workspace';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import type { ChannelConfig } from '@/lib/channel-config';

export interface ScenarioLandingCopy {
  name: string;
  summary: string | ((channel: ChannelConfig) => string);
  helper: string | ((channel: ChannelConfig) => string);
  howItWorksDescription: string | ((channel: ChannelConfig) => string);
  howItWorksSteps: string[] | ((channel: ChannelConfig) => string[]);
  comingNextDescription: string | ((channel: ChannelConfig) => string);
  primaryActionLabel: string;
  secondaryActionLabel: string;
}

export interface ScenarioSessionCopy {
  headerSubtitle: string | ((channel: ChannelConfig) => string);
  permissionPrompt: string | ((channel: ChannelConfig) => string);
  workspaceEyebrow: string;
  workspaceTitle: string;
  workspaceDescription: string | ((channel: ChannelConfig) => string);
  endDialogTitle: string;
  endDialogDescription: string;
  keepActionLabel: string;
  endActionLabel: string;
}

export interface ScenarioWorkspaceProps {
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  userFacingState: UserFacingSessionState;
  isConnected: boolean;
  onEditWorkflow: () => Promise<void> | void;
  onConfirmWorkflow: () => Promise<void> | void;
}

export interface ScenarioConfirmationProps {
  telemetrySnapshot: SessionTelemetrySnapshot;
  onStartNewFlow: () => void;
  onBackToDemo: () => void;
}

export interface ScenarioConfig {
  id: string;
  platformLabel: string;
  landing: ScenarioLandingCopy;
  session: ScenarioSessionCopy;
  WorkspaceComponent: ComponentType<ScenarioWorkspaceProps>;
  ConfirmationComponent: ComponentType<ScenarioConfirmationProps>;
}

export function resolveScenarioCopy(
  value: string | string[] | ((channel: ChannelConfig) => string | string[]),
  channel: ChannelConfig
) {
  if (typeof value === 'function') {
    return value(channel);
  }

  return value;
}

const WINGSTOP_SCENARIO: ScenarioConfig = {
  id: 'wingstop_inbound_ordering',
  platformLabel: 'VoixAI Voice AI System',
  landing: {
    name: 'Wingstop inbound ordering',
    summary: (channel) =>
      `VoixAI is the core voice AI system. The active scenario is Wingstop inbound ordering on the ${channel.shortLabel.toLowerCase()} channel, with more use cases to follow.`,
    helper: (channel) =>
      `Wingstop ordering is the current live scenario on top of the shared VoixAI session system. ${channel.landingDescription}`,
    howItWorksDescription: (channel) =>
      `VoixAI core session flow with the Wingstop ordering scenario on the ${channel.shortLabel.toLowerCase()} channel.`,
    howItWorksSteps: (channel) => [
      `1. Start the VoixAI ${channel.shortLabel.toLowerCase()} session`,
      '2. Run the Wingstop inbound ordering scenario',
      '3. Review the live workflow and confirm',
    ],
    comingNextDescription: (channel) =>
      `Additional VoixAI scenarios can later include reservations, support intake, appointment booking, and other inbound voice workflows across ${channel.shortLabel.toLowerCase()}, phone, and future channels.`,
    primaryActionLabel: 'Start demo',
    secondaryActionLabel: 'Use text input',
  },
  session: {
    headerSubtitle: (channel) =>
      `Core session shell with Wingstop as the active scenario on ${channel.shortLabel.toLowerCase()}`,
    permissionPrompt: (channel) =>
      channel.id === 'phone'
        ? 'Phone channel sessions are designed for voice-only behavior.'
        : 'Allow microphone access to continue this voice session.',
    workspaceEyebrow: 'Scenario workspace',
    workspaceTitle: 'Wingstop inbound ordering',
    workspaceDescription: (channel) =>
      `This business workflow runs on top of the shared VoixAI voice session. ${channel.sessionDescription}`,
    endDialogTitle: 'End this order?',
    endDialogDescription: 'Your current mock order will be discarded.',
    keepActionLabel: 'Keep ordering',
    endActionLabel: 'End order',
  },
  WorkspaceComponent: WingstopScenarioWorkspace,
  ConfirmationComponent: WingstopScenarioConfirmation,
};

export const SCENARIO_REGISTRY: Record<string, ScenarioConfig> = {
  [WINGSTOP_SCENARIO.id]: WINGSTOP_SCENARIO,
};

export function getScenarioConfig(scenarioId: string | null | undefined): ScenarioConfig {
  if (!scenarioId) {
    return WINGSTOP_SCENARIO;
  }

  return SCENARIO_REGISTRY[scenarioId] ?? WINGSTOP_SCENARIO;
}
