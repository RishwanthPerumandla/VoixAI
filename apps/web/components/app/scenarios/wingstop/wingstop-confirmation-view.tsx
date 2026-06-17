'use client';

import { useEffect } from 'react';
import { CheckCircleIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

interface WingstopConfirmationViewProps {
  service: string | null;
  items: string[];
  pickupTime: string | null;
  total: string | null;
  orderNumber: string | null;
  onStartNewOrder: () => void;
  onBackToDemo: () => void;
}

export function WingstopConfirmationView({
  service,
  items,
  pickupTime,
  total,
  orderNumber,
  onStartNewOrder,
  onBackToDemo,
}: WingstopConfirmationViewProps) {
  useEffect(() => {
    const timer = window.setTimeout(() => {
      onBackToDemo();
    }, 4000);

    return () => window.clearTimeout(timer);
  }, [onBackToDemo]);

  return (
    <section className="mx-auto flex min-h-svh w-full max-w-4xl items-center px-6 pt-12 pb-12 md:px-10">
      <div
        className="w-full rounded-[32px] border border-emerald-200 bg-[var(--voix-bg-elevated)] p-8 md:p-12"
        style={{ boxShadow: 'var(--voix-card-shadow-hover)' }}
      >
        <div className="mx-auto max-w-2xl text-center">
          <div className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-4 py-1.5 text-xs font-medium tracking-[0.16em] text-emerald-700">
            Wingstop inbound ordering
          </div>
          <CheckCircleIcon size={56} className="mx-auto mt-6 text-emerald-500" weight="fill" />
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-[var(--voix-text-primary)]">
            Order confirmed
          </h1>
          <p className="mt-3 text-lg text-[var(--voix-text-secondary)]">
            Your mock pickup order is ready.
          </p>

          <div className="mt-8 rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-6 text-left">
            <h2 className="text-lg font-semibold text-[var(--voix-text-primary)]">Summary</h2>
            <dl className="mt-4 space-y-3 text-sm text-[var(--voix-text-secondary)]">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--voix-text-muted)]">Service</dt>
                <dd>{service ?? 'Not set'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--voix-text-muted)]">Items</dt>
                <dd className="text-right">
                  {items.length > 0 ? items.join(', ') : 'No items listed'}
                </dd>
              </div>
              {pickupTime && (
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--voix-text-muted)]">Pickup time</dt>
                  <dd>{pickupTime}</dd>
                </div>
              )}
              {total && (
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--voix-text-muted)]">Total</dt>
                  <dd className="font-semibold text-[var(--voix-text-primary)]">{total}</dd>
                </div>
              )}
              {orderNumber && (
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--voix-text-muted)]">Order number</dt>
                  <dd className="font-mono text-[var(--voix-accent-hover)]">{orderNumber}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Button
              type="button"
              onClick={onStartNewOrder}
              className="h-12 rounded-full bg-[color:var(--voix-accent)] px-7 text-white hover:bg-[color:var(--voix-accent-hover)]"
            >
              Start new order
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onBackToDemo}
              className="h-12 rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] px-7 text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
            >
              Back to demo
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
