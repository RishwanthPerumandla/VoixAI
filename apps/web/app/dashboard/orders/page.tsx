'use client';

import { useCallback } from 'react';
import { Clock, Package, Receipt } from 'lucide-react';
import {
  EmptyState,
  ErrorState,
  KpiCard,
  Panel,
  SkeletonGrid,
} from '@/components/dashboard/primitives';
import { dashboardApi, usePoll } from '@/lib/dashboard/api';
import { formatClock, formatTimeAgo } from '@/lib/dashboard/format';

function parseMoney(value: string): number {
  return parseFloat(value.replace(/[$,]/g, '')) || 0;
}

export default function OrdersPage() {
  const orders = usePoll(
    useCallback((signal) => dashboardApi.orders(100, signal), []),
    15000
  );

  const data = orders.data;
  const list = data?.orders ?? [];
  const revenue = list.reduce((sum, o) => sum + parseMoney(o.total), 0);
  const avgTicket = list.length > 0 ? revenue / list.length : 0;
  const avgEta = list.length > 0 ? list.reduce((s, o) => s + o.eta_minutes, 0) / list.length : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Orders</h1>
        <p className="mt-1 text-sm text-[var(--voix-text-muted)]">
          Orders the agent placed and persisted through the backend — the source of truth.
        </p>
      </div>

      {orders.error && !data ? (
        <ErrorState message={orders.error} onRetry={orders.refresh} />
      ) : !data ? (
        <SkeletonGrid count={3} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard label="Total orders" value={data.total} hint="Persisted, idempotent records" />
            <KpiCard
              label="Captured revenue"
              value={`$${revenue.toFixed(2)}`}
              accent="var(--voix-success)"
              hint={`$${avgTicket.toFixed(2)} avg ticket`}
            />
            <KpiCard
              label="Avg prep ETA"
              value={`${Math.round(avgEta)} min`}
              accent="var(--voix-warning)"
              hint="Quoted to the customer"
            />
          </div>

          <Panel title="Order feed" subtitle="Newest first · refreshes automatically">
            {list.length === 0 ? (
              <EmptyState
                title="No orders placed yet"
                hint="Complete an order on the live agent, or seed demo data with scripts/seed_dashboard.py"
              />
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {list.map((order) => (
                  <div
                    key={order.order_number}
                    className="rounded-xl border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4 transition hover:border-[var(--voix-border-strong)]"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--voix-accent)]/15">
                          <Package size={15} style={{ color: 'var(--voix-accent)' }} />
                        </span>
                        <div>
                          <p className="font-mono text-sm font-semibold text-[var(--voix-text-primary)]">
                            {order.order_number}
                          </p>
                          <p className="text-xs text-[var(--voix-text-muted)]">
                            {order.customer_name || 'Guest'}
                            {order.order_type ? ` · ${order.order_type}` : ''}
                          </p>
                        </div>
                      </div>
                      <span className="text-base font-semibold text-[var(--voix-success)]">
                        {order.total}
                      </span>
                    </div>

                    {order.item_summary.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {order.item_summary.map((item, i) => (
                          <span
                            key={i}
                            className="rounded-md bg-[var(--voix-bg-primary)] px-2 py-1 text-xs text-[var(--voix-text-secondary)]"
                          >
                            {item}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="mt-3 flex items-center gap-4 text-xs text-[var(--voix-text-muted)]">
                      <span className="flex items-center gap-1">
                        <Receipt size={12} /> {order.item_count} item
                        {order.item_count === 1 ? '' : 's'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> {order.eta_minutes} min ETA
                      </span>
                      <span className="ml-auto" title={formatClock(order.created_at)}>
                        {formatTimeAgo(order.created_at)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
