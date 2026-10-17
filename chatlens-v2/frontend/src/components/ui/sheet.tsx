'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { X } from '@/components/ui/icons';
import {
  project,
  rubberband,
  createVelocityTracker,
  triggerHaptic,
} from '@/lib/fluid-motion';

interface SheetContextType {
  open: boolean;
  setOpen: (open: boolean) => void;
  titleId: string;
  descriptionId: string;
}

const SheetContext = React.createContext<SheetContextType | undefined>(
  undefined
);

function useSheetContext() {
  const context = React.useContext(SheetContext);
  if (!context) {
    throw new Error('Sheet components must be used within a Sheet');
  }
  return context;
}

export interface SheetProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: React.ReactNode;
}

export function Sheet({
  open: controlledOpen,
  onOpenChange,
  children,
}: SheetProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(false);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const setOpen = React.useCallback(
    (value: boolean) => {
      if (!isControlled) {
        setUncontrolledOpen(value);
      }
      onOpenChange?.(value);
      if (value) {
        triggerHaptic('light');
      }
    },
    [isControlled, onOpenChange]
  );

  const titleId = React.useId();
  const descriptionId = React.useId();

  return (
    <SheetContext.Provider value={{ open, setOpen, titleId, descriptionId }}>
      {children}
    </SheetContext.Provider>
  );
}

