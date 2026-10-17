import * as React from 'react';
import { cn } from '@/lib/utils';
import { AlertCircle, Inbox, RefreshCw, Loader2 } from '@/components/ui/icons';
import { Button } from './button';
import { triggerHaptic } from '@/lib/fluid-motion';

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'empty' | 'error' | 'loading';
  icon?: React.ReactNode;
  title?: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    loading?: boolean;
  };
}

function EmptyState({
  variant = 'empty',
  icon,
  title,
  description,
  action,
  className,
  children,
  ...props
}: EmptyStateProps) {
  const defaultIcons = {
    empty: <Inbox className="w-10 h-10 text-muted-foreground/35" />,
    error: <AlertCircle className="w-10 h-10 text-destructive/60" />,
    loading: <Loader2 className="w-8 h-8 text-primary animate-spin" />,
  };

  const defaultTitles = {
    empty: 'No data found',
    error: 'Something went wrong',
    loading: 'Loading...',
  };

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center py-12 px-6 gap-3',
        className
      )}
      {...props}
    >
      {icon || defaultIcons[variant]}
      {variant !== 'loading' && (
        <>
          <h4 className="text-sm font-semibold text-foreground font-heading tracking-tight mt-1">
            {title || defaultTitles[variant]}
          </h4>
          {description && (
            <p className="text-xs text-muted-foreground/80 max-w-xs leading-relaxed font-normal">
              {description}
            </p>
          )}
          {action && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                triggerHaptic('light');
                action.onClick();
              }}
              isLoading={action.loading}
              className="mt-2 touch-manipulation"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              {action.label}
            </Button>
          )}
        </>
      )}
      {children}
    </div>
  );
}

export { EmptyState };
