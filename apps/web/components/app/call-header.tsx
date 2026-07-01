'use client';

import { PhoneOffIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LatencyIndicator } from '@/components/app/latency-indicator';
import type { SessionTelemetrySnapshot } from '@/hooks/useSessionTelemetry';
import type { UserFacingSessionState } from '@/components/app/session-status';
import { getSessionStatusContent, getSessionStatusTone } from '@/components/app/session-status';
import { cn } from '@/lib/shadcn/utils';

const TONE_BADGE_CLASSES: Record<string, string> = {
  teal: 'bg-emerald-100 text-emerald-700',
  blue: 'bg-sky-100 text-sky-700',
  violet: 'bg-indigo-100 text-indigo-700',
  amber: 'bg-amber-100 text-amber-700',
  green: 'bg-emerald-100 text-emerald-700',
  rose: 'bg-rose-100 text-rose-700',
  slate: 'bg-slate-100 text-slate-600',
};

interface CallHeaderProps {
  state: UserFacingSessionState;
  telemetrySnapshot: SessionTelemetrySnapshot | null;
  onEndCall: () => void;
  className?: string;
}

export function CallHeader({ state, telemetrySnapshot, onEndCall, className }: CallHeaderProps) {
  const copy = getSessionStatusContent(state);
  const tone = getSessionStatusTone(state);
  const isEnding = state === 'complete' || state === 'error';

  return (
    <header
      className={cn(
        'flex items-center justify-between gap-4 rounded-[24px] border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-elevated)] px-5 py-3.5',
        className
      )}
      style={{ boxShadow: 'var(--voix-card-shadow)' }}
    >
      <div className="flex items-center gap-3.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[color:var(--voix-accent)]">
          <span className="text-sm font-bold text-white">M</span>
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--voix-text-primary)]">Mia</p>
          <p className="text-xs text-[var(--voix-text-muted)]">Wingstop Team</p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <LatencyIndicator telemetrySnapshot={telemetrySnapshot} />

        <span
          aria-live="polite"
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
            TONE_BADGE_CLASSES[tone] ?? TONE_BADGE_CLASSES.slate
          )}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          {copy.label}
        </span>

        {!isEnding && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onEndCall}
            className="h-8 rounded-full border-rose-200 bg-white px-3 text-xs text-rose-600 hover:bg-rose-50"
            aria-label="End call"
          >
            <PhoneOffIcon className="h-3.5 w-3.5" />
            End
          </Button>
        )}
      </div>
    </header>
  );
}
