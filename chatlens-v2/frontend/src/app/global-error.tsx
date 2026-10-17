'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCw } from '@/components/ui/icons';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Global Error caught:', error);
  }, [error]);

  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="min-h-full flex flex-col font-sans text-foreground bg-background items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-2xl bg-surface-1 border border-border text-center shadow-xl animate-up">
          <div className="w-14 h-14 rounded-full bg-destructive/10 border border-destructive/20 text-red-400 flex items-center justify-center mx-auto mb-5">
            <AlertCircle className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2 font-heading">
            Something went wrong!
          </h2>
          <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
            An unforeseen application error occurred. You can attempt to reload
            the view.
          </p>
          <button
            onClick={() => reset()}
            className="w-full min-h-[44px] py-2.5 px-4 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-medium flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none transition-colors active-press"
          >
            <RefreshCw className="w-4 h-4" /> Try again
          </button>
        </div>
      </body>
    </html>
  );
}
