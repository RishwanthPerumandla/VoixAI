'use client';

import { useState } from 'react';
import { SendHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TextFallbackInputProps {
  onSend: (message: string) => Promise<unknown>;
}

export function TextFallbackInput({ onSend }: TextFallbackInputProps) {
  const [value, setValue] = useState('');
  const [isSending, setIsSending] = useState(false);

  const handleSubmit = async () => {
    const nextValue = value.trim();
    if (!nextValue || isSending) {
      return;
    }

    setIsSending(true);
    try {
      await onSend(nextValue);
      setValue('');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <form
      className="flex items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void handleSubmit();
      }}
    >
      <label className="sr-only" htmlFor="voix-text-fallback">
        Type your order or correction
      </label>
      <textarea
        id="voix-text-fallback"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            void handleSubmit();
          }
        }}
        rows={1}
        placeholder="Type your order or correction..."
        className="min-h-12 flex-1 resize-none rounded-[22px] border border-[var(--voix-border-strong)] bg-[var(--voix-bg-subtle)] px-4 py-3 text-sm text-[var(--voix-text-primary)] placeholder:text-[var(--voix-text-muted)] focus:outline-none focus-visible:border-[color:var(--voix-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--voix-accent)]/30"
      />
      <Button
        type="submit"
        size="icon"
        aria-label="Send text message"
        disabled={isSending || value.trim().length === 0}
        className="h-12 w-12 rounded-full bg-[color:var(--voix-accent)] text-white shadow-sm hover:bg-[color:var(--voix-accent-hover)]"
      >
        <SendHorizontal />
      </Button>
    </form>
  );
}
