import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'circle' | 'text' | 'avatar' | 'card' | 'table-row';
  animation?: 'shimmer' | 'pulse' | 'none';
}

function Skeleton({
  className,
  variant = 'default',
  animation = 'shimmer',
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'bg-surface-2/60 rounded-[--radius-md]',
        animation === 'shimmer' && 'shimmer',
        animation === 'pulse' && 'animate-pulse bg-surface-3',
        variant === 'circle' && 'rounded-full',
        variant === 'text' && 'h-4 rounded-[--radius-sm]',
        variant === 'avatar' && 'w-10 h-10 rounded-full shrink-0',
        variant === 'card' &&
          'h-32 w-full rounded-[--radius-xl] border border-border p-4',
        variant === 'table-row' && 'h-12 w-full rounded-[--radius-md]',
        className
      )}
      {...props}
    />
  );
}

function SkeletonCard({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'p-5 rounded-[--radius-xl] border border-border apple-card space-y-4 animate-pulse',
        className
      )}
      {...props}
    >
      <div className="flex items-center justify-between">
        <Skeleton variant="text" className="w-1/3 h-5" animation="pulse" />
        <Skeleton variant="circle" className="w-6 h-6" animation="pulse" />
      </div>
      <Skeleton variant="text" className="w-2/3 h-4" animation="pulse" />
      <div className="pt-2 flex gap-2">
        <Skeleton
          variant="text"
          className="w-16 h-6 rounded-full"
          animation="pulse"
        />
        <Skeleton
          variant="text"
          className="w-20 h-6 rounded-full"
          animation="pulse"
        />
      </div>
    </div>
  );
}

function SkeletonTable({
  rows = 4,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={cn('w-full space-y-3', className)}>
      <Skeleton
        variant="table-row"
        className="h-10 bg-surface-3/50 rounded-[--radius-lg]"
      />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton
          key={i}
          variant="table-row"
          className="h-12 opacity-80 rounded-[--radius-lg]"
        />
      ))}
    </div>
  );
}

export { Skeleton, SkeletonCard, SkeletonTable };
