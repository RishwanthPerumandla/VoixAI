'use client';

import { memo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import type { TelemetryOrderState, TelemetryPriceQuote } from '@/hooks/useSessionTelemetry';
import { cn } from '@/lib/shadcn/utils';

interface LiveOrderSummaryProps {
  order: TelemetryOrderState | null;
  priceQuote: TelemetryPriceQuote | null;
  className?: string;
}

function OrderItem({
  name,
  quantity,
  flavors,
  modifiers,
}: {
  name: string;
  quantity: number;
  flavors: string[];
  modifiers: string[];
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start justify-between gap-2"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-[var(--voix-text-primary)]">
          {quantity}x {name}
        </p>
        {(flavors.length > 0 || modifiers.length > 0) && (
          <p className="mt-0.5 truncate text-xs text-[var(--voix-text-muted)]">
            {[...flavors, ...modifiers].join(', ')}
          </p>
        )}
      </div>
    </motion.div>
  );
}

export const LiveOrderSummary = memo(function LiveOrderSummary({
  order,
  priceQuote,
  className,
}: LiveOrderSummaryProps) {
  const items = order?.line_items ?? [];
  const hasItems = items.length > 0;

  if (!hasItems && !priceQuote) {
    return (
      <div
        className={cn(
          'rounded-[20px] border border-dashed border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4',
          className
        )}
      >
        <p className="text-center text-xs text-[var(--voix-text-muted)]">
          Your order will appear here
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'rounded-[20px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold tracking-wide text-[var(--voix-text-muted)] uppercase">
          Current Order
        </p>
        {order?.pickup_or_delivery && (
          <span className="rounded-full bg-[color:var(--voix-accent)]/10 px-2 py-0.5 text-[10px] font-medium text-[color:var(--voix-accent)]">
            {order.pickup_or_delivery === 'pickup' ? 'Pickup' : 'Delivery'}
          </span>
        )}
      </div>

      {hasItems && (
        <div className="mt-3 space-y-2.5">
          <AnimatePresence mode="popLayout">
            {items.map((item) => (
              <OrderItem
                key={item.line_id}
                name={item.name}
                quantity={item.quantity}
                flavors={item.flavors}
                modifiers={item.modifiers}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {priceQuote && (
        <div className="mt-3 border-t border-[var(--voix-border-subtle)] pt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--voix-text-muted)]">Subtotal</span>
            <span className="text-[var(--voix-text-secondary)]">${priceQuote.subtotal}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--voix-text-muted)]">Tax</span>
            <span className="text-[var(--voix-text-secondary)]">${priceQuote.tax}</span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-sm font-semibold">
            <span className="text-[var(--voix-text-primary)]">Total</span>
            <span className="text-[color:var(--voix-accent)]">${priceQuote.total}</span>
          </div>
          {priceQuote.eta_minutes > 0 && (
            <p className="mt-1.5 text-center text-[10px] text-[var(--voix-text-muted)]">
              Ready in ~{priceQuote.eta_minutes} min
            </p>
          )}
        </div>
      )}

      {order?.confirmed && (
        <div className="mt-3 rounded-full bg-emerald-50 py-1.5 text-center text-xs font-medium text-emerald-700">
          Order confirmed
        </div>
      )}
    </div>
  );
});
