import { setCachedValue } from '@/hooks/useNativeQuery';
import { parseTimetable } from '@/lib/timetable-parser';
import { registerCourseTitles } from '@/lib/course-utils';

export interface PrefetchOptions {
  academicYear?: string;
  semesterId?: string;
}

let isPrefetching = false;
let hasPrefetchedThisSession = false;

/** Fetch with a single retry on transient 502/504 errors, but NEVER retry on 429 rate limits */
async function fetchWithRetry(
  url: string,
  init?: RequestInit
): Promise<Response> {
  const res = await fetch(url, init);
  if (res.status === 429) {
    return res;
  }
  if (res.status === 502 || res.status === 504) {
    await new Promise((r) => setTimeout(r, 2000));
    return fetch(url, init);
  }
  return res;
}

/**
 * Prefetches essential academic ERP data gently in the background with inter-request delays
 * to protect the student's official ERP account from rate limiting.
 */
export async function prefetchAllUserData(
  options: PrefetchOptions & { force?: boolean } = {}
): Promise<void> {
  if (typeof window === 'undefined' || isPrefetching) return;
  if (hasPrefetchedThisSession && !options.force) return;

  isPrefetching = true;

  const academicYear =
    options.academicYear || localStorage.getItem('kl_erp_year') || '';

  const semesterId =
    options.semesterId || localStorage.getItem('kl_erp_sem') || '';

  const postHeaders = { 'Content-Type': 'application/json' };

  const taskList: Array<() => Promise<void>> = [];

  // 1. Profile Prefetch (Essential for student identity)
  taskList.push(async () => {
    try {
      const res = await fetchWithRetry('/api/erp-proxy/profile');
      if (res.ok) {
        const json = await res.json();
        if (json?.success && json?.data) {
          setCachedValue('/api/erp-proxy/profile', json.data);
          if (json.data.studentId) {
            try {
              localStorage.setItem('studentId', json.data.studentId);
            } catch {}
          }
          if (json.data.name) {
            try {
              localStorage.setItem('kl_student_name', json.data.name);
            } catch {}
          }
          if (json.data.photoUrl) {
            try {
              localStorage.setItem('kl_student_photo', json.data.photoUrl);
            } catch {}
          }
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new Event('kl_profile_updated'));
          }
        }
      }
    } catch {}
  });

  // 2. Attendance Prefetch
  if (academicYear && semesterId) {
    const payload = JSON.stringify({ academicYear, semesterId });
    const attKey = [
      '/api/erp-proxy/attendance',
      academicYear,
      semesterId,
    ] as const;

    taskList.push(async () => {
      try {
        const res = await fetchWithRetry('/api/erp-proxy/attendance', {
          method: 'POST',
          headers: postHeaders,
          body: payload,
        });
        if (res.ok) {
          const json = await res.json();
          if (json?.success && (json?.attendanceData || json?.data)) {
            const data = json.attendanceData || json.data;
            registerCourseTitles(data);
            setCachedValue(attKey, data);
          }
        }
      } catch {}
    });

    // 3. Timetable Prefetch
    const ttKey = [
      '/api/erp-proxy/timetable',
      academicYear,
      semesterId,
    ] as const;
    taskList.push(async () => {
      try {
        const res = await fetchWithRetry('/api/erp-proxy/timetable', {
          method: 'POST',
          headers: postHeaders,
          body: payload,
        });
        if (res.ok) {
          const json = await res.json();
          if (json?.success && json?.data) {
            const parsed = parseTimetable(json.data);
            setCachedValue(ttKey, parsed);
          }
        }
      } catch {}
    });

    // 4. Marks Prefetch
    const marksKey = [
      '/api/erp-proxy/marks',
      academicYear,
      semesterId,
    ] as const;
    taskList.push(async () => {
      try {
        const res = await fetchWithRetry('/api/erp-proxy/marks', {
          method: 'POST',
          headers: postHeaders,
          body: payload,
        });
        if (res.ok) {
          const json = await res.json();
          if (json?.success && json?.data) {
            registerCourseTitles(json.data);
            setCachedValue(marksKey, json.data);
          }
        }
      } catch {}
    });
  }

  // 5. Fee Prefetch
  taskList.push(async () => {
    try {
      const res = await fetchWithRetry('/api/erp-proxy/fee');
      if (res.ok) {
        const json = await res.json();
        if (json?.success && json?.data) {
          setCachedValue('/api/erp-proxy/fee', json.data);
        }
      }
    } catch {}
  });

  // 6. Generic Modules Prefetch (Circulars, Hostels, Library, Exam Seating)
  const genericModules = ['circulars', 'hostels', 'library', 'exam-seating'];
  for (const mod of genericModules) {
    taskList.push(async () => {
      try {
        const res = await fetchWithRetry(`/api/erp-proxy/${mod}`);
        if (res.ok) {
          const json = await res.json();
          if (json?.success && json?.data) {
            setCachedValue(`/api/erp-proxy/${mod}`, json.data);
          }
        }
      } catch {}
    });
  }

  try {
    // Run sequentially with a gentle 450ms gap between requests
    for (const task of taskList) {
      await task();
      await new Promise((resolve) => setTimeout(resolve, 450));
    }
    hasPrefetchedThisSession = true;
  } finally {
    isPrefetching = false;
  }
}
