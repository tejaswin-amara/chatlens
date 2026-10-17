'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCw } from '@/components/ui/icons';

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Root error caught:', error);
  }, [error]);

  const isDev = process.env.NODE_ENV === 'development';
  const displayMessage =
    isDev && error?.message
      ? error.message
      : 'An unexpected application error occurred. Please try refreshing or logging in again.';

  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center p-6 text-center animate-up">
      <div className="max-w-md w-full p-8 rounded-[--radius-xl] bg-surface-1 border border-border shadow-xl">
        <div className="w-14 h-14 rounded-full bg-destructive/10 border border-destructive/20 text-red-400 flex items-center justify-center mx-auto mb-5">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-semibold text-foreground mb-2 font-heading">
          Application Error
        </h2>
        <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
          {displayMessage}
        </p>
        <button
          onClick={() => reset()}
          className="w-full min-h-[44px] py-2.5 px-4 rounded-[--radius-md] bg-primary hover:bg-primary/90 text-primary-foreground font-medium flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none transition-colors active-press"
        >
          <RefreshCw className="w-4 h-4" /> Try again
        </button>
      </div>
    </div>
  );
}
