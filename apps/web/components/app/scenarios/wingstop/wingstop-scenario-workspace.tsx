'use client';

import type { UserFacingSessionState } from '@/components/app/session-status';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import {
  WingstopOrderPanel,
  buildWingstopMissingDetails,
  buildWingstopOrderItems,
} from '@/components/app/scenarios/wingstop/wingstop-order-panel';

interface WingstopScenarioWorkspaceProps {
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  userFacingState: UserFacingSessionState;
  isConnected: boolean;
  onEditWorkflow: () => Promise<void> | void;
  onConfirmWorkflow: () => Promise<void> | void;
}

export function WingstopScenarioWorkspace({
  telemetrySnapshot,
  userFacingState,
  isConnected,
  onEditWorkflow,
  onConfirmWorkflow,
}: WingstopScenarioWorkspaceProps) {
  const orderItems = buildWingstopOrderItems(telemetrySnapshot);
  const missingDetails = buildWingstopMissingDetails(telemetrySnapshot);
  const confirmDisabled =
    userFacingState === 'complete' ||
    missingDetails.length > 0 ||
    orderItems.length === 0 ||
    !isConnected;
  const confirmHelperText =
    missingDetails.length > 0
      ? `Add ${missingDetails.join(', ').toLowerCase()} before confirming.`
      : orderItems.length === 0
        ? 'Add at least one item before confirming.'
        : null;

  return (
    <WingstopOrderPanel
      service={telemetrySnapshot?.order.pickup_or_delivery ?? null}
      items={orderItems}
      pickupTime={telemetrySnapshot?.order.pickup_time ?? null}
      drink={telemetrySnapshot?.order.drink ?? null}
      total={telemetrySnapshot?.mock_order?.total ?? null}
      missingDetails={missingDetails}
      isConfirmed={Boolean(telemetrySnapshot?.order.confirmed)}
      onEditOrder={onEditWorkflow}
      onConfirmOrder={onConfirmWorkflow}
      confirmDisabled={confirmDisabled}
      confirmHelperText={confirmHelperText}
      className="border-white/8 bg-[linear-gradient(180deg,rgba(13,20,35,0.82),rgba(8,14,26,0.9))] shadow-none"
    />
  );
}
