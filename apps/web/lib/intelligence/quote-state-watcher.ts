import type { TelemetryPriceQuote } from '@/hooks/useSessionTelemetry';

export interface QuoteSnapshot {
  total: string;
  subtotal: string;
  tax: string;
  etaMinutes: number;
  lineItemCount: number;
  pricingSource: string;
}

export function extractQuoteSnapshot(quote: TelemetryPriceQuote | null | undefined): QuoteSnapshot | null {
  if (!quote) return null;

  return {
    total: quote.total,
    subtotal: quote.subtotal,
    tax: quote.tax,
    etaMinutes: quote.eta_minutes,
    lineItemCount: quote.line_items.length,
    pricingSource: quote.pricing_source,
  };
}

export function hasQuoteChanged(
  prev: QuoteSnapshot | null,
  next: QuoteSnapshot | null
): boolean {
  if (!prev && !next) return false;
  if (!prev || !next) return true;
  return (
    prev.total !== next.total ||
    prev.subtotal !== next.subtotal ||
    prev.tax !== next.tax ||
    prev.etaMinutes !== next.etaMinutes ||
    prev.lineItemCount !== next.lineItemCount
  );
}
