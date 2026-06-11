'use client';

import React, { type ReactNode } from 'react';
import { type MotionProps, motion } from 'motion/react';
import { type ReceivedMessage, useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { Button } from '@/components/ui/button';
import {
  type SessionTelemetrySnapshot,
  useSessionTelemetry,
} from '@/hooks/useSessionTelemetry';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.4,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.3,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

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

interface OrderSnapshot {
  serviceType?: string;
  items: string[];
  flavor?: string;
  style?: string;
  drink?: string;
  pickupTime?: string;
  confirmed: boolean;
  stageLabel: string;
  rawSegments: string[];
}

interface LatencySnapshot {
  completedTurns: number;
  userMessages: number;
  agentMessages: number;
  lastReplyMs: number | null;
  averageReplyMs: number | null;
  longestReplyMs: number | null;
}

interface OrderPanelState {
  serviceType: string | null;
  items: string[];
  flavor: string | null;
  style: string | null;
  drink: string | null;
  pickupTime: string | null;
  confirmed: boolean;
  total: string | null;
  mockOrderNumber: string | null;
  stageLabel: string;
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

function deriveLatencySnapshot(messages: ReceivedMessage[]): LatencySnapshot {
  const responseTimes: number[] = [];
  let pendingUserTimestamp: number | null = null;
  let userMessages = 0;
  let agentMessages = 0;

  for (const message of messages) {
    const timestamp = new Date(message.timestamp).getTime();

    if (message.from?.isLocal) {
      userMessages += 1;
      pendingUserTimestamp = timestamp;
      continue;
    }

    agentMessages += 1;
    if (pendingUserTimestamp !== null) {
      responseTimes.push(Math.max(0, timestamp - pendingUserTimestamp));
      pendingUserTimestamp = null;
    }
  }

  const totalResponseTime = responseTimes.reduce((sum, value) => sum + value, 0);

  return {
    completedTurns: responseTimes.length,
    userMessages,
    agentMessages,
    lastReplyMs: responseTimes.at(-1) ?? null,
    averageReplyMs: responseTimes.length > 0 ? totalResponseTime / responseTimes.length : null,
    longestReplyMs: responseTimes.length > 0 ? Math.max(...responseTimes) : null,
  };
}

function buildLatencySnapshotFromTelemetry(
  snapshot: SessionTelemetrySnapshot | null,
  fallback: LatencySnapshot
): LatencySnapshot {
  if (!snapshot) {
    return fallback;
  }

  const assistantMetrics = snapshot.assistant_turn_metrics;
  return {
    completedTurns: snapshot.turn_count || fallback.completedTurns,
    userMessages: fallback.userMessages,
    agentMessages: fallback.agentMessages,
    lastReplyMs:
      typeof assistantMetrics?.e2e_latency === 'number' ? assistantMetrics.e2e_latency * 1000 : null,
    averageReplyMs:
      typeof assistantMetrics?.e2e_latency === 'number'
        ? assistantMetrics.e2e_latency * 1000
        : fallback.averageReplyMs,
    longestReplyMs:
      typeof assistantMetrics?.e2e_latency === 'number'
        ? assistantMetrics.e2e_latency * 1000
        : fallback.longestReplyMs,
  };
}

function deriveOrderSnapshot(
  orderSummary: ParsedOrderSummary | null,
  finalMockOrder: ParsedFinalOrder | null,
  messageCount: number
): OrderSnapshot {
  const summaryText = finalMockOrder?.summary ?? orderSummary?.summary ?? '';
  const rawSegments = summaryText
    .replace(/^Current order:\s*/i, '')
    .replace(/\.$/, '')
    .split(';')
    .map((segment) => segment.trim())
    .filter(Boolean);

  const snapshot: OrderSnapshot = {
    items: [],
    confirmed: false,
    stageLabel: messageCount === 0 ? 'Waiting for conversation' : 'Collecting order details',
    rawSegments,
  };

  for (const segment of rawSegments) {
    const normalizedSegment = segment.toLowerCase();

    if (normalizedSegment.endsWith(' order')) {
      snapshot.serviceType = segment.replace(/\s+order$/i, '');
      continue;
    }

    if (normalizedSegment.startsWith('items:')) {
      snapshot.items = segment
        .replace(/^items:\s*/i, '')
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
      continue;
    }

    if (normalizedSegment.startsWith('flavor:')) {
      snapshot.flavor = segment.replace(/^flavor:\s*/i, '').trim();
      continue;
    }

    if (normalizedSegment.startsWith('style:')) {
      snapshot.style = segment.replace(/^style:\s*/i, '').trim();
      continue;
    }

    if (normalizedSegment.startsWith('drink:')) {
      snapshot.drink = segment.replace(/^drink:\s*/i, '').trim();
      continue;
    }

    if (normalizedSegment.startsWith('pickup time:')) {
      snapshot.pickupTime = segment.replace(/^pickup time:\s*/i, '').trim();
      continue;
    }

    if (normalizedSegment === 'confirmed') {
      snapshot.confirmed = true;
    }
  }

  if (finalMockOrder) {
    snapshot.stageLabel = 'Mock order created';
  } else if (snapshot.confirmed) {
    snapshot.stageLabel = 'Confirmed, awaiting mock order';
  } else if (orderSummary?.summary) {
    snapshot.stageLabel = 'Reviewing recap before confirmation';
  }

  return snapshot;
}

function buildOrderPanelState(
  snapshot: SessionTelemetrySnapshot | null,
  fallbackOrderSummary: ParsedOrderSummary | null,
  fallbackFinalMockOrder: ParsedFinalOrder | null,
  messageCount: number
): OrderPanelState {
  if (!snapshot) {
    const fallback = deriveOrderSnapshot(fallbackOrderSummary, fallbackFinalMockOrder, messageCount);
    return {
      serviceType: fallback.serviceType ?? null,
      items: fallback.items,
      flavor: fallback.flavor ?? null,
      style: fallback.style ?? null,
      drink: fallback.drink ?? null,
      pickupTime: fallback.pickupTime ?? null,
      confirmed: fallback.confirmed,
      total: fallbackFinalMockOrder?.total ?? fallbackOrderSummary?.total ?? null,
      mockOrderNumber: fallbackFinalMockOrder?.orderNumber ?? null,
      stageLabel: fallback.stageLabel,
    };
  }

  const { order, mock_order: mockOrder } = snapshot;
  const hasOrderDetails =
    Boolean(order.pickup_or_delivery) ||
    order.items.length > 0 ||
    Boolean(order.flavor) ||
    Boolean(order.classic_or_boneless) ||
    Boolean(order.drink) ||
    Boolean(order.pickup_time);

  const stageLabel = mockOrder
    ? 'Mock order created'
    : order.confirmed
      ? 'Confirmed, awaiting mock order'
      : hasOrderDetails
        ? 'Collecting live order details'
        : messageCount > 0
          ? 'Listening for order details'
          : 'Waiting for conversation';

  return {
    serviceType: order.pickup_or_delivery,
    items: order.items,
    flavor: order.flavor,
    style: order.classic_or_boneless,
    drink: order.drink,
    pickupTime: order.pickup_time,
    confirmed: order.confirmed,
    total: mockOrder?.total ?? fallbackOrderSummary?.total ?? null,
    mockOrderNumber: mockOrder?.order_number ?? null,
    stageLabel,
  };
}

function formatLatency(ms: number | null): string {
  if (ms === null) {
    return 'Waiting';
  }

  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(ms >= 10000 ? 1 : 2)}s`;
  }

  return `${Math.round(ms)}ms`;
}

function formatCount(label: string, count: number): string {
  return `${count} ${label}${count === 1 ? '' : 's'}`;
}

function getSessionHeadline(
  finalMockOrder: ParsedFinalOrder | null,
  orderSummary: ParsedOrderSummary | null,
  messageCount: number
): string {
  if (finalMockOrder) {
    return `Mock order ${finalMockOrder.orderNumber} is ready to review.`;
  }

  if (orderSummary) {
    return 'The order recap is live. Review the details before confirming.';
  }

  if (messageCount > 0) {
    return 'The agent is actively building the order from the conversation.';
  }

  return 'Start the conversation to populate the order state, transcript, and timing panels.';
}

interface StatusPillProps {
  active: boolean;
  label: string;
}

function StatusPill({ active, label }: StatusPillProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-[10px] tracking-[0.22em] uppercase shadow-sm backdrop-blur',
        active
          ? 'border-emerald-500/35 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300'
          : 'border-border bg-background/80 text-muted-foreground'
      )}
    >
      <span
        className={cn(
          'inline-block size-1.5 rounded-full',
          active ? 'bg-emerald-500' : 'bg-muted-foreground/50'
        )}
      />
      {label}
    </span>
  );
}

interface ShellPanelProps {
  title: string;
  description?: string;
  className?: string;
  children: ReactNode;
}

function ShellPanel({ title, description, className, children }: ShellPanelProps) {
  return (
    <section
      className={cn(
        'rounded-[28px] border border-border/70 bg-background/82 p-5 shadow-xl shadow-black/5 backdrop-blur',
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-foreground">
            {title}
          </p>
          {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  tone?: 'default' | 'good' | 'warn';
}

function MetricCard({ label, value, tone = 'default' }: MetricCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border px-4 py-3',
        tone === 'good' && 'border-emerald-500/25 bg-emerald-500/10',
        tone === 'warn' && 'border-amber-500/25 bg-amber-500/10',
        tone === 'default' && 'border-border/70 bg-muted/25'
      )}
    >
      <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-xl font-semibold tracking-tight text-foreground">{value}</p>
    </div>
  );
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
  const { state: agentState } = useAgent();
  const telemetrySnapshot = useSessionTelemetry();
  const [chatOpen, setChatOpen] = React.useState(true);
  const isListening = agentState === 'listening';
  const isSpeaking = agentState === 'speaking';
  const orderSummary = extractOrderSummary(messages);
  const finalMockOrder = extractFinalMockOrder(messages);
  const latencyFallback = deriveLatencySnapshot(messages);
  const latencySnapshot = buildLatencySnapshotFromTelemetry(telemetrySnapshot, latencyFallback);
  const orderPanel = buildOrderPanelState(
    telemetrySnapshot,
    orderSummary,
    finalMockOrder,
    messages.length
  );
  const sessionHeadline = getSessionHeadline(finalMockOrder, orderSummary, messages.length);
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

  return (
    <section
      ref={ref}
      className={cn(
        'relative min-h-svh overflow-y-auto bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(241,245,249,0.96))] dark:bg-[linear-gradient(180deg,rgba(9,9,11,0.98),rgba(17,24,39,0.97))]',
        className
      )}
      {...props}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.16),transparent_28%),radial-gradient(circle_at_top_right,rgba(16,185,129,0.10),transparent_24%)]" />

      <div className="relative mx-auto flex min-h-svh max-w-[1600px] flex-col px-4 py-4 md:px-6 md:py-6 xl:px-8">
        <div className="rounded-[30px] border border-border/70 bg-background/76 p-5 shadow-xl shadow-black/5 backdrop-blur">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="font-mono text-[11px] tracking-[0.28em] uppercase text-muted-foreground">
                VoixAI Operator Console
              </p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
                Production-style live voice ordering view
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
                {sessionHeadline}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 xl:justify-end">
              {roomName && <StatusPill active label={`Room ${roomName}`} />}
              <StatusPill active={session.isConnected} label={connectionStatusLabel ?? 'Connected'} />
              <StatusPill active={isListening} label={agentStatusLabel ?? 'Listening'} />
              <StatusPill active={isSpeaking} label="Speaking" />
              <Button
                type="button"
                variant="destructive"
                disabled={!session.isConnected}
                onClick={session.end}
                className="h-9 rounded-full px-4 font-mono text-[11px] tracking-[0.18em] uppercase"
              >
                End Conversation
              </Button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Last assistant reply"
              value={formatLatency(latencySnapshot.lastReplyMs)}
              tone={
                latencySnapshot.lastReplyMs !== null && latencySnapshot.lastReplyMs > 2500
                  ? 'warn'
                  : 'good'
              }
            />
            <MetricCard
              label="Average reply time"
              value={formatLatency(latencySnapshot.averageReplyMs)}
              tone={
                latencySnapshot.averageReplyMs !== null && latencySnapshot.averageReplyMs > 2200
                  ? 'warn'
                  : 'default'
              }
            />
            <MetricCard
              label="Completed turns"
              value={String(latencySnapshot.completedTurns)}
              tone="default"
            />
            <MetricCard
              label="Transcript volume"
              value={`${latencySnapshot.userMessages}/${latencySnapshot.agentMessages}`}
              tone="default"
            />
          </div>
        </div>

        <div className="mt-4 grid min-h-0 flex-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)_380px]">
          <aside className="flex min-h-0 flex-col gap-4">
            <ShellPanel
              title="Order State"
              description="The latest order recap stays pinned here while the call is active."
              className="min-h-0"
            >
              <div className="space-y-4">
                <div className="rounded-2xl border border-border/70 bg-muted/20 p-4">
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                    Current stage
                  </p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {orderPanel.stageLabel}
                  </p>
                  {orderPanel.mockOrderNumber && (
                    <p className="mt-2 font-mono text-sm text-foreground">
                      {orderPanel.mockOrderNumber}
                      {orderPanel.total ? ` / ${orderPanel.total}` : ''}
                    </p>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <div className="rounded-2xl border border-border/70 p-4">
                    <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                      Service
                    </p>
                    <p className="mt-2 text-sm font-medium text-foreground">
                      {orderPanel.serviceType ?? 'Not captured yet'}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-border/70 p-4">
                    <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                      Drink and style
                    </p>
                    <p className="mt-2 text-sm font-medium text-foreground">
                      {[orderPanel.drink, orderPanel.style].filter(Boolean).join(' / ') ||
                        'Waiting for order details'}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/70 p-4">
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                    Items
                  </p>
                  {orderPanel.items.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {orderPanel.items.map((item) => (
                        <li
                          key={item}
                          className="rounded-xl bg-muted/25 px-3 py-2 text-sm text-foreground"
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-muted-foreground">
                      Items will appear here once the agent recaps the order.
                    </p>
                  )}
                </div>

                <div className="rounded-2xl border border-border/70 p-4">
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                    Summary details
                  </p>
                  <dl className="mt-3 space-y-2 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-muted-foreground">Flavor</dt>
                      <dd className="text-right text-foreground">
                        {orderPanel.flavor ?? 'Not set'}
                      </dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-muted-foreground">Pickup time</dt>
                      <dd className="text-right text-foreground">
                        {orderPanel.pickupTime ?? 'Not set'}
                      </dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-muted-foreground">Confirmation</dt>
                      <dd className="text-right text-foreground">
                        {orderPanel.confirmed ? 'Confirmed' : 'Pending'}
                      </dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-muted-foreground">Demo total</dt>
                      <dd className="text-right text-foreground">
                        {orderPanel.total ?? 'Waiting'}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </ShellPanel>

            <ShellPanel
              title="Operator Guide"
              description="Use this script to steer the conversation and test corrections."
            >
              <ul className="space-y-3">
                {suggestedPrompts.map((prompt, index) => (
                  <li key={prompt} className="flex gap-3">
                    <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] text-foreground">
                      {index + 1}
                    </span>
                    <span className="text-sm leading-6 text-muted-foreground">{prompt}</span>
                  </li>
                ))}
              </ul>
            </ShellPanel>
          </aside>

          <div className="flex min-h-0 flex-col gap-3">
            <ShellPanel
              title="Live Session"
              description="The voice session stays centered while controls remain docked below it."
              className="flex min-h-[340px] flex-col overflow-hidden p-0"
            >
              <div className="relative min-h-[340px] overflow-hidden rounded-[24px] border border-border/60 bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.08),transparent_34%),linear-gradient(180deg,rgba(248,250,252,0.98),rgba(241,245,249,0.94))] dark:bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.12),transparent_34%),linear-gradient(180deg,rgba(9,9,11,0.95),rgba(17,24,39,0.96))]">
                <div className="absolute left-5 top-5 z-10 flex flex-wrap items-center gap-2">
                  <StatusPill active={session.isConnected} label="Session live" />
                  <StatusPill active={isListening} label="Listening" />
                  <StatusPill active={isSpeaking} label="Speaking" />
                </div>

                <div className="absolute bottom-5 left-5 z-10 max-w-md rounded-2xl border border-border/70 bg-background/78 px-4 py-3 shadow-lg backdrop-blur">
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                    Live notes
                  </p>
                  <p className="mt-2 text-sm leading-6 text-foreground">
                    {messages.length > 0
                      ? 'Keep the conversation short and specific for the cleanest turn timing and order recap updates.'
                      : preConnectMessage}
                  </p>
                </div>

                <div className="absolute inset-0">
                  <TileLayout
                    chatOpen={false}
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
                </div>
              </div>
            </ShellPanel>

            {isPreConnectBufferEnabled && messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="block rounded-2xl border border-border/70 bg-background/82 px-5 py-4 text-center text-sm font-medium text-muted-foreground shadow-lg shadow-black/5"
              >
                {preConnectMessage}
              </MotionMessage>
            )}

            <AgentControlBar
              variant="livekit"
              controls={controls}
              isChatOpen={chatOpen}
              isConnected={session.isConnected}
              onDisconnect={session.end}
              onIsChatOpenChange={setChatOpen}
              className="rounded-[28px] border-border/70 bg-background/88 shadow-xl shadow-black/5"
            />
          </div>

          <aside className="flex min-h-0 flex-col gap-4">
            <ShellPanel
              title="Latency Metrics"
              description="These browser-side timing estimates show how quickly the agent answers each user turn."
            >
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <MetricCard
                  label="End-to-end latency"
                  value={
                    telemetrySnapshot?.assistant_turn_metrics?.e2e_latency !== null &&
                    telemetrySnapshot?.assistant_turn_metrics?.e2e_latency !== undefined
                      ? formatLatency(telemetrySnapshot.assistant_turn_metrics.e2e_latency * 1000)
                      : formatLatency(latencySnapshot.lastReplyMs)
                  }
                  tone={
                    latencySnapshot.lastReplyMs !== null && latencySnapshot.lastReplyMs > 1500
                      ? 'warn'
                      : 'good'
                  }
                />
                <MetricCard
                  label="LLM first token"
                  value={
                    telemetrySnapshot?.assistant_turn_metrics?.llm_ttft !== null &&
                    telemetrySnapshot?.assistant_turn_metrics?.llm_ttft !== undefined
                      ? formatLatency(telemetrySnapshot.assistant_turn_metrics.llm_ttft * 1000)
                      : formatLatency(latencySnapshot.averageReplyMs)
                  }
                  tone={
                    telemetrySnapshot?.assistant_turn_metrics?.llm_ttft !== null &&
                    telemetrySnapshot?.assistant_turn_metrics?.llm_ttft !== undefined &&
                    telemetrySnapshot.assistant_turn_metrics.llm_ttft * 1000 > 800
                      ? 'warn'
                      : 'default'
                  }
                />
                <MetricCard
                  label="TTS first byte"
                  value={
                    telemetrySnapshot?.assistant_turn_metrics?.tts_ttfb !== null &&
                    telemetrySnapshot?.assistant_turn_metrics?.tts_ttfb !== undefined
                      ? formatLatency(telemetrySnapshot.assistant_turn_metrics.tts_ttfb * 1000)
                      : formatLatency(latencySnapshot.longestReplyMs)
                  }
                  tone="default"
                />
                <div className="rounded-2xl border border-border/70 bg-muted/20 px-4 py-3">
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
                    Turn and target
                  </p>
                  <p className="mt-2 text-sm leading-6 text-foreground">
                    {formatCount('caller turn', latencySnapshot.userMessages)}
                  </p>
                  <p className="text-sm leading-6 text-foreground">
                    {formatCount('assistant turn', latencySnapshot.agentMessages)}
                  </p>
                  <p className="pt-2 font-mono text-[11px] text-muted-foreground">
                    Target: under{' '}
                    {formatLatency(
                      telemetrySnapshot?.target_e2e_latency_ms ?? 800
                    )}{' '}
                    ideal
                  </p>
                </div>
              </div>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                These numbers now prefer agent-published telemetry from the LiveKit room. If that
                channel is unavailable, the panel falls back to rough browser-observed timings.
              </p>
            </ShellPanel>

            <div className="min-h-[420px] flex-1">
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="h-full"
              />
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
