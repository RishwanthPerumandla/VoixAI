'use client';

import { memo } from 'react';
import { cn } from '@/lib/shadcn/utils';

interface TranscriptMessageProps {
  role: 'assistant' | 'user';
  message: string;
}

export const TranscriptMessage = memo(function TranscriptMessage({ role, message }: TranscriptMessageProps) {
  const isAssistant = role === 'assistant';

  return (
    <article
      className={cn('flex', isAssistant ? 'justify-start' : 'justify-end')}
      aria-label={isAssistant ? 'Assistant message' : 'Your message'}
    >
      <div
        className={cn(
          'max-w-[88%] rounded-[24px] px-4 py-3.5 text-sm leading-6 md:max-w-[72%]',
          isAssistant
            ? 'border border-[var(--voix-border-subtle)] bg-[var(--voix-bg-subtle)] text-[var(--voix-text-primary)]'
            : 'bg-[color:var(--voix-accent)] text-white'
        )}
      >
        <p
          className={cn(
            'mb-1 text-xs font-medium',
            isAssistant ? 'text-[var(--voix-text-muted)]' : 'text-white/75'
          )}
        >
          {isAssistant ? 'Assistant' : 'You'}
        </p>
        <p className="whitespace-pre-wrap">{message}</p>
      </div>
    </article>
  );
});
