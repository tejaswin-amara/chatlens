import { useNativeQuery } from './useNativeQuery';
import { timetableResponseSchema } from '@/lib/schemas/timetable';
import { parseTimetable, ParsedTimetable } from '@/lib/timetable-parser';

export interface UseTimetableResult {
  data: ParsedTimetable | null;
  isLoading: boolean;
  error: Error | null;
  mutate: () => Promise<void>;
}

async function timetableFetcher(key: unknown) {
  const [url, academicYear, semesterId] = key as [string, string, string];
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ academicYear, semesterId }),
  });
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    throw new Error('Session expired or invalid server response');
  }
  const json = await res.json();
  const parsed = timetableResponseSchema.safeParse(json);
  if (!parsed.success || !json.success) {
    throw new Error(json.error || 'Failed to fetch timetable data');
  }
  const rawRows = (json.data as Record<string, unknown>[]) || [];
  return parseTimetable(rawRows);
}

export function useTimetable(
  academicYear?: string,
  semesterId?: string
): UseTimetableResult {
  const key =
    academicYear && semesterId
      ? (['/api/erp-proxy/timetable', academicYear, semesterId] as const)
      : null;
  const { data, error, isLoading, mutate } = useNativeQuery<ParsedTimetable>(
    key,
    timetableFetcher
  );

  return {
    data: data || null,
    isLoading,
    error: error || null,
    mutate,
  };
}
