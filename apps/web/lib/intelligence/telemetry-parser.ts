import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import type {
  BackendWorkflowStep,
  IntelligenceEvent,
  IntelligenceEventKind,
  IntelligenceEventStatus,
  WorkflowStage,
} from './types';

let eventCounter = 0;

function makeId(): string {
  eventCounter += 1;
  return `evt-${Date.now()}-${eventCounter}`;
}

function classifyIntent(order: SessionTelemetrySnapshot['order']): IntelligenceEvent | null {
  if (!order) return null;

  const items = order.line_items ?? [];
  if (items.length === 0) return null;

  const lastItem = items[items.length - 1];
  return {
    id: makeId(),
    kind: 'intent_detected',
    status: 'completed',
    label: 'Order intent',
    detail: `Adding ${lastItem.name} (${lastItem.quantity}x)`,
    timestamp: Date.now(),
    metadata: { item: lastItem },
  };
}

function classifyEntities(order: SessionTelemetrySnapshot['order']): IntelligenceEvent[] {
  const events: IntelligenceEvent[] = [];

  if (order.customer_name) {
    events.push({
      id: makeId(),
      kind: 'entity_extracted',
      status: 'completed',
      label: 'Customer name',
      detail: order.customer_name,
      timestamp: Date.now(),
    });
  }

  if (order.pickup_or_delivery) {
    events.push({
      id: makeId(),
      kind: 'entity_extracted',
      status: 'completed',
      label: 'Order type',
      detail: order.pickup_or_delivery === 'pickup' ? 'Pickup' : 'Delivery',
      timestamp: Date.now(),
    });
  }

  if (order.phone) {
    events.push({
      id: makeId(),
      kind: 'entity_extracted',
      status: 'completed',
      label: 'Phone number',
      detail: order.phone,
      timestamp: Date.now(),
    });
  }

  return events;
}

function detectValidation(order: SessionTelemetrySnapshot['order']): IntelligenceEvent[] {
  const events: IntelligenceEvent[] = [];

  if (order.validation_errors && order.validation_errors.length > 0) {
    for (const error of order.validation_errors) {
      events.push({
        id: makeId(),
        kind: 'validation_error',
        status: 'failed',
        label: 'Validation',
        detail: error,
        timestamp: Date.now(),
      });
    }
  }

  if (order.last_clarification_question) {
    events.push({
      id: makeId(),
      kind: 'system_message',
      status: 'info',
      label: 'Clarification',
      detail: order.last_clarification_question,
      timestamp: Date.now(),
    });
  }

  return events;
}

function detectGuardrails(snapshot: SessionTelemetrySnapshot): IntelligenceEvent[] {
  const events: IntelligenceEvent[] = [];

  if (snapshot.assistant_guardrail_violations && snapshot.assistant_guardrail_violations.length > 0) {
    for (const violation of snapshot.assistant_guardrail_violations) {
      events.push({
        id: makeId(),
        kind: 'guardrail_triggered',
        status: 'failed',
        label: 'Guardrail',
        detail: violation,
        timestamp: Date.now(),
      });
    }
  }

  return events;
}

function detectQuoteEvent(snapshot: SessionTelemetrySnapshot): IntelligenceEvent | null {
  if (!snapshot.price_quote) return null;

  const quote = snapshot.price_quote;
  return {
    id: makeId(),
    kind: 'quote_received',
    status: 'completed',
    label: 'Price quote',
    detail: `$${quote.total} (subtotal: $${quote.subtotal}, tax: $${quote.tax})`,
    timestamp: Date.now(),
    metadata: {
      total: quote.total,
      eta: quote.eta_minutes,
      lineItemCount: quote.line_items.length,
    },
  };
}

function detectOrderUpdated(
  order: SessionTelemetrySnapshot['order'],
  prevOrderHash: string
): { event: IntelligenceEvent | null; hash: string } {
  const currentHash = JSON.stringify({
    items: order.line_items?.map((i) => `${i.item_id}:${i.quantity}:${i.flavors.join(',')}`),
    confirmed: order.confirmed,
    phase: order.phase,
  });

  if (currentHash === prevOrderHash) {
    return { event: null, hash: currentHash };
  }

  const itemCount = order.line_items?.length ?? order.items.length;
  return {
    event: {
      id: makeId(),
      kind: 'order_updated',
      status: order.confirmed ? 'completed' : 'active',
      label: 'Order updated',
      detail: itemCount > 0 ? `${itemCount} item${itemCount !== 1 ? 's' : ''} in order` : 'Empty order',
      timestamp: Date.now(),
      metadata: { itemCount, confirmed: order.confirmed },
    },
    hash: currentHash,
  };
}

