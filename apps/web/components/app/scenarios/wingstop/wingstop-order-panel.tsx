'use client';

import { Button } from '@/components/ui/button';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import { cn } from '@/lib/shadcn/utils';

export interface WingstopOrderItem {
  name: string;
  quantity: number;
  flavor?: string | null;
  style?: string | null;
  modifiers?: string[];
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

  if (order.line_items && order.line_items.length > 0) {
    return order.line_items.map((item) => ({
      name: item.name,
      quantity: item.quantity,
      flavor: item.flavors.length > 0 ? item.flavors.join(', ') : null,
      style: item.style,
      modifiers: item.modifiers,
      notes: item.notes,
    }));
  }

  return order.items.map((item) => ({
    name: toTitleCase(item),
    quantity: 1,
    flavor: order.flavor,
    style: order.classic_or_boneless,
  }));
}

function buildItemDetailText(item: WingstopOrderItem, drink: string | null) {
  const visibleModifiers = (item.modifiers ?? []).filter((modifier) => modifier !== drink);
  const detailParts: string[] = [];

  if (visibleModifiers.length > 0) {
    detailParts.push(visibleModifiers.join(', '));
  }
  if (item.notes) {
    detailParts.push(item.notes);
  }

  return detailParts.length > 0 ? detailParts.join(' | ') : null;
}

export function buildWingstopMissingDetails(snapshot: SessionTelemetrySnapshot | null) {
  const order = snapshot?.order;
  if (!order) {
    return ['Service', 'Items', 'Pickup time'];
  }

  const missing: string[] = [];
  if (!order.pickup_or_delivery) missing.push('Service');
  if (order.items.length === 0) missing.push('Items');
  if (order.validation_errors && order.validation_errors.length > 0) {
    return [...new Set([...missing, ...order.validation_errors])];
  }
  if (!order.drink && order.items.some((item) => item.toLowerCase().includes('combo')))
    missing.push('Drink');
  if (
    !order.classic_or_boneless &&
    order.items.some((item) => item.toLowerCase().includes('wings'))
  ) {
    missing.push('Style');
  }
  return missing;
}

export function buildWingstopConfirmationItems(snapshot: SessionTelemetrySnapshot) {
  if (snapshot.order.line_items && snapshot.order.line_items.length > 0) {
    return snapshot.order.line_items.map((item) =>
      item.quantity > 1 ? `${item.quantity}x ${item.name}` : item.name
    );
  }

  return snapshot.order.items.map(toTitleCase);
}

function MissingDetailsList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm font-medium text-emerald-600">
        Everything needed for confirmation is in place.
      </p>
    );
  }

  return (
    <ul className="space-y-2.5 text-sm text-[var(--voix-text-secondary)]">
      {items.map((item) => (
        <li
          key={item}
          className="flex items-center gap-2 rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-3 py-2"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
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
        'rounded-[32px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] p-6',
        className
      )}
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-[var(--voix-text-primary)]">Order summary</h2>
          <p className="mt-1 text-sm text-[var(--voix-text-secondary)]">
            Wingstop inbound ordering
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--voix-text-muted)]">
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
            className="rounded-full border-[var(--voix-border-strong)] bg-[var(--voix-bg-elevated)] text-[var(--voix-text-secondary)] hover:bg-[var(--voix-bg-subtle)]"
          >
            Change order
          </Button>
        )}
      </div>

      <div className="mt-6 space-y-6">
        <section className="rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-[var(--voix-text-muted)]">Service</p>
            <span className="inline-flex rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-3 py-1 text-xs font-medium text-[var(--voix-text-primary)]">
              {service ? service[0].toUpperCase() + service.slice(1) : 'Not selected'}
            </span>
          </div>
          {pickupTime && (
            <p className="mt-3 text-sm text-[var(--voix-text-secondary)]">
              Pickup time: {pickupTime}
            </p>
          )}
          {drink && (
            <p className="mt-2 text-sm text-[var(--voix-text-secondary)]">Drink: {drink}</p>
          )}
        </section>

        <section>
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-[var(--voix-text-muted)]">Items</p>
            {items.length > 0 && (
              <p className="text-xs text-[var(--voix-text-muted)]">
                {items.length} item{items.length === 1 ? '' : 's'}
              </p>
            )}
          </div>
          {items.length === 0 ? (
            <p className="mt-3 rounded-[22px] border border-dashed border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] px-4 py-5 text-sm leading-6 text-[var(--voix-text-muted)]">
              Wingstop items will appear here as you order.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {items.map((item, index) => {
                const detailText = buildItemDetailText(item, drink);

                return (
                  <article
                    key={`${item.name}-${index}`}
                    className="rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-base font-medium text-[var(--voix-text-primary)]">
                          {item.quantity}x {item.name}
                        </p>
                        {detailText && (
                          <p className="mt-2 text-sm text-[var(--voix-text-muted)]">{detailText}</p>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.flavor && (
                        <span className="rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-3 py-1 text-xs text-[var(--voix-text-secondary)]">
                          {item.flavor}
                        </span>
                      )}
                      {item.style && (
                        <span className="rounded-full border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-3 py-1 text-xs text-[var(--voix-text-secondary)]">
                          {item.style}
                        </span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section>
          <p className="text-sm text-[var(--voix-text-muted)]">Still needed</p>
          <div className="mt-3">
            <MissingDetailsList items={missingDetails} />
          </div>
        </section>

        {total && (
          <section className="rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] p-4">
            <p className="text-sm text-[var(--voix-text-muted)]">Total</p>
            <p className="mt-1 text-lg font-semibold text-[var(--voix-text-primary)]">{total}</p>
          </section>
        )}
      </div>

      <div className="mt-8 rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-accent-soft)] p-4">
        <p className="text-sm font-medium text-[var(--voix-text-primary)]">
          {confirmDisabled ? 'Review your order' : 'Ready to confirm'}
        </p>
        <p className="mt-2 text-sm leading-6 text-[var(--voix-text-muted)]">
          {confirmDisabled
            ? confirmHelperText
            : "Please review your order. Say 'confirm' or press Confirm order."}
        </p>
        <Button
          type="button"
          disabled={confirmDisabled}
          onClick={() => void onConfirmOrder()}
          className="mt-4 h-11 w-full rounded-full bg-[color:var(--voix-accent)] text-white hover:bg-[color:var(--voix-accent-hover)] disabled:bg-[var(--voix-bg-subtle)] disabled:text-[var(--voix-text-muted)]"
        >
          Confirm order
        </Button>
      </div>
    </aside>
  );
}
