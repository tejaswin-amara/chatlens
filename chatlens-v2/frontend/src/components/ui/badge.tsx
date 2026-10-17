import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | 'default'
    | 'secondary'
    | 'success'
    | 'warning'
    | 'danger'
    | 'destructive'
    | 'info'
    | 'outline'
    | 'emerald'
    | 'present'
    | 'absent'
    | 'pending'
    | 'neutral'
    | 'glass';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  pulse?: boolean;
  icon?: React.ReactNode;
}

const variantStyles: Record<string, string> = {
  default: 'bg-surface-2 text-foreground border-border apple-pill',
  secondary: 'bg-secondary text-secondary-foreground border-border apple-pill',
  success: 'bg-success/15 text-success border-success/30 apple-pill',
  warning: 'bg-warning/15 text-warning border-warning/30 apple-pill',
  danger: 'bg-destructive/15 text-error border-destructive/30 apple-pill',
  destructive: 'bg-destructive/15 text-error border-destructive/30 apple-pill',
  info: 'bg-primary/15 text-primary border-primary/30 apple-pill',
  outline: 'bg-transparent text-foreground border-border apple-pill',
  emerald: 'bg-success/15 text-success border-success/30 apple-pill',
  present: 'bg-success/15 text-success border-success/35 apple-pill',
  absent: 'bg-error/10 text-error border-error/25 apple-pill',
  pending: 'bg-warning/15 text-warning border-warning/35 apple-pill',
  neutral: 'bg-surface-2 text-foreground border-border apple-pill',
  glass: 'apple-card text-foreground border-border shadow-xs apple-pill',
};

const sizeStyles: Record<string, string> = {
  sm: 'text-[10px] px-2 py-0.5',
  md: 'text-[11px] px-2.5 py-1',
  lg: 'text-xs px-3 py-1.5',
};

const dotColorStyles: Record<string, string> = {
  success: 'bg-success',
  emerald: 'bg-success',
  present: 'bg-success',
  warning: 'bg-warning',
  pending: 'bg-warning',
  danger: 'bg-destructive',
  destructive: 'bg-destructive',
  absent: 'bg-destructive',
  info: 'bg-primary',
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant = 'default',
      size = 'md',
      dot,
      pulse,
      icon,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1.5 font-semibold tracking-wide rounded-full border transition-all select-none',
          sizeStyles[size],
          variantStyles[variant],
          pulse && 'animate-pulse',
          className
        )}
        {...props}
      >
        {dot && (
          <span
            className={cn(
              'w-1.5 h-1.5 rounded-full shrink-0',
              pulse && 'animate-ping',
              dotColorStyles[variant] || 'bg-muted-foreground'
            )}
          />
        )}
        {icon && <span className="shrink-0 flex items-center">{icon}</span>}
        {children}
      </span>
    );
  }
);
Badge.displayName = 'Badge';
