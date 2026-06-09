'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import {
  type ReceivedMessage,
  useAgent,
  useSessionContext,
  useSessionMessages,
} from '@livekit/components-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

interface StatusIndicatorProps {
  active: boolean;
  label: string;
}

function StatusIndicator({ active, label }: StatusIndicatorProps) {
  return (
    <span
      className={cn(
        'rounded-full border px-3 py-1 font-mono text-[10px] tracking-wide uppercase shadow-sm backdrop-blur',
        active
          ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-700'
          : 'bg-background/85 text-muted-foreground'
      )}
    >
      <span
        className={cn(
          'mr-2 inline-block size-1.5 rounded-full align-middle',
          active ? 'bg-emerald-500' : 'bg-muted-foreground/50'
        )}
      />
      {label}
    </span>
  );
}

interface DemoPanelProps {
  title: string;
  className?: string;
  children: React.ReactNode;
}

function DemoPanel({ title, className, children }: DemoPanelProps) {
  return (
    <section
      className={cn(
        'rounded-[24px] border bg-background/88 p-5 shadow-lg shadow-black/5 backdrop-blur',
        className
      )}
    >
      <p className="text-foreground font-mono text-[11px] tracking-[0.24em] uppercase">{title}</p>
      <div className="mt-4">{children}</div>
    </section>
  );
}

interface ParsedOrderSummary {
  summary: string;
  total?: string;
}

interface ParsedFinalOrder {
  orderNumber: string;
  total?: string;
  summary?: string;
  rawMessage: string;
}

const ORDER_NUMBER_PATTERN = /VX-\d{4}/i;
const TOTAL_PATTERN = /Demo total:\s*(\$\d+(?:\.\d{2})?)/i;

function extractOrderSummary(messages: ReceivedMessage[]): ParsedOrderSummary | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const entry = messages[index];
    if (entry.from?.isLocal) continue;

    const summaryMatch = entry.message.match(
      /Current order:\s*(.+?)(?:\s*Demo total:|\s*Should I place this mock order\?|\s*$)/i
    );
    if (!summaryMatch) continue;

    const totalMatch = entry.message.match(TOTAL_PATTERN);
    return {
      summary: summaryMatch[1].trim(),
      total: totalMatch?.[1],
    };
  }

  return null;
}

function extractFinalMockOrder(messages: ReceivedMessage[]): ParsedFinalOrder | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const entry = messages[index];
    if (entry.from?.isLocal) continue;

    const orderNumberMatch = entry.message.match(ORDER_NUMBER_PATTERN);
    if (!orderNumberMatch) continue;

    const totalMatch = entry.message.match(TOTAL_PATTERN);
    const summaryMatch = entry.message.match(/Current order:\s*(.+?)(?:\s*$)/i);
    return {
      orderNumber: orderNumberMatch[0].toUpperCase(),
      total: totalMatch?.[1],
      summary: summaryMatch?.[1]?.trim(),
      rawMessage: entry.message.trim(),
    };
  }

  return null;
}

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  className?: string;
  connectionStatusLabel?: string;
  agentStatusLabel?: string;
  roomName?: string;
}

