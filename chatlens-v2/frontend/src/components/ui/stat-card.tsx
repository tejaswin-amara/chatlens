import { cn } from '@/lib/utils';
import { type LucideIcon } from '@/components/ui/icons';

interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: string; positive?: boolean };
  accent?: 'primary' | 'success' | 'warning' | 'danger' | 'purple';
}

const accentMap = {
  primary: {
    icon: 'bg-accent text-primary border-primary/15',
    marker: 'bg-primary',
  },
  success: {
    icon: 'bg-success/15 text-success border-success/25',
    marker: 'bg-success',
  },
  warning: {
    icon: 'bg-warning/15 text-warning border-warning/25',
    marker: 'bg-warning',
  },
  danger: {
    icon: 'bg-destructive/15 text-destructive border-destructive/25',
    marker: 'bg-destructive',
  },
  purple: {
    icon: 'bg-primary/15 text-primary border-primary/25',
    marker: 'bg-violet-600',
  },
};

function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  accent = 'primary',
  className,
  ...props
}: StatCardProps) {
  const colors = accentMap[accent];
  return (
    <div
      className={cn(
        'apple-card group flex min-h-[112px] items-center gap-4 rounded-[--radius-lg] p-5 transition-transform active:scale-[0.985]',
        className
      )}
      {...props}
    >
      {Icon && (
        <div
          className={cn(
            'relative flex h-11 w-11 shrink-0 items-center justify-center rounded-[--radius-md] border',
            colors.icon
          )}
        >
          <span
            className={cn(
              'absolute start-0 top-3 h-5 w-0.5 rounded-full',
              colors.marker
            )}
          />
          <Icon className="h-5 w-5" />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="caption-label mb-1.5 truncate text-muted-foreground">
          {label}
        </p>
        <p className="font-heading text-2xl font-bold tracking-tight text-foreground tabular-numbers">
          {value}
        </p>
        {trend && (
          <p
            className={cn(
              'mt-1 text-[11px] font-semibold',
              trend.positive ? 'text-success' : 'text-destructive'
            )}
          >
            {trend.value}
          </p>
        )}
      </div>
    </div>
  );
}

export { StatCard };
