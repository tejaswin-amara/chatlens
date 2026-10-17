'use client';

import { Loader2 } from '@/components/ui/icons';

interface AIToolExecutionIndicatorProps {
  toolName?: string;
  status: 'thinking' | 'executing_tool' | 'error';
}

export function AIToolExecutionIndicator({
  toolName,
  status,
}: AIToolExecutionIndicatorProps) {
  if (status === 'error') return null;

  const displayMessage =
    status === 'executing_tool' && toolName
      ? `Querying ERP via ${toolName}...`
      : 'Analyzing request & executing workflow...';

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/15 border border-primary/25 text-indigo-300 text-xs font-semibold apple-pill backdrop-blur-md animate-pulse my-2 max-w-fit shadow-xs">
      <Loader2 className="w-3.5 h-3.5 animate-spin text-primary shrink-0" />
      <span className="tracking-tight">{displayMessage}</span>
    </div>
  );
}