function buildWorkflowSteps(
  snapshot: SessionTelemetrySnapshot,
  stage: WorkflowStage
): BackendWorkflowStep[] {
  const steps: BackendWorkflowStep[] = [];
  const order = snapshot.order;
  const hasItems = (order.line_items?.length ?? 0) > 0 || order.items.length > 0;
  const hasPrice = !!snapshot.price_quote;
  const isConfirmed = order.confirmed;
  const isPlaced = !!snapshot.mock_order;

  steps.push({
    id: 'listen',
    label: 'Listen',
    status: stage === 'listening' ? 'in_progress' : stage === 'idle' ? 'pending' : 'completed',
  });

  steps.push({
    id: 'process',
    label: 'Process',
    status: stage === 'processing' ? 'in_progress' : hasItems ? 'completed' : 'pending',
  });

  steps.push({
    id: 'menu',
    label: 'Menu lookup',
    status: stage === 'menu_lookup' ? 'in_progress' : hasItems ? 'completed' : 'pending',
  });

  steps.push({
    id: 'order',
    label: 'Build order',
    status: stage === 'order_building' ? 'in_progress' : hasItems ? 'completed' : 'pending',
  });

  steps.push({
    id: 'validate',
    label: 'Validate',
    status: stage === 'validation' ? 'in_progress' : order.pos_validation_passed ? 'completed' : 'pending',
  });

  steps.push({
    id: 'price',
    label: 'Price',
    status: stage === 'pricing' ? 'in_progress' : hasPrice ? 'completed' : 'pending',
  });

  steps.push({
    id: 'confirm',
    label: 'Confirm',
    status: stage === 'confirmation' ? 'in_progress' : isConfirmed ? 'completed' : 'pending',
  });

  steps.push({
    id: 'place',
    label: 'Place',
    status: isPlaced ? 'completed' : 'pending',
  });

  return steps;
}

function deriveWorkflowStage(snapshot: SessionTelemetrySnapshot): WorkflowStage {
  const order = snapshot.order;
  const hasItems = (order.line_items?.length ?? 0) > 0 || order.items.length > 0;
  const hasPrice = !!snapshot.price_quote;
  const isConfirmed = order.confirmed;
  const isPlaced = !!snapshot.mock_order;

  if (isPlaced) return 'placed';
  if (isConfirmed) return 'confirmation';
  if (hasPrice) return 'pricing';
  if (order.pos_validation_passed === false || (order.validation_errors && order.validation_errors.length > 0)) {
    return 'validation';
  }
  if (hasItems) return 'order_building';
  if (order.phase === 'menu_lookup') return 'menu_lookup';
  if (snapshot.reason.includes('turn') || snapshot.turn_count > 0) return 'processing';
  return 'listening';
}

export interface ParsedIntelligence {
  events: IntelligenceEvent[];
  workflowSteps: BackendWorkflowStep[];
  stage: WorkflowStage;
  orderHash: string;
}

export function parseTelemetryToEvents(
  snapshot: SessionTelemetrySnapshot | null,
  prevOrderHash: string = ''
): ParsedIntelligence {
  if (!snapshot) {
    return {
      events: [],
      workflowSteps: [],
      stage: 'idle',
      orderHash: prevOrderHash,
    };
  }

  const order = snapshot.order;
  const stage = deriveWorkflowStage(snapshot);

  const intent = classifyIntent(order);
  const entities = classifyEntities(order);
  const validations = detectValidation(order);
  const guardrails = detectGuardrails(snapshot);
  const quote = detectQuoteEvent(snapshot);
  const { event: orderUpdate, hash: newHash } = detectOrderUpdated(order, prevOrderHash);

  const events: IntelligenceEvent[] = [
    ...(intent ? [intent] : []),
    ...entities,
    ...validations,
    ...guardrails,
    ...(quote ? [quote] : []),
    ...(orderUpdate ? [orderUpdate] : []),
  ].sort((a, b) => a.timestamp - b.timestamp);

  return {
    events,
    workflowSteps: buildWorkflowSteps(snapshot, stage),
    stage,
    orderHash: newHash,
  };
}
