import * as React from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

function PageHeader({
  title,
  description,
  actions,
  className,
  ...props
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-2',
        className
      )}
      {...props}
    >
      <div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] text-foreground font-heading leading-tight">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-muted-foreground/90 mt-1 font-normal leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
}

export { PageHeader };
