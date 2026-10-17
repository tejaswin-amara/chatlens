'use client';

import { useState } from 'react';
import { useFee } from '@/hooks/useFee';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { StatCard } from '@/components/ui/stat-card';
import {
  CheckCircle,
  Clock,
  ChevronDown,
  ChevronUp,
} from '@/components/ui/icons';
import { findStatusKey, isRowUnpaid } from '@/lib/fee-utils';
import { FeeBreakdownChart } from './FeeBreakdownChart';
import { triggerHaptic } from '@/lib/fluid-motion';

function FeeMobileCard({ row }: { row: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(row);
  if (entries.length === 0) return null;

  const unpaid = isRowUnpaid(row);
  const [primaryKey, primaryVal] = entries[0];
  const secondaryEntries = entries.slice(1, 3);
  const remainingEntries = entries.slice(3);

  const toggleExpand = () => {
    triggerHaptic('selection');
    setExpanded(!expanded);
  };

  return (
    <div
      className={`p-4 rounded-[--radius-xl] overflow-hidden border ${unpaid ? 'border-destructive/35 bg-destructive/10' : 'border-border apple-card'} space-y-3 transition-all duration-[--duration-normal] ease-[--ease-spring-default]`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="caption-label text-muted-foreground/80">
            {primaryKey}
          </div>
          <div className="text-sm font-semibold text-foreground truncate mt-0.5 tracking-tight">
            {String(primaryVal)}
          </div>
        </div>

        {remainingEntries.length > 0 && (
          <button
            type="button"
            onClick={toggleExpand}
            aria-expanded={expanded}
            aria-label={`Toggle details for ${String(primaryVal)}`}
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

export default function FeePage() {
  const {
    data: rawData,
    totalPending,
    totalPaid,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useFee();
  const data = (rawData as Record<string, unknown>[]) || [];
  const error = fetchError ? fetchError.message : null;

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      <PageHeader
        title="Fee Details"
        description="Payment records synced from ERP"
      />
      <p className="text-xs text-muted-foreground -mt-3">
        Note: Fee data shown is cumulative across all semesters.
      </p>

      {!loading && !error && data.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <StatCard
              label="Total Pending"
              value={`₹${totalPending.toLocaleString()}`}
              icon={Clock}
              accent="danger"
            />
            <StatCard
              label="Total Paid"
              value={`₹${totalPaid.toLocaleString()}`}
              icon={CheckCircle}
              accent="success"
            />
          </div>
          <FeeBreakdownChart
            data={data}
            totalFee={totalPaid + totalPending}
            pendingFee={totalPending}
          />
        </>
      )}

      <div className="rounded-[--radius-2xl] apple-card overflow-hidden shadow-xl border border-border">
        {loading ? (
          <div className="p-6 space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-[--radius-lg]" />
            ))}
          </div>
        ) : error ? (
          <EmptyState
            variant="error"
            description={error}
            action={{ label: 'Retry', onClick: () => mutate() }}
          />
        ) : data.length === 0 ? (
          <EmptyState
            title="No fee records"
            description="Fee data will appear here once available."
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
                  {data.map((row, idx) => {
                    const unpaid = isRowUnpaid(row);
                    return (
                      <tr
                        key={idx}
                        className={`hover:bg-surface-2 transition-colors ${unpaid ? 'bg-destructive/5' : ''}`}
                      >
                        {Object.entries(row).map(([key, val], j) => {
                          const statusKey = findStatusKey(row);
                          const isStatus = statusKey === key;
                          return (
                            <td
                              key={j}
                              className="px-5 py-3.5 text-sm text-foreground tabular-numbers font-medium whitespace-nowrap"
                            >
                              {isStatus ? (
                                <span
                                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold apple-pill ${
                                    unpaid
                                      ? 'bg-destructive/15 text-destructive border border-destructive/25'
                                      : 'bg-success/15 text-success border border-success/25'
                                  }`}
                                >
                                  {unpaid ? (
                                    <Clock className="w-3 h-3" />
                                  ) : (
                                    <CheckCircle className="w-3 h-3" />
                                  )}
                                  {String(val)}
                                </span>
                              ) : (
                                String(val)
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards (<640px) */}
            <div className="block sm:hidden p-4 space-y-3">
              {data.map((row, idx) => (
                <FeeMobileCard key={idx} row={row} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