export function AgentSessionView_01({
  preConnectMessage = 'Agent is listening, ask it a question',
  supportsChatInput = true,
  supportsVideoInput = true,
  supportsScreenShare = true,
  isPreConnectBufferEnabled = true,
  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,
  connectionStatusLabel,
  agentStatusLabel,
  roomName,
  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();
  const isListening = agentState === 'listening';
  const isSpeaking = agentState === 'speaking';
  const recentMessages = messages.slice(-6);
  const orderSummary = extractOrderSummary(messages);
  const finalMockOrder = extractFinalMockOrder(messages);
  const suggestedPrompts = [
    'I want ten lemon pepper wings for pickup.',
    'Actually, make that boneless.',
    'Add fries and change the drink to lemonade.',
    'Can you recap the order before I confirm?',
  ];

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: supportsVideoInput,
    screenShare: supportsScreenShare,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section
      ref={ref}
      className={cn('bg-background relative z-10 h-full w-full overflow-hidden', className)}
      {...props}
    >
      <Fade top className="absolute inset-x-4 top-0 z-10 h-40" />

      <div className="pointer-events-none absolute top-5 left-1/2 z-20 flex -translate-x-1/2 flex-col items-center gap-2">
        {roomName && (
          <p className="bg-background/85 text-foreground rounded-full border px-4 py-2 font-mono text-[11px] tracking-wide uppercase shadow-sm backdrop-blur">
            Room: {roomName}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-center gap-2">
          <StatusIndicator active={session.isConnected} label="Connected" />
          <StatusIndicator active={isListening} label="Listening" />
          <StatusIndicator active={isSpeaking} label="Speaking" />
        </div>
        {(connectionStatusLabel || agentStatusLabel) && (
          <p className="bg-background/85 text-muted-foreground rounded-full border px-4 py-2 font-mono text-[11px] tracking-wide uppercase shadow-sm backdrop-blur">
            {connectionStatusLabel ?? 'Unknown'} · {agentStatusLabel ?? 'Unknown'}
          </p>
        )}
      </div>

      <div className="pointer-events-none absolute inset-x-4 top-32 bottom-40 z-20 hidden xl:block">
        <div className="mx-auto flex h-full max-w-[1280px] items-start justify-between gap-6">
          <aside className="pointer-events-auto flex w-72 flex-col justify-end gap-4">
            <DemoPanel title="Demo Script">
              <ul className="space-y-3">
                {suggestedPrompts.map((prompt, index) => (
                  <li key={prompt} className="flex gap-3">
                    <span className="text-foreground mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border font-mono text-[10px]">
                      {index + 1}
                    </span>
                    <span className="text-muted-foreground text-sm leading-6">{prompt}</span>
                  </li>
                ))}
              </ul>
            </DemoPanel>

            <DemoPanel title="Session Notes">
              <p className="text-muted-foreground text-sm leading-6">
                Ask for a recap before you confirm. The live order summary and final mock order
                appear on the right as the conversation progresses.
              </p>
            </DemoPanel>
          </aside>

          <aside className="pointer-events-auto flex w-80 flex-col gap-4">
            <DemoPanel title="Current Order Summary">
              {orderSummary ? (
                <div className="space-y-3">
                  <ul className="space-y-2">
                    {orderSummary.summary.split(';').map((item) => (
                      <li key={item} className="text-muted-foreground text-sm leading-6">
                        {item.trim()}
                      </li>
                    ))}
                  </ul>
                  {orderSummary.total && (
                    <p className="text-foreground font-mono text-sm font-semibold">
                      Demo total: {orderSummary.total}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm leading-6">
                  Ask the agent for a recap to surface the current order and demo total here.
                </p>
              )}
            </DemoPanel>

            <DemoPanel title="Final Mock Order">
              {finalMockOrder ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-foreground font-mono text-lg font-semibold">
                      {finalMockOrder.orderNumber}
                    </p>
                    {finalMockOrder.total && (
                      <p className="text-foreground font-mono text-sm">{finalMockOrder.total}</p>
                    )}
                  </div>
                  <p className="text-muted-foreground text-sm leading-6">
                    {finalMockOrder.summary ?? finalMockOrder.rawMessage}
                  </p>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm leading-6">
                  Confirm the mock order and the VX order number will appear here.
                </p>
              )}
            </DemoPanel>

            <DemoPanel title="Recent Transcript" className="min-h-0 flex-1">
              <div className="space-y-3">
                {recentMessages.length > 0 ? (
                  recentMessages.map((entry) => (
                    <div
                      key={entry.id}
                      className={cn(
                        'rounded-2xl border px-4 py-3 text-sm leading-6',
                        entry.from?.isLocal
                          ? 'ml-6 border-blue-500/20 bg-blue-500/8'
                          : 'mr-6 bg-muted/35'
                      )}
                    >
                      <p className="text-foreground mb-1 font-mono text-[10px] tracking-wide uppercase">
                        {entry.from?.isLocal ? 'You' : 'Agent'}
                      </p>
                      <p className="text-muted-foreground">{entry.message}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground text-sm leading-6">
                    The live transcript will appear here after the conversation starts.
                  </p>
                )}
              </div>
            </DemoPanel>
          </aside>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-3 bottom-28 z-40 xl:hidden">
        <div className="pointer-events-auto mx-auto max-w-md">
          <DemoPanel title={finalMockOrder ? 'Final Mock Order' : 'Current Order Summary'}>
            {finalMockOrder ? (
              <div className="space-y-2">
                <p className="text-foreground font-mono text-base font-semibold">
                  {finalMockOrder.orderNumber}
                  {finalMockOrder.total ? ` · ${finalMockOrder.total}` : ''}
                </p>
                <p className="text-muted-foreground text-sm leading-6">
                  {finalMockOrder.summary ?? finalMockOrder.rawMessage}
                </p>
              </div>
            ) : orderSummary ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-sm leading-6">{orderSummary.summary}</p>
                {orderSummary.total && (
                  <p className="text-foreground font-mono text-sm">Demo total: {orderSummary.total}</p>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm leading-6">
                Ask for a recap or confirm the order to surface the latest demo summary here.
              </p>
            )}
          </DemoPanel>
        </div>
      </div>

      <div className="absolute top-0 bottom-[135px] flex w-full flex-col md:bottom-[170px]">
        <AnimatePresence>
          {chatOpen && (
            <motion.div
              {...CHAT_MOTION_PROPS}
              className="flex h-full w-full flex-col gap-4 space-y-3 transition-opacity duration-300 ease-out"
            >
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="mx-auto w-full max-w-2xl [&_.is-user>div]:rounded-[22px] [&>div>div]:px-4 [&>div>div]:pt-40 md:[&>div>div]:px-6"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <TileLayout
        chatOpen={chatOpen}
        audioVisualizerType={audioVisualizerType}
        audioVisualizerColor={audioVisualizerColor}
        audioVisualizerColorShift={audioVisualizerColorShift}
        audioVisualizerBarCount={audioVisualizerBarCount}
        audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
        audioVisualizerRadialRadius={audioVisualizerRadialRadius}
        audioVisualizerGridRowCount={audioVisualizerGridRowCount}
        audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
        audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
      />

      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {isPreConnectBufferEnabled && (
          <AnimatePresence>
            {messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="pointer-events-none mx-auto block w-full max-w-2xl pb-4 text-center text-sm font-semibold"
              >
                {preConnectMessage}
              </MotionMessage>
            )}
          </AnimatePresence>
        )}
        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar
            variant="livekit"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={session.end}
            onIsChatOpenChange={setChatOpen}
          />
        </div>
      </motion.div>
    </section>
  );
}
