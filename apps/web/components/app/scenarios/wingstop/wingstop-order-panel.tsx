'use client';

import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

export interface WingstopOrderItem {
  name: string;
  flavor?: string | null;
  style?: string | null;
  notes?: string | null;
}

interface WingstopOrderPanelProps {
  service: string | null;
  items: WingstopOrderItem[];
  pickupTime: string | null;
  drink: string | null;
  total: string | null;
  missingDetails: string[];
  isConfirmed: boolean;
  onEditOrder: () => Promise<void> | void;
  onConfirmOrder: () => Promise<void> | void;
  confirmDisabled: boolean;
  confirmHelperText: string | null;
  className?: string;
}

function toTitleCase(value: string) {
  return value
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function buildWingstopOrderItems(
  snapshot: SessionTelemetrySnapshot | null
): WingstopOrderItem[] {
  const order = snapshot?.order;
  if (!order || order.items.length === 0) {
    return [];
  }

  return order.items.map((item) => ({
    name: toTitleCase(item),
    flavor: order.flavor,
    style: order.classic_or_boneless,
  }));
}

export function buildWingstopMissingDetails(snapshot: SessionTelemetrySnapshot | null) {
  const order = snapshot?.order;
  if (!order) {
    return ['Service', 'Items', 'Pickup time'];
  }

  const missing: string[] = [];
  if (!order.pickup_or_delivery) missing.push('Service');
  if (order.items.length === 0) missing.push('Items');
  if (!order.drink) missing.push('Drink');
  if (!order.pickup_time) missing.push('Pickup time');
  if (!order.classic_or_boneless && order.items.some((item) => item.toLowerCase().includes('wings'))) {
    missing.push('Style');
  }
  return missing;
}

export function buildWingstopConfirmationItems(snapshot: SessionTelemetrySnapshot) {
  return snapshot.order.items.map(toTitleCase);
}

function MissingDetailsList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-emerald-300">Everything needed for confirmation is in place.</p>
    );
  }

  return (
    <ul className="space-y-2.5 text-sm text-slate-300">
      {items.map((item) => (
        <li
          key={item}
          className="flex items-center gap-2 rounded-full border border-white/6 bg-white/[0.035] px-3 py-2"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-amber-300" />
          {item}
        </li>
      ))}
    </ul>
  );
}

export function WingstopOrderPanel({
  service,
  items,
  pickupTime,
  drink,
  total,
  missingDetails,
  isConfirmed,
  onEditOrder,
  onConfirmOrder,
  confirmDisabled,
  confirmHelperText,
  className,
}: WingstopOrderPanelProps) {
  return (
    <aside
      className={cn(
        'rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,20,35,0.94),rgba(8,14,26,0.98))] p-6 shadow-[0_32px_120px_rgba(0,0,0,0.28)]',
        className
      )}
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-50">Order summary</h2>
          <p className="mt-1 text-sm text-slate-300">Wingstop inbound ordering</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {isConfirmed
              ? 'Review before confirming.'
              : items.length > 0
                ? 'Building the Wingstop workflow live.'
                : 'The active Wingstop order will appear here as you speak.'}
          </p>
        </div>
        {items.length > 0 && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void onEditOrder()}
            className="rounded-full border-white/10 bg-transparent text-slate-100 hover:bg-white/8"
          >
            Change order
          </Button>
        )}
      </div>

      <div className="mt-6 space-y-6">
        <section className="rounded-[24px] border border-white/8 bg-white/[0.035] p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate-400">Service</p>
            <span className="inline-flex rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs font-medium text-slate-100">
              {service ? service[0].toUpperCase() + service.slice(1) : 'Not selected'}
            </span>
          </div>
          {pickupTime && <p className="mt-3 text-sm text-slate-300">Pickup time: {pickupTime}</p>}
          {drink && <p className="mt-2 text-sm text-slate-300">Drink: {drink}</p>}
        </section>

        <section>
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate-400">Items</p>
            {items.length > 0 && (
              <p className="text-xs text-slate-500">
                {items.length} item{items.length === 1 ? '' : 's'}
              </p>
            )}
          </div>
          {items.length === 0 ? (
            <p className="mt-3 rounded-[22px] border border-dashed border-white/10 bg-white/[0.025] px-4 py-5 text-sm leading-6 text-slate-300">
              Wingstop items will appear here as you order.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {items.map((item, index) => (
                <article
                  key={`${item.name}-${index}`}
                  className="rounded-[24px] border border-white/8 bg-white/[0.045] p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-medium text-slate-50">1x {item.name}</p>
                      {item.notes && <p className="mt-2 text-sm text-slate-400">{item.notes}</p>}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {item.flavor && (
                      <span className="rounded-full border border-white/8 bg-white/[0.06] px-3 py-1 text-xs text-slate-200">
                        {item.flavor}
                      </span>
                    )}
                    {item.style && (
                      <span className="rounded-full border border-white/8 bg-white/[0.06] px-3 py-1 text-xs text-slate-200">
                        {item.style}
                      </span>
                    )}
                    {drink && (
                      <span className="rounded-full border border-white/8 bg-white/[0.06] px-3 py-1 text-xs text-slate-200">
                        {drink}
                      </span>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section>
          <p className="text-sm text-slate-400">Still needed</p>
          <div className="mt-3">
            <MissingDetailsList items={missingDetails} />
          </div>
        </section>

        {total && (
          <section className="rounded-[24px] border border-white/8 bg-white/[0.03] p-4">
            <p className="text-sm text-slate-400">Total</p>
            <p className="mt-1 text-lg font-semibold text-slate-50">{total}</p>
          </section>
        )}
      </div>

      <div className="mt-8 rounded-[24px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.03))] p-4">
        <p className="text-sm font-medium text-slate-50">
          {confirmDisabled ? 'Review your order' : 'Ready to confirm'}
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          {confirmDisabled
            ? confirmHelperText
            : "Please review your order. Say 'confirm' or press Confirm order."}
        </p>
        <Button
          type="button"
          disabled={confirmDisabled}
          onClick={() => void onConfirmOrder()}
          className="mt-4 h-11 w-full rounded-full bg-[color:var(--voix-accent)] text-[color:var(--voix-accent-foreground)] hover:bg-[color:var(--voix-accent-hover)] disabled:bg-white/10 disabled:text-slate-500"
        >
          Confirm order
        </Button>
      </div>
    </aside>
  );
}
