'use client';

import { motion } from 'motion/react';
import { cn } from '@/lib/shadcn/utils';

interface TranscriptMessageProps {
  role: 'assistant' | 'user';
  message: string;
}

export function TranscriptMessage({ role, message }: TranscriptMessageProps) {
  const isAssistant = role === 'assistant';

  return (
    <motion.article
      className={cn('flex', isAssistant ? 'justify-start' : 'justify-end')}
      aria-label={isAssistant ? 'Assistant message' : 'Your message'}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
    >
      <div
        className={cn(
          'max-w-[88%] rounded-[24px] px-4 py-3.5 text-sm leading-6 shadow-[0_12px_32px_rgba(0,0,0,0.16)] md:max-w-[72%]',
          isAssistant
            ? 'border border-white/8 bg-white/[0.055] text-slate-100'
            : 'bg-[linear-gradient(180deg,rgba(240,138,67,0.96),rgba(223,123,54,0.96))] text-[color:var(--voix-accent-foreground)]'
        )}
      >
        <p className={cn('mb-1 text-xs font-medium', isAssistant ? 'text-slate-400' : 'text-black/70')}>
          {isAssistant ? 'Assistant' : 'You'}
        </p>
        <p className="whitespace-pre-wrap">{message}</p>
      </div>
    </motion.article>
  );
}
