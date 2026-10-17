'use client';

import { useState } from 'react';
import { useAcademicSession } from '@/hooks/useAcademicSession';
import { useMarks } from '@/hooks/useMarks';
import { PageHeader } from '@/components/ui/page-header';
import { Select } from '@/components/ui/select';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { exportTableToCSV } from '@/lib/utils';
import {
  Search,
  Download,
  ChevronDown,
  ChevronUp,
} from '@/components/ui/icons';
import { Input } from '@/components/ui/input';
import { GpaTrendChart } from './GpaTrendChart';
import { triggerHaptic } from '@/lib/fluid-motion';

function MarksMobileCard({ row }: { row: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(row);
  if (entries.length === 0) return null;

  const [primaryKey, primaryVal] = entries[0];
  const secondaryEntries = entries.slice(1, 3);
  const remainingEntries = entries.slice(3);

  const toggleExpand = () => {
    triggerHaptic('selection');
    setExpanded(!expanded);
  };

  return (
    <div className="p-4 rounded-[--radius-xl] overflow-hidden border border-border apple-card space-y-3 transition-all duration-[--duration-normal] ease-[--ease-spring-default]">
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
              <div className="text-xs font-medium text-foreground truncate tracking-tight mt-0.5">
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

export default function MarksPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const {
    years,
    semesters,
    selectedYear,
    selectedSem,
    handleYearChange,
    handleSemChange,
  } = useAcademicSession();
  const {
    data: rawData,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useMarks(selectedYear, selectedSem);
  const data = (rawData as Record<string, unknown>[]) || [];
  const error = fetchError ? fetchError.message : null;

  const filteredData = data.filter((row) =>
    Object.values(row).some((val) =>
      String(val).toLowerCase().includes(searchQuery.toLowerCase())
    )
  );

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      <PageHeader
        title="Marks & Grades"
        description="Academic performance synced from ERP"
        actions={
          <div className="flex items-center gap-2">
            <Select
              options={years}
              value={selectedYear}
              onChange={(e) => handleYearChange(e.target.value)}
              aria-label="Select Academic Year"
            />
            <Select
              options={semesters}
              value={selectedSem}
              onChange={(e) => handleSemChange(e.target.value)}
              aria-label="Select Semester"
            />
          </div>
        }
      />

      {/* GPA Trend Chart */}
      {!loading && !error && data.length > 0 && <GpaTrendChart data={data} />}

      {/* Search + Export */}
      {!loading && !error && data.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <Input
            placeholder="Search courses..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="w-4 h-4" />}
            className="flex-1"
            aria-label="Search courses"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              triggerHaptic('light');
              exportTableToCSV(filteredData, 'marks');
            }}
            className="min-h-[44px] px-4 touch-manipulation"
          >
            <Download className="w-4 h-4 mr-1.5" /> Export CSV
          </Button>
        </div>
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
        ) : filteredData.length === 0 ? (
          <EmptyState
            title="No marks data"
            description={
              searchQuery
                ? 'Try a different search.'
                : 'Marks will appear once published.'
            }
          />
        ) : (
          <>
            {/* Desktop Table (>=640px) */}
            <div className="hidden sm:block overflow-x-auto custom-scrollbar">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-2/40 sticky top-0 z-10 backdrop-blur-md">
                    {Object.keys(filteredData[0] || {}).map((key, i) => (
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
                  {filteredData.map((row, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-surface-2 transition-colors"
                    >
                      {Object.values(row).map((val: unknown, j) => (
                        <td
                          key={j}
                          className="px-5 py-3.5 text-sm text-foreground tabular-numbers font-medium whitespace-nowrap"
                        >
                          {String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards (<640px) */}
            <div className="block sm:hidden p-4 space-y-3">
              {filteredData.map((row, idx) => (
                <MarksMobileCard key={idx} row={row} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
