'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown } from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[];
  placeholder?: string;
  haptic?: boolean;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    { className, options, placeholder, haptic = true, onChange, ...props },
    ref
  ) => {
    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      if (haptic) {
        triggerHaptic('selection');
      }
      onChange?.(e);
    };

    return (
      <div className="relative">
        <select
          ref={ref}
          onChange={handleChange}
          className={cn(
            'appearance-none w-full min-h-[44px] rounded-[--radius-md] ps-3.5 pe-9 py-2 text-sm tracking-tight font-medium',
            'bg-surface-2/70 backdrop-blur-md border border-border text-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background focus-visible:border-primary/50',
            'hover:border-primary/35 active:scale-[0.985] transition-all duration-[--duration-fast] ease-[--ease-spring-default] cursor-pointer touch-manipulation',
            'disabled:cursor-not-allowed disabled:opacity-40',
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute end-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
      </div>
    );
  }
);
Select.displayName = 'Select';

export { Select };
