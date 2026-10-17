import { useNativeQuery } from './useNativeQuery';
import {
  AttendanceSubject,
  attendanceResponseSchema,
} from '@/lib/schemas/attendance';
import { registerCourseTitles } from '@/lib/course-utils';

export interface UseAttendanceResult {
  data: AttendanceSubject[] | null;
  raw: Record<string, unknown>[] | null;
  overallPercentage: number;
  totalAttended: number;
  totalConducted: number;
  isLoading: boolean;
  error: Error | null;
  mutate: () => Promise<void>;
}

async function attendanceFetcher(key: unknown) {
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
  const parsed = attendanceResponseSchema.safeParse(json);
  if (!parsed.success || !json.success) {
    throw new Error(json.error || 'Failed to fetch attendance data');
  }
  return json.attendanceData || json.data || [];
}

export function useAttendance(
  academicYear?: string,
  semesterId?: string
): UseAttendanceResult {
  const key =
    academicYear && semesterId
      ? (['/api/erp-proxy/attendance', academicYear, semesterId] as const)
      : null;
  const {
    data: rawData,
    error,
    isLoading,
    mutate,
  } = useNativeQuery<AttendanceSubject[]>(key, attendanceFetcher);

  const data = rawData || null;

  let totalAttended = 0;
  let totalConducted = 0;

  if (data && Array.isArray(data)) {
    registerCourseTitles(data);
    data.forEach((row) => {
      const condKey = Object.keys(row).find((k) => {
        const kl = k.toLowerCase();
        return (
          kl.includes('conducted') ||
          kl.includes('held') ||
          (kl.includes('total') && !kl.includes('%'))
        );
      });
      const attKey = Object.keys(row).find((k) => {
        const kl = k.toLowerCase();
        return kl.includes('attended') || kl.includes('present');
      });
      if (condKey && attKey) {
        totalConducted += parseFloat(String(row[condKey])) || 0;
        totalAttended += parseFloat(String(row[attKey])) || 0;
      }
    });
  }

  const overallPercentage =
    totalConducted > 0 ? Math.round((totalAttended / totalConducted) * 100) : 0;

  return {
    data,
    raw: (data as Record<string, unknown>[]) || null,
    overallPercentage,
    totalAttended,
    totalConducted,
    isLoading,
    error: error || null,
    mutate,
  };
}
