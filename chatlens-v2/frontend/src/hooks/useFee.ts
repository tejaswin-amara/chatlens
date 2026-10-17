import { useNativeQuery } from './useNativeQuery';
import { FeeItem, feeResponseSchema } from '@/lib/schemas/fee';
import { calculatePendingFee, parseCurrency } from '@/lib/fee-utils';

export interface UseFeeResult {
  data: FeeItem[] | null;
  totalPending: number;
  totalPaid: number;
  isLoading: boolean;
  error: Error | null;
  mutate: () => Promise<void>;
}

async function feeFetcher(url: unknown) {
  const res = await fetch(url as string);
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    throw new Error('Session expired or invalid server response');
  }
  const json = await res.json();
  const parsed = feeResponseSchema.safeParse(json);
  if (!parsed.success || !json.success) {
    throw new Error(json.error || 'Failed to fetch fee data');
  }
  return (json.data as FeeItem[]) || [];
}

export function useFee(): UseFeeResult {
  const {
    data: rawData,
    error,
    isLoading,
    mutate,
  } = useNativeQuery<FeeItem[]>('/api/erp-proxy/fee', feeFetcher);

  const data = rawData || null;
  const totalPending = data
    ? calculatePendingFee(data as Record<string, unknown>[])
    : 0;

  let totalPaid = 0;
  if (data && Array.isArray(data)) {
    data.forEach((row) => {
      const paidKey = Object.keys(row).find((k) => {
        const norm = k.toLowerCase();
        return (
          (norm.includes('paid') ||
            norm.includes('received') ||
            norm.includes('cleared')) &&
          !norm.includes('status') &&
          !norm.includes('unpaid')
        );
      });
      if (paidKey) {
        totalPaid += parseCurrency(row[paidKey]);
      }
    });
  }

  return {
    data,
    totalPending,
    totalPaid,
    isLoading,
    error: error || null,
    mutate,
  };
}
