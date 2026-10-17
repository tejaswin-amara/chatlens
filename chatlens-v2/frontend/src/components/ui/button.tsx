'use client';

import * as React from 'react';
import { Loader2 } from '@/components/ui/icons';
import { cn } from '@/lib/utils';
import { triggerHaptic } from '@/lib/fluid-motion';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | 'default'
    | 'primary'
    | 'secondary'
    | 'ghost'
    | 'outline'
    | 'destructive'
    | 'glass';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  isLoading?: boolean;
  haptic?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'default',
      size = 'default',
      isLoading = false,
      haptic = true,
      disabled,
      children,
      type = 'button',
      onClick,
      onPointerDown,
      ...props
    },
    ref
  ) => {
    const handlePointerDown = (
      event: React.PointerEvent<HTMLButtonElement>
    ) => {
      if (!disabled && !isLoading && haptic) triggerHaptic('light');
      onPointerDown?.(event);
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        data-loading={isLoading || undefined}
        onPointerDown={handlePointerDown}
        onClick={onClick}
        className={cn(
          'inline-flex items-center justify-center gap-2 font-semibold tracking-[-0.01em] touch-manipulation select-none cursor-pointer',
          'transition-[transform,background-color,border-color,box-shadow,color] duration-[--duration-fast] ease-[--ease-spring-default]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          'disabled:opacity-45 disabled:pointer-events-none active:scale-[0.97]',
          variant === 'default' &&
            'bg-primary text-primary-foreground border border-primary/70 shadow-sm shadow-primary/20 hover:bg-primary/90 hover:shadow-md',
          variant === 'primary' &&
            'bg-primary text-primary-foreground border border-primary/70 shadow-sm shadow-primary/20 hover:bg-primary/90 hover:shadow-md',
          variant === 'secondary' &&
            'bg-surface-2 text-foreground border border-border shadow-xs hover:bg-surface-3 hover:border-primary/25',
          variant === 'glass' &&
            'apple-pill text-foreground hover:bg-surface-3',
          variant === 'ghost' &&
            'text-muted-foreground hover:bg-surface-2 hover:text-foreground',
          variant === 'outline' &&
            'bg-surface-1 text-foreground border border-border shadow-xs hover:bg-surface-2 hover:border-primary/30',
          variant === 'destructive' &&
            'bg-destructive text-destructive-foreground border border-destructive/70 shadow-sm hover:bg-destructive/90',
          size === 'default' &&
            'min-h-[44px] rounded-[--radius-md] px-4 py-2.5 text-sm',
          size === 'sm' &&
            'min-h-[44px] rounded-[--radius-sm] px-3.5 py-2 text-xs',
          size === 'lg' &&
            'min-h-[48px] rounded-[--radius-lg] px-6 py-3 text-[0.9375rem]',
          size === 'icon' &&
            'min-h-[44px] min-w-[44px] rounded-[--radius-md] p-2.5',
          className
        )}
        {...props}
      >
        {isLoading && <Loader2 className="h-4 w-4 shrink-0 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button };
