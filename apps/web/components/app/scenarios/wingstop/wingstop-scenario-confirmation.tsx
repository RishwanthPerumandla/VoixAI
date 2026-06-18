'use client';

import { WingstopConfirmationView } from '@/components/app/scenarios/wingstop/wingstop-confirmation-view';
import { buildWingstopConfirmationItems } from '@/components/app/scenarios/wingstop/wingstop-order-panel';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';

interface WingstopScenarioConfirmationProps {
  telemetrySnapshot: SessionTelemetrySnapshot;
  onStartNewFlow: () => void;
  onBackToDemo: () => void;
}

export function WingstopScenarioConfirmation({
  telemetrySnapshot,
  onStartNewFlow,
  onBackToDemo,
}: WingstopScenarioConfirmationProps) {
  return (
    <WingstopConfirmationView
      service={telemetrySnapshot.order.pickup_or_delivery}
      items={buildWingstopConfirmationItems(telemetrySnapshot)}
      pickupTime={telemetrySnapshot.order.pickup_time}
      total={telemetrySnapshot.mock_order?.total ?? telemetrySnapshot.price_quote?.total ?? null}
      orderNumber={telemetrySnapshot.mock_order?.order_number ?? null}
      onStartNewOrder={onStartNewFlow}
      onBackToDemo={onBackToDemo}
    />
  );
}
