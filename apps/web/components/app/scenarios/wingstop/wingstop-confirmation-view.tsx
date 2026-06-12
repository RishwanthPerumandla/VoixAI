'use client';

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
  return (
    <section className="mx-auto flex min-h-[calc(100svh-7rem)] w-full max-w-4xl items-center px-6 pb-12 pt-24 md:px-10">
      <div className="w-full rounded-[32px] border border-emerald-400/20 bg-[linear-gradient(180deg,rgba(8,18,26,0.96),rgba(10,24,24,0.96))] p-8 shadow-2xl shadow-black/20 md:p-12">
        <div className="mx-auto max-w-2xl text-center">
          <div className="inline-flex rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-1.5 text-xs font-medium tracking-[0.16em] text-emerald-200">
            Wingstop inbound ordering
          </div>
          <CheckCircleIcon size={56} className="mx-auto mt-6 text-emerald-300" weight="fill" />
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-slate-50">
            Order confirmed
          </h1>
          <p className="mt-3 text-lg text-slate-300">Your mock pickup order is ready.</p>

          <div className="mt-8 rounded-[24px] border border-white/10 bg-white/[0.05] p-6 text-left">
            <h2 className="text-lg font-semibold text-slate-50">Summary</h2>
            <dl className="mt-4 space-y-3 text-sm text-slate-300">
              <div className="flex justify-between gap-4">
                <dt>Service</dt>
                <dd>{service ?? 'Not set'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>Items</dt>
                <dd className="text-right">
                  {items.length > 0 ? items.join(', ') : 'No items listed'}
                </dd>
              </div>
              {pickupTime && (
                <div className="flex justify-between gap-4">
                  <dt>Pickup time</dt>
                  <dd>{pickupTime}</dd>
                </div>
              )}
              {total && (
                <div className="flex justify-between gap-4">
                  <dt>Total</dt>
                  <dd>{total}</dd>
                </div>
              )}
              {orderNumber && (
                <div className="flex justify-between gap-4">
                  <dt>Order number</dt>
                  <dd>{orderNumber}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Button
              type="button"
              onClick={onStartNewOrder}
              className="h-12 rounded-full bg-[color:var(--voix-accent)] px-7 text-[color:var(--voix-accent-foreground)] hover:bg-[color:var(--voix-accent-hover)]"
            >
              Start new order
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onBackToDemo}
              className="h-12 rounded-full border-white/10 bg-transparent px-7 text-slate-100 hover:bg-white/8"
            >
              Back to demo
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
