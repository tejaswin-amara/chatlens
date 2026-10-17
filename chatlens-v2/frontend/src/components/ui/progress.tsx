import * as React from 'react';
import { cn } from '@/lib/utils';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  variant?: 'linear' | 'circular';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  colorByValue?: boolean;
}

function getProgressColor(value: number): string {
  if (value >= 85) return 'text-success';
  if (value >= 75) return 'text-warning';
  return 'text-destructive';
}

function getProgressBg(value: number): string {
  if (value >= 85) return 'bg-success shadow-[0_0_12px_rgba(48,209,88,0.35)]';
  if (value >= 75) return 'bg-warning shadow-[0_0_12px_rgba(255,214,10,0.35)]';
  return 'bg-destructive shadow-[0_0_12px_rgba(255,69,58,0.35)]';
}

function Progress({
  value,
  max = 100,
  variant = 'linear',
  size = 'md',
  showLabel = false,
  colorByValue = false,
  className,
  ...props
}: ProgressProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);

  if (variant === 'circular') {
    const dimensions = { sm: 44, md: 60, lg: 76 };
    const strokes = { sm: 4, md: 5.5, lg: 7 };
    const fonts = { sm: 'text-[11px]', md: 'text-xs', lg: 'text-sm' };

    const dim = dimensions[size];
    const stroke = strokes[size];
    const r = (dim - stroke) / 2;
    const circ = 2 * Math.PI * r;
    const offset = circ - (pct / 100) * circ;

    return (
      <div
        className={cn(
          'relative inline-flex items-center justify-center select-none',
          className
        )}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        {...props}
      >
        <svg width={dim} height={dim} className="-rotate-90">
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            className="text-surface-3/80"
          />
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={cn(
              'transition-all duration-[600ms] ease-[--ease-spring-default]',
              colorByValue ? getProgressColor(pct) : 'text-primary'
            )}
          />
        </svg>
        {showLabel && (
          <span
            className={cn(
              'absolute font-bold tabular-numbers font-heading tracking-tight',
              fonts[size],
              colorByValue ? getProgressColor(pct) : 'text-foreground'
            )}
          >
            {Math.round(pct)}%
          </span>
        )}
      </div>
    );
  }

  // Linear
  const heights = { sm: 'h-1.5', md: 'h-2', lg: 'h-2.5' };

  return (
    <div
      className={cn('w-full flex items-center gap-2.5 select-none', className)}
      {...props}
    >
      <div
        className={cn(
          'flex-1 rounded-full bg-surface-3/80 overflow-hidden shadow-inner border border-border/60',
          heights[size]
        )}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-[600ms] ease-[--ease-spring-default]',
            colorByValue
              ? getProgressBg(pct)
              : 'bg-primary shadow-[0_0_12px_rgba(99,102,241,0.35)]'
          )}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
      {showLabel && (
        <span
          className={cn(
            'text-xs font-semibold tabular-numbers tracking-tight shrink-0',
            colorByValue ? getProgressColor(pct) : 'text-muted-foreground'
          )}
        >
          {Math.round(pct)}%
        </span>
      )}
    </div>
  );
}

export { Progress };
