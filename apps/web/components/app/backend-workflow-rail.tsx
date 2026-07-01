'use client';

import { motion } from 'motion/react';
import type { BackendWorkflowStep } from '@/lib/intelligence/types';
import { cn } from '@/lib/shadcn/utils';

const STATUS_CONFIG = {
  pending: {
    bg: 'bg-slate-100 border-slate-200',
    dot: 'bg-slate-300',
    text: 'text-slate-500',
    line: 'bg-slate-200',
  },
  in_progress: {
    bg: 'bg-indigo-50 border-indigo-200',
    dot: 'bg-indigo-500',
    text: 'text-indigo-700',
    line: 'bg-indigo-200',
  },
  completed: {
    bg: 'bg-emerald-50 border-emerald-200',
    dot: 'bg-emerald-500',
    text: 'text-emerald-700',
    line: 'bg-emerald-200',
  },
  failed: {
    bg: 'bg-rose-50 border-rose-200',
    dot: 'bg-rose-500',
    text: 'text-rose-700',
    line: 'bg-rose-200',
  },
} as const;

interface BackendWorkflowRailProps {
  steps: BackendWorkflowStep[];
  className?: string;
}

export function BackendWorkflowRail({ steps, className }: BackendWorkflowRailProps) {
  return (
    <div
      className={cn('space-y-1', className)}
      role="list"
      aria-label="Backend workflow"
    >
      {steps.map((step, index) => {
        const config = STATUS_CONFIG[step.status];
        const isLast = index === steps.length - 1;

        return (
          <div key={step.id} role="listitem" className="flex items-stretch gap-3">
            <div className="flex flex-col items-center">
              <motion.div
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full border',
                  config.bg
                )}
                animate={
                  step.status === 'in_progress'
                    ? { scale: [1, 1.1, 1] }
                    : undefined
                }
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <span className={cn('h-2 w-2 rounded-full', config.dot)} />
              </motion.div>
              {!isLast && (
                <div className={cn('w-px flex-1', config.line)} />
              )}
            </div>

            <div className={cn('flex-1 pb-3', isLast && 'pb-0')}>
              <p className={cn('text-xs font-medium', config.text)}>{step.label}</p>
              {step.detail && (
                <p className="mt-0.5 text-[10px] text-[var(--voix-text-muted)]">
                  {step.detail}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
