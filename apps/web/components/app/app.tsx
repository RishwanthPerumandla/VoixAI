'use client';

import { useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import {
  getDefaultRuntimeConfig,
  toApiRuntimeConfig,
  type RuntimeConfig,
} from '@/lib/runtime-config';
import { getSandboxTokenSource } from '@/lib/utils';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig>(() =>
    getDefaultRuntimeConfig(appConfig.defaultVoiceMode)
  );
  const [orderSessionId, setOrderSessionId] = useState(() => Date.now().toString());
  const sessionRoomName = useMemo(
    () => `${appConfig.roomName}-${orderSessionId}`,
    [appConfig.roomName, orderSessionId]
  );

  const tokenSource = useMemo(() => {
    return typeof process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT === 'string'
      ? getSandboxTokenSource(appConfig)
      : TokenSource.custom(async () => {
          const response = await fetch(`${appConfig.apiBaseUrl}/api/livekit/token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              room_name: sessionRoomName,
              participant_name: appConfig.participantName,
              runtime_config: {
                ...toApiRuntimeConfig(runtimeConfig),
                scenario_id: appConfig.activeScenarioId,
                channel_id: appConfig.activeChannelId,
              },
            }),
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Unable to start the voice session');
          }

          const data = (await response.json()) as {
            livekit_url: string;
            token: string;
            room_name: string;
          };

          return {
            serverUrl: data.livekit_url,
            participantToken: data.token,
          };
        });
  }, [appConfig, runtimeConfig, sessionRoomName]);

  const session = useSession(tokenSource);
  const handleSessionEnded = () => {
    setOrderSessionId(`${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  };

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="min-h-svh">
        <ViewController
          appConfig={appConfig}
          runtimeConfig={runtimeConfig}
          onRuntimeConfigChange={setRuntimeConfig}
          onSessionEnded={handleSessionEnded}
        />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