export const SheetTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean }
>(({ className, onClick, children, ...props }, ref) => {
  const { open, setOpen } = useSheetContext();

  return (
    <button
      ref={ref}
      type="button"
      aria-expanded={open}
      onClick={(e) => {
        onClick?.(e);
        setOpen(!open);
      }}
      className={cn(
        'inline-flex items-center justify-center min-w-[44px] min-h-[44px] touch-manipulation active:scale-95 transition-transform duration-[--duration-fast]',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
});
SheetTrigger.displayName = 'SheetTrigger';

export interface SheetContentProps extends React.HTMLAttributes<HTMLDivElement> {
  side?: 'top' | 'bottom' | 'left' | 'right';
}

export const SheetContent = React.forwardRef<HTMLDivElement, SheetContentProps>(
  ({ className, side = 'right', children, ...props }, ref) => {
    const { open, setOpen, titleId, descriptionId } = useSheetContext();
    const sheetRef = React.useRef<HTMLDivElement | null>(null);
    const [dragOffset, setDragOffset] = React.useState(0);
    const [isDragging, setIsDragging] = React.useState(false);
    const velocityTrackerRef = React.useRef(createVelocityTracker());
    const startPosRef = React.useRef(0);

    React.useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && open) {
          setOpen(false);
        }
      };
      if (typeof window !== 'undefined') {
        window.addEventListener('keydown', handleKeyDown);
      }
      return () => {
        if (typeof window !== 'undefined') {
          window.removeEventListener('keydown', handleKeyDown);
        }
      };
    }, [open, setOpen]);

    // Handle gesture dragging on bottom sheets
    const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
      if (side !== 'bottom') return;
      // Only initiate gesture drag if grabbed near top header / handle
      const target = e.target as HTMLElement;
      if (
        target.closest('button') ||
        target.closest('input') ||
        target.closest('select')
      )
        return;

      const rect = sheetRef.current?.getBoundingClientRect();
      if (!rect) return;

      setIsDragging(true);
      startPosRef.current = e.clientY;
      velocityTrackerRef.current.reset();
      velocityTrackerRef.current.addPoint(e.clientX, e.clientY);
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    };

    const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || side !== 'bottom') return;
      velocityTrackerRef.current.addPoint(e.clientX, e.clientY);
      const deltaY = e.clientY - startPosRef.current;

      if (deltaY < 0) {
        // Dragging upward past natural height: apply Apple rubber-band resistance
        const dampened = rubberband(deltaY, 400, 0.45);
        setDragOffset(dampened);
      } else {
        // 1:1 direct finger tracking downward
        setDragOffset(deltaY);
      }
    };

    const handlePointerUp = () => {
      if (!isDragging || side !== 'bottom') return;
      setIsDragging(false);

      const vel = velocityTrackerRef.current.getVelocity();
      const projectedDelta = dragOffset + project(vel.vy, 0.998);

      // Dismiss if pulled down > 120px or flicked downward > 350px/s
      if (dragOffset > 120 || vel.vy > 350 || projectedDelta > 200) {
        triggerHaptic('light');
        setOpen(false);
      }
      setDragOffset(0);
    };

    if (!open) return null;

    const dragStyle = isDragging
      ? {
          transform: `translateY(${Math.max(dragOffset, -40)}px)`,
          transition: 'none',
        }
      : { transform: undefined };

    return (
      <div className="fixed inset-0 z-50 flex">
        {/* Apple Translucent Dimming Scrim */}
        <div
          role="button"
          tabIndex={0}
          aria-label="Close drawer backdrop"
          onClick={() => {
            triggerHaptic('light');
            setOpen(false);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setOpen(false);
            }
          }}
          className="fixed inset-0 bg-slate-950/25 backdrop-blur-sm transition-opacity duration-[--duration-normal] ease-[--ease-spring-default] animate-fade-in"
        />

        {/* Apple Sheet Container */}
        <div
          ref={(node) => {
            sheetRef.current = node;
            if (typeof ref === 'function') ref(node);
            else if (ref)
              (ref as React.MutableRefObject<HTMLDivElement | null>).current =
                node;
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          style={dragStyle}
          className={cn(
            'fixed z-50 flex flex-col gap-4 apple-sheet overflow-hidden p-6 shadow-xl transition-all duration-[--duration-normal] ease-[--ease-spring-sheet]',
            side === 'right' &&
              'inset-y-0 right-0 h-full w-3/4 max-w-sm border-l border-border animate-slide-in-right rounded-l-2xl',
            side === 'left' &&
              'inset-y-0 left-0 h-full w-3/4 max-w-sm border-r border-border animate-slide-in-left rounded-r-2xl',
            side === 'top' &&
              'inset-x-0 top-0 w-full border-b border-border animate-slide-in-top rounded-b-2xl',
            side === 'bottom' &&
              'inset-x-0 bottom-0 w-full border-t border-border animate-sheet-enter rounded-t-[28px] max-h-[92vh]',
            className
          )}
          {...props}
        >
          {side === 'bottom' && (
            <div className="drag-handle" aria-hidden="true" />
          )}
          {children}
          <button
            type="button"
            onClick={() => {
              triggerHaptic('light');
              setOpen(false);
            }}
            aria-label="Close drawer"
            className="absolute right-4 top-4 flex min-w-[44px] min-h-[44px] items-center justify-center rounded-full p-2 text-muted-foreground transition-colors duration-[--duration-fast] hover:bg-surface-2 hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }
);
SheetContent.displayName = 'SheetContent';

export function SheetHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex flex-col space-y-1.5 text-left', className)}
      {...props}
    />
  );
}

export function SheetTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  const { titleId } = useSheetContext();
  return (
    <h2
      id={titleId}
      className={cn(
        'text-lg font-semibold text-foreground tracking-[-0.015em] font-heading',
        className
      )}
      {...props}
    >
      {children}
    </h2>
  );
}

export function SheetDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  const { descriptionId } = useSheetContext();
  return (
    <p
      id={descriptionId}
      className={cn(
        'text-xs text-muted-foreground/90 leading-relaxed font-normal',
        className
      )}
      {...props}
    >
      {children}
    </p>
  );
}

export function SheetFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-auto pt-4 border-t border-border/40',
        className
      )}
      {...props}
    />
  );
}

export function SheetClose({
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { setOpen } = useSheetContext();
  return (
    <button
      type="button"
      onClick={() => {
        triggerHaptic('light');
        setOpen(false);
      }}
      className={cn(
        'inline-flex items-center justify-center min-w-[44px] min-h-[44px] touch-manipulation active:scale-95 transition-transform duration-[--duration-fast]',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
