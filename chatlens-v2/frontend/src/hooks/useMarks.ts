import { useNativeQuery } from './useNativeQuery';
import { MarksSubject, marksResponseSchema } from '@/lib/schemas/marks';
import { registerCourseTitles } from '@/lib/course-utils';

export interface UseMarksResult {
  data: MarksSubject[] | null;
  isLoading: boolean;
  error: Error | null;
  mutate: () => Promise<void>;
}

async function marksFetcher(key: unknown) {
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
  const parsed = marksResponseSchema.safeParse(json);
  if (!parsed.success || !json.success) {
    throw new Error(json.error || 'Failed to fetch marks data');
  }
  return (json.data as MarksSubject[]) || [];
}

export function useMarks(
  academicYear?: string,
  semesterId?: string
): UseMarksResult {
  const key =
    academicYear && semesterId
      ? (['/api/erp-proxy/marks', academicYear, semesterId] as const)
      : null;
  const { data, error, isLoading, mutate } = useNativeQuery<MarksSubject[]>(
    key,
    marksFetcher
  );

  if (data && Array.isArray(data)) {
    registerCourseTitles(data);
  }

  return {
    data: data || null,
    isLoading,
    error: error || null,
    mutate,
  };
}
