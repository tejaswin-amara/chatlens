'use client';

import * as React from 'react';
import { useToast, ToastItem } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
} from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';

export function ToastProvider({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster />
    </>
  );
}

export function Toaster() {
  const { toasts, dismiss } = useToast();

  if (!toasts.length) return null;

  return (
    <div
      role="region"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full p-4 pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastSingle
          key={toast.id}
          toast={toast}
          onDismiss={() => dismiss(toast.id)}
        />
      ))}
    </div>
  );
}

function ToastSingle({
  toast,
  onDismiss,
}: {
  toast: ToastItem;
  onDismiss: () => void;
}) {
  const { variant = 'default', title, description, action } = toast;

  React.useEffect(() => {
    if (variant === 'success') triggerHaptic('success');
    else if (variant === 'destructive') triggerHaptic('error');
    else if (variant === 'warning') triggerHaptic('warning');
    else triggerHaptic('light');
  }, [variant]);

  return (
    <div
      role={variant === 'destructive' ? 'alert' : 'status'}
      aria-live={variant === 'destructive' ? 'assertive' : 'polite'}
      className={cn(
        'pointer-events-auto flex items-start gap-3 p-4 rounded-[--radius-xl] overflow-hidden border shadow-2xl animate-spring-up apple-modal transition-all duration-[--duration-normal] ease-[--ease-spring-default]',
        variant === 'default' &&
          'border-border/80 bg-surface-2/95 text-foreground',
        variant === 'destructive' &&
          'border-destructive/35 bg-destructive/15 text-foreground',
        variant === 'success' &&
          'border-success/35 bg-success/15 text-foreground',
        variant === 'warning' &&
          'border-warning/35 bg-warning/15 text-foreground',
        variant === 'info' && 'border-primary/35 bg-primary/15 text-foreground'
      )}
    >
      <div className="shrink-0 mt-0.5">
        {variant === 'success' && (
          <CheckCircle2 className="w-5 h-5 text-success" />
        )}
        {variant === 'warning' && (
          <AlertTriangle className="w-5 h-5 text-warning" />
        )}
        {variant === 'destructive' && (
          <AlertCircle className="w-5 h-5 text-destructive" />
        )}
        {variant === 'info' && <Info className="w-5 h-5 text-primary" />}
      </div>
      <div className="flex-1 min-w-0">
        {title && (
          <div className="text-sm font-semibold tracking-[-0.012em] font-heading">
            {title}
          </div>
        )}
        {description && (
          <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed font-normal">
            {description}
          </div>
        )}
        {action && <div className="mt-2">{action}</div>}
      </div>
      <button
        onClick={() => {
          triggerHaptic('light');
          onDismiss();
        }}
        aria-label="Close notification"
        className="shrink-0 p-1.5 rounded-full text-muted-foreground hover:text-foreground hover:bg-surface-2 active:scale-90 transition-all min-w-[44px] min-h-[44px] flex items-center justify-center -mr-2 -mt-2 cursor-pointer"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export { ToastSingle as Toast };
