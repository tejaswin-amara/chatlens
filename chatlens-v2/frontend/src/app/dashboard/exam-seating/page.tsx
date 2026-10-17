'use client';

import { useState } from 'react';
import { useNativeQuery } from '@/hooks/useNativeQuery';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Armchair,
  ChevronDown,
  ChevronUp,
  GraduationCap,
} from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';

const fetcher = async (url: unknown) => {
  const res = await fetch(url as string);
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) {
    throw new Error('Session expired or server error. Please login again.');
  }
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error || 'Failed to fetch exam seating data');
  }
  return (json.data as Record<string, unknown>[]) || [];
};

function ExamSeatingMobileCard({ row }: { row: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(row);
  if (entries.length === 0) return null;

  let seatNo = '';
  let course = '';

  entries.forEach(([k, v]) => {
    const key = k.toLowerCase();
    if (key.includes('seat')) seatNo = String(v);
    if (
      key.includes('course') ||
      key.includes('subject') ||
      key.includes('code')
    ) {
      if (!course) course = String(v);
    }
  });

  const [, primaryVal] = entries[0];
  const secondaryEntries = entries.slice(1, 3);
  const remainingEntries = entries.slice(3);

  const toggleExpand = () => {
    triggerHaptic('selection');
    setExpanded(!expanded);
  };

  return (
    <div className="p-4 rounded-[--radius-xl] border border-border apple-card space-y-3 transition-all duration-[--duration-normal] ease-[--ease-spring-default]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          {seatNo && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider apple-pill bg-primary/15 text-primary border border-primary/25 tabular-numbers">
              <Armchair className="w-3.5 h-3.5" /> Seat {seatNo}
            </span>
          )}
          <div className="text-sm font-semibold text-foreground truncate mt-0.5 tracking-tight">
            {course || String(primaryVal)}
          </div>
        </div>

        {remainingEntries.length > 0 && (
          <button
            type="button"
            onClick={toggleExpand}
            aria-expanded={expanded}
            aria-label={`Toggle details for ${course || String(primaryVal)}`}
            className="p-2 rounded-full hover:bg-surface-3 text-muted-foreground hover:text-foreground transition-all min-w-[44px] min-h-[44px] flex items-center justify-center -mr-1 -mt-1 touch-manipulation active:scale-90 cursor-pointer"
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {secondaryEntries.length > 0 && (
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border">
          {secondaryEntries.map(([key, val]) => (
            <div key={key} className="min-w-0">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                {key}
              </div>
              <div className="text-xs font-medium text-foreground truncate tracking-tight mt-0.5 tabular-numbers">
                {String(val)}
              </div>
            </div>
          ))}
        </div>
      )}

      {expanded && remainingEntries.length > 0 && (
        <div className="pt-3 border-t border-border space-y-2 animate-spring-scale">
          {remainingEntries.map(([key, val]) => (
            <div
              key={key}
              className="flex justify-between items-center text-xs py-1 border-b border-border/60 last:border-0"
            >
              <span className="text-muted-foreground font-medium">{key}</span>
              <span className="text-foreground font-semibold text-right max-w-[60%] truncate tabular-numbers">
                {String(val)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ExamSeatingPage() {
  const {
    data: rawData,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useNativeQuery('/api/erp-proxy/exam-seating', fetcher);
  const data = rawData || [];
  const error = fetchError ? fetchError.message : null;

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      <PageHeader
        title="Exam Seating"
        description="Live exam seating and hall allocation synced securely from the ERP"
        actions={
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold apple-pill bg-primary/10 text-primary border border-primary/20">
              <GraduationCap className="w-3.5 h-3.5" />
              Exam Seating
            </span>
          </div>
        }
      />

      <div className="rounded-[--radius-2xl] apple-card overflow-hidden shadow-xl border border-border min-h-[300px]">
        {loading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-[--radius-lg]" />
            ))}
          </div>
        ) : error ? (
          <EmptyState
            variant="error"
            title="Failed to sync with ERP"
            description={error}
            action={{ label: 'Retry', onClick: () => mutate() }}
          />
        ) : data.length === 0 ? (
          <EmptyState
            icon={<Armchair className="w-10 h-10 text-muted-foreground/35" />}
            title="No exam seating data"
            description="Exam seating and hall allocation records will appear here."
          />
        ) : (
          <>
            {/* Desktop Table (>=640px) */}
            <div className="hidden sm:block overflow-x-auto custom-scrollbar">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-2/40 sticky top-0 z-10 backdrop-blur-md">
                    {Object.keys(data[0] || {}).map((key, i) => (
                      <th
                        key={i}
                        scope="col"
                        className="px-5 py-3.5 caption-label text-muted-foreground whitespace-nowrap text-left"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.map((row, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-surface-2 transition-colors"
                    >
                      {Object.values(row).map((val: unknown, j) => {
                        const colName = Object.keys(row)[j].toLowerCase();
                        let displayVal: React.ReactNode = String(val);

                        if (colName.includes('seat')) {
                          displayVal = (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider apple-pill bg-primary/15 text-primary border border-primary/25 tabular-numbers">
                              <Armchair className="w-3.5 h-3.5" />
                              {String(val)}
                            </span>
                          );
                        }

                        return (
                          <td
                            key={j}
                            className="px-5 py-3.5 text-sm text-foreground/95 tabular-numbers font-medium whitespace-nowrap"
                          >
                            {displayVal}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards (<640px) */}
            <div className="block sm:hidden p-4 space-y-3">
              {data.map((row, idx) => (
                <ExamSeatingMobileCard key={idx} row={row} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
