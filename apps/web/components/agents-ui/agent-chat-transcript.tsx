'use client';

import { type ComponentProps } from 'react';
import { AnimatePresence } from 'motion/react';
import { type AgentState, type ReceivedMessage } from '@livekit/components-react';
import { AgentChatIndicator } from '@/components/agents-ui/agent-chat-indicator';
import { cn } from '@/lib/shadcn/utils';

/**
 * Props for the AgentChatTranscript component.
 */
export interface AgentChatTranscriptProps extends ComponentProps<'div'> {
  /**
   * The current state of the agent. When 'thinking', displays a loading indicator.
   */
  agentState?: AgentState;
  /**
   * Array of messages to display in the transcript.
   * @defaultValue []
   */
  messages?: ReceivedMessage[];
  /**
   * Additional CSS class names to apply to the conversation container.
   */
  className?: string;
}

/**
 * A chat transcript component that displays a conversation between the user and agent.
 * Shows messages with timestamps and origin indicators, plus a thinking indicator
 * when the agent is processing.
 *
 * @extends ComponentProps<'div'>
 *
 * @example
 * ```tsx
 * <AgentChatTranscript
 *   agentState={agentState}
 *   messages={chatMessages}
 * />
 * ```
 */
export function AgentChatTranscript({
  agentState,
  messages = [],
  className,
  ...props
}: AgentChatTranscriptProps) {
  return (
    <div
      className={cn(
        'flex h-full min-h-0 flex-col overflow-hidden rounded-[28px] border bg-background/88 shadow-lg shadow-black/5 backdrop-blur',
        className
      )}
      {...props}
    >
      <div className="sticky top-0 z-10 border-b bg-background/92 px-5 py-4 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-foreground">
              Transcript
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {messages.length > 0
                ? `${messages.length} live message${messages.length === 1 ? '' : 's'}`
                : 'Live transcript will appear here once the session starts.'}
            </p>
          </div>
          {agentState === 'thinking' && <AgentChatIndicator size="sm" />}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3 [scrollbar-width:thin]">
        <div className="space-y-3">
          {messages.map((receivedMessage, index) => {
            const { id, timestamp, from, message } = receivedMessage;
            const locale = typeof navigator !== 'undefined' ? navigator.language : 'en-US';
            const messageOrigin = from?.isLocal ? 'user' : 'assistant';
            const time = new Date(timestamp);
            const title = time.toLocaleTimeString(locale, {
              hour: 'numeric',
              minute: '2-digit',
              second: '2-digit',
            });
            const previousMessage = index > 0 ? messages[index - 1] : null;
            const responseGapMs =
              previousMessage && previousMessage.from?.isLocal !== from?.isLocal
                ? Math.max(
                    0,
                    new Date(timestamp).getTime() - new Date(previousMessage.timestamp).getTime()
                  )
                : null;

            return (
              <article
                key={id}
                className={cn(
                  'rounded-2xl border px-4 py-3',
                  messageOrigin === 'user'
                    ? 'ml-6 border-sky-500/25 bg-sky-500/10'
                    : 'mr-6 border-border bg-muted/30'
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-mono text-[10px] tracking-[0.22em] uppercase text-foreground">
                    {messageOrigin === 'user' ? 'Caller' : 'Agent'}
                  </p>
                  <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                    <span>{title}</span>
                    {responseGapMs !== null && (
                      <span>{`${(responseGapMs / 1000).toFixed(2)}s gap`}</span>
                    )}
                  </div>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground/92">
                  {message}
                </p>
              </article>
            );
          })}

          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed px-4 py-5 text-sm leading-6 text-muted-foreground">
              Start speaking and the transcript, response timings, and order recap cues will build
              here in real time.
            </div>
          )}
        </div>

        <AnimatePresence>
          {agentState === 'thinking' && (
            <div className="px-2 pt-3">
              <AgentChatIndicator size="sm" />
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
