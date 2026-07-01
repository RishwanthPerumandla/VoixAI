export type IntelligenceEventKind =
  | 'intent_detected'
  | 'entity_extracted'
  | 'tool_called'
  | 'tool_completed'
  | 'state_changed'
  | 'validation_error'
  | 'order_updated'
  | 'quote_received'
  | 'guardrail_triggered'
  | 'system_message';

export type IntelligenceEventStatus = 'active' | 'completed' | 'failed' | 'info';

export interface IntelligenceEvent {
  id: string;
  kind: IntelligenceEventKind;
  status: IntelligenceEventStatus;
  label: string;
  detail?: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface BackendWorkflowStep {
  id: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  detail?: string;
  timestamp?: number;
}

export interface IntelligenceTimelineState {
  events: IntelligenceEvent[];
  backendSteps: BackendWorkflowStep[];
  lastUpdated: number;
}

export type WorkflowStage =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'menu_lookup'
  | 'order_building'
  | 'validation'
  | 'pricing'
  | 'confirmation'
  | 'placed';

const WORKFLOW_STAGE_LABELS: Record<WorkflowStage, string> = {
  idle: 'Waiting',
  listening: 'Listening',
  processing: 'Processing',
  menu_lookup: 'Looking up menu',
  order_building: 'Building order',
  validation: 'Validating',
  pricing: 'Calculating price',
  confirmation: 'Confirming',
  placed: 'Placed',
};

export function getWorkflowStageLabel(stage: WorkflowStage): string {
  return WORKFLOW_STAGE_LABELS[stage];
}

export const WORKFLOW_STAGES: WorkflowStage[] = [
  'listening',
  'processing',
  'menu_lookup',
  'order_building',
  'validation',
  'pricing',
  'confirmation',
  'placed',
];
