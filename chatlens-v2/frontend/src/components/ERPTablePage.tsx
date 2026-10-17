'use client';

import { useState, type ReactNode } from 'react';
import { useNativeQuery } from '@/hooks/useNativeQuery';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronDown, ChevronUp } from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';

interface ERPTablePageProps {
  module: string;
  title: string;
  description: string;
  emptyIcon: ReactNode;
  emptyTitle: string;
  emptyDescription: string;
  columnFormatters?: Record<
    string,
    (val: unknown, row: Record<string, unknown>) => ReactNode
  >;
  headerActions?: ReactNode;
}

const fetcher = async (url: unknown) => {
  const response = await fetch(url as string);
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json'))
    throw new Error('Session expired.');
  const json = await response.json();
  if (!json.success) throw new Error(json.error || 'Failed to fetch data');
  return (json.data as Record<string, unknown>[]) || [];
};

function MobileCardItem({
  row,
  columnFormatters,
}: {
  row: Record<string, unknown>;
  columnFormatters?: Record<
    string,
    (val: unknown, row: Record<string, unknown>) => ReactNode
  >;
}) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(row);
  if (!entries.length) return null;
  const [primaryKey, primaryVal] = entries[0];
  const secondaryEntries = entries.slice(1, 3);
  const remainingEntries = entries.slice(3);

  const formatValue = (key: string, val: unknown) => {
    const formatter = columnFormatters?.[key];
    return formatter ? formatter(val, row) : String(val ?? '');
  };

  return (
    <article className="apple-card space-y-3 rounded-[--radius-lg] overflow-hidden p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="caption-label text-muted-foreground">{primaryKey}</p>
          <div className="mt-1 break-words text-sm font-bold tracking-tight text-foreground">
            {formatValue(primaryKey, primaryVal)}
          </div>
        </div>
        {remainingEntries.length > 0 && (
          <button
            type="button"
            onClick={() => {
              triggerHaptic('selection');
              setExpanded((current) => !current);
            }}
            aria-expanded={expanded}
            aria-label={`Toggle details for ${String(primaryVal)}`}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground hover:bg-surface-2 hover:text-foreground"
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        )}
      </div>
      {secondaryEntries.length > 0 && (
        <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
          {secondaryEntries.map(([key, value]) => (
            <div key={key} className="min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                {key}
              </p>
              <div className="mt-1 break-words text-xs font-semibold text-foreground">
                {formatValue(key, value)}
              </div>
            </div>
          ))}
        </div>
      )}
      {expanded && remainingEntries.length > 0 && (
        <div className="space-y-2 border-t border-border pt-3">
          {remainingEntries.map(([key, value]) => (
            <div
              key={key}
              className="flex items-start justify-between gap-4 border-b border-border/70 py-2 text-xs last:border-0"
            >
              <span className="text-muted-foreground">{key}</span>
              <div className="max-w-[60%] break-words text-right font-semibold text-foreground tabular-nums">
                {formatValue(key, value)}
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export default function ERPTablePage({
  module,
  title,
  description,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  columnFormatters,
  headerActions,
}: ERPTablePageProps) {
  const {
    data: rawData,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useNativeQuery(`/api/erp-proxy/${module}`, fetcher);
  const data = rawData || [];
  const error = fetchError ? fetchError.message : null;
  return (
    <div className="flex w-full animate-spring-up flex-col gap-6">
      <PageHeader
        title={title}
        description={description}
        actions={headerActions}
      />
      <section className="apple-card overflow-hidden rounded-[--radius-2xl]">
        {loading ? (
          <div className="space-y-3 p-6">
            {[...Array(4)].map((_, index) => (
              <Skeleton
                key={index}
                className="h-12 w-full rounded-[--radius-md]"
              />
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
            icon={emptyIcon}
            title={emptyTitle}
            description={emptyDescription}
          />
        ) : (
          <>
            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 backdrop-blur-md">
                  <tr className="border-b border-border bg-surface-2/80">
                    <th className="w-8 px-5 py-4 caption-label text-muted-foreground">
                      #
                    </th>
                    {Object.keys(data[0] || {}).map((key) => (
                      <th
                        key={key}
                        scope="col"
                        className="whitespace-nowrap px-4 py-4 text-left caption-label text-muted-foreground"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {data.map((row, index) => (
                    <tr
                      key={index}
                      className="transition-colors hover:bg-surface-2/60"
                    >
                      <td className="px-5 py-4 text-xs font-bold text-muted-foreground">
                        {String(index + 1).padStart(2, '0')}
                      </td>
                      {Object.entries(row).map(([key, value], columnIndex) => {
                        const formatter = columnFormatters?.[key];
                        const content = formatter
                          ? formatter(value, row)
                          : String(value ?? '');
                        return (
                          <td
                            key={columnIndex}
                            className="max-w-[320px] break-words px-4 py-4 text-sm font-medium text-foreground tabular-nums"
                          >
                            {content}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-3 p-4 sm:hidden">
              {data.map((row, index) => (
                <MobileCardItem
                  key={index}
                  row={row}
                  columnFormatters={columnFormatters}
                />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
