'use client';

import { useEffect, useState } from 'react';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';

// Same API the live voice client and dashboard use.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';

export interface RoomOrder {
  order_number: string;
  total: string;
  item_summary: string[];
  customer_name: string;
  order_type: string | null;
  created_at: number;
}

/**
 * Belt-and-suspenders for the order-placed confirmation.
 *
 * The order is persisted to the backend the moment it's placed (over HTTP,
 * independent of the LiveKit data channel). So even if the `mock_order`
 * telemetry snapshot never arrives, we can still detect completion by polling
 * the backend for an order on this room — and drive the confirmation/redirect
 * from that. Polling stops as soon as an order is found.
 */
export function useRoomOrder(roomName: string | undefined, enabled: boolean): RoomOrder | null {
  const [order, setOrder] = useState<RoomOrder | null>(null);

  useEffect(() => {
    if (!enabled || !roomName || order) {
      return;
    }

    let active = true;
    const controller = new AbortController();

    const poll = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/orders?room_name=${encodeURIComponent(roomName)}&limit=1`,
          { signal: controller.signal, cache: 'no-store', headers: { Accept: 'application/json' } }
        );
        if (!res.ok) return;
        const data = (await res.json()) as { orders?: RoomOrder[] };
        if (active && data.orders && data.orders.length > 0) {
          setOrder(data.orders[0]);
        }
      } catch {
        // best-effort — a failed poll just retries on the next tick
      }
    };

    void poll();
    const id = window.setInterval(poll, 2500);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(id);
    };
  }, [roomName, enabled, order]);

  return order;
}

/**
 * Build a confirmation-ready telemetry snapshot from a backend order, so the
 * existing scenario confirmation view can render without any live telemetry.
 * Reuses live snapshot fields (line items, pickup time) when available.
 */
export function synthesizeConfirmationSnapshot(
  order: RoomOrder,
  base: SessionTelemetrySnapshot | null
): SessionTelemetrySnapshot {
  return {
    type: 'session_snapshot',
    reason: 'api_order_fallback',
    timestamp: Date.now() / 1000,
    target_e2e_latency_ms: base?.target_e2e_latency_ms ?? 800,
    acceptable_e2e_latency_ms: base?.acceptable_e2e_latency_ms ?? 1500,
    turn_count: base?.turn_count ?? 0,
    order: {
      ...base?.order,
      pickup_or_delivery: order.order_type ?? base?.order?.pickup_or_delivery ?? null,
      items: order.item_summary,
      line_items: base?.order?.line_items,
      customer_name: order.customer_name || base?.order?.customer_name || null,
      flavor: base?.order?.flavor ?? null,
      classic_or_boneless: base?.order?.classic_or_boneless ?? null,
      drink: base?.order?.drink ?? null,
      pickup_time: base?.order?.pickup_time ?? null,
      confirmed: true,
    },
    price_quote: base?.price_quote ?? null,
    mock_order: { order_number: order.order_number, total: order.total, summary: '' },
    runtime_profile: base?.runtime_profile ?? null,
    user_turn_metrics: base?.user_turn_metrics ?? null,
    assistant_turn_metrics: base?.assistant_turn_metrics ?? null,
  };
}
