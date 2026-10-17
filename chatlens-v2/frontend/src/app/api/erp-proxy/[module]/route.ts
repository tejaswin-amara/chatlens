import { NextRequest, NextResponse } from 'next/server';
import { decodeSession, isDemoModeEnabled, isDemoSession } from '@/lib/session';
import {
  resolveSessionToken,
  checkRateLimitDistributed,
  getClientIP,
} from '@/lib/request-utils';
import {
  fetchAttendanceData,
  fetchTimetableData,
  fetchMarksData,
  fetchEndExamResults,
  fetchProfileData,
  fetchCGPAData,
  fetchFeeData,
  fetchGenericModuleData,
  ERP_ENDPOINTS,
  ScraperSession,
  ERPRateLimitError,
} from '@/lib/scraper';
import {
  DEMO_SESSION,
  DEMO_ATTENDANCE,
  DEMO_TIMETABLE_RAW,
  DEMO_MARKS,
  DEMO_FEE_ITEMS,
  DEMO_PROFILE,
  DEMO_CGPA,
} from '@/lib/fixtures';

export const dynamic = 'force-dynamic';

interface CacheEntry {
  data: unknown;
  timestamp: number;
}
const serverProxyCache = new Map<string, CacheEntry>();
const inFlightProxyRequests = new Map<string, Promise<unknown>>();
const sessionQueues = new Map<string, Promise<unknown>>();
const lastRequestTime = new Map<string, number>();

function throttleForSession<T>(
  sessionKey: string,
  fn: () => Promise<T>
): Promise<T> {
  const prev = sessionQueues.get(sessionKey) || Promise.resolve();
  const next = prev.then(async () => {
    const last = lastRequestTime.get(sessionKey) || 0;
    const elapsed = Date.now() - last;
    const minGap = 400; // Minimum 400ms between outbound ERP calls per session
    if (elapsed < minGap) {
      await new Promise((r) => setTimeout(r, minGap - elapsed));
    }
    lastRequestTime.set(sessionKey, Date.now());
    return fn();
  });
  sessionQueues.set(
    sessionKey,
    next.catch(() => {})
  );
  return next;
}

function apiJson(data: unknown, init?: ResponseInit) {
  const headers = new Headers(init?.headers);
  headers.set('Cache-Control', 'private, no-store, max-age=0');
  headers.set('Vary', 'Cookie');
  return NextResponse.json(data, { ...init, headers });
}

async function handleProxy(
  request: NextRequest,
  { params }: { params: Promise<{ module: string }> }
) {
  try {
    const resolvedParams = await params;
    const moduleName = resolvedParams.module;

    const clientIP = getClientIP(request);
    const rl = await checkRateLimitDistributed(
      `erp-proxy:${clientIP}`,
      1000,
      60_000
    );
    if (!rl.allowed) {
      return apiJson(
        { success: false, error: 'Too many requests. Please slow down.' },
        { status: 429 }
      );
    }

    // Extract parameter payload from POST body or query parameters
    let body: Record<string, string> = {};
    if (request.method === 'POST') {
      try {
        body = await request.json();
      } catch {}
    }

    const searchParams = request.nextUrl.searchParams;

    let session: ScraperSession;
    const sessionValue =
      resolveSessionToken(request) ||
      (typeof body.sessionId === 'string' ? body.sessionId : undefined) ||
      searchParams.get('sessionId') ||
      undefined;
    const demoMode = isDemoModeEnabled();

    if (!sessionValue) {
      if (!demoMode) {
        return apiJson(
          { success: false, error: 'Authentication required.' },
          { status: 401 }
        );
      }
      session = DEMO_SESSION;
    } else {
      try {
        session = await decodeSession(sessionValue);
      } catch {
        if (demoMode && sessionValue.includes('demo')) {
          session = DEMO_SESSION;
        } else {
          return apiJson(
            { success: false, error: 'Session expired. Please sign in again.' },
            { status: 401 }
          );
        }
      }
    }
    const academicYear =
      body.academicYear ||
      searchParams.get('academicYear') ||
      searchParams.get('academicyear') ||
      searchParams.get('academic_year') ||
      undefined;
    const semesterId =
      body.semesterId ||
      searchParams.get('semesterId') ||
      searchParams.get('semester') ||
      searchParams.get('semester_id') ||
      undefined;
    const rawCsrf =
      (typeof body.csrfToken === 'string' ? body.csrfToken : undefined) ||
      (typeof body._csrf === 'string' ? body._csrf : undefined) ||
      searchParams.get('csrfToken') ||
      searchParams.get('_csrf') ||
      searchParams.get('csrf') ||
      request.headers.get('x-csrf-token') ||
      (sessionValue && session ? session.csrfToken : undefined);

    // Validate CSRF token resolution for POST endpoints requiring form submission
    if (
      !rawCsrf &&
      ['attendance', 'timetable', 'marks', 'end-exam'].includes(moduleName)
    ) {
      return apiJson(
        { success: false, error: 'CSRF token missing' },
        { status: 400 }
      );
    }

    const resolvedCsrf = rawCsrf || session.csrfToken;

    // Validate required parameters for academic term modules
    if (
      ['attendance', 'timetable', 'marks', 'end-exam'].includes(moduleName) &&
      (!academicYear || !semesterId)
    ) {
      return apiJson(
        { success: false, error: 'Missing academicYear or semesterId' },
        { status: 400 }
      );
    }

    // Validate module existence
    const knownModules = [
      'attendance',
      'timetable',
      'marks',
      'end-exam',
      'profile',
      'cgpa',
      'fee',
      'hostels',
      'hostel',
      'exam-seating',
      'circulars',
      'library',
    ];
    if (!knownModules.includes(moduleName) && !ERP_ENDPOINTS[moduleName]) {
      return apiJson(
        { success: false, error: `Unknown module: ${moduleName}` },
        { status: 404 }
      );
    }

    if (isDemoSession(session) && !demoMode) {
      return apiJson(
        { success: false, error: 'Authentication required.' },
        { status: 401 }
      );
    }

    if (demoMode && isDemoSession(session)) {
      if (moduleName === 'attendance') {
        return apiJson({
          success: true,
          attendanceData: DEMO_ATTENDANCE.map((item) => ({
            ...item,
            'Academic Year': academicYear || item['Academic Year'],
            Semester: semesterId || item.Semester,
          })),
        });
      }
      if (moduleName === 'timetable') {
        return apiJson({
          success: true,
          data: DEMO_TIMETABLE_RAW,
        });
      }
      if (moduleName === 'marks') {
        return apiJson({
          success: true,
          data: DEMO_MARKS,
        });
      }
      if (moduleName === 'profile') {
        return apiJson({
          success: true,
          data: {
            ...DEMO_PROFILE,
            success: true,
            extendedProfile: JSON.stringify(DEMO_PROFILE.extendedProfile),
          },
        });
      }
      if (moduleName === 'cgpa') {
        return apiJson({
          success: true,
          data: DEMO_CGPA,
        });
      }
      if (moduleName === 'fee') {
        return apiJson({
          success: true,
          data: DEMO_FEE_ITEMS,
        });
      }
      if (moduleName === 'circulars') {
        return apiJson({
          success: true,
          data: [
            {
              'Circular No': 'CIR/2026/08',
              Subject: 'Commencement of Even Semester Registration',
              Date: '2026-08-10',
              Department: 'Academic Affairs',
            },
            {
              'Circular No': 'CIR/2026/07',
              Subject: 'Mid-Semester Examination Schedule Notification',
              Date: '2026-08-01',
              Department: 'Examination Cell',
            },
          ],
        });
      }
      if (moduleName === 'hostels') {
        return apiJson({
          success: true,
          data: [
            {
              'Hostel Name': 'Tulasi Block',
              'Room No': 'T-402',
              'Bed Type': 'Non-AC Attached',
              Status: 'Occupied',
            },
          ],
        });
      }
      if (moduleName === 'library') {
        return apiJson({
          success: true,
          data: [
            {
              'Book Title': 'Introduction to Algorithms (CLRS)',
              'Accession No': 'LIB-94820',
              'Issue Date': '2026-08-01',
              'Due Date': '2026-08-25',
              Fine: '₹0.00',
            },
          ],
        });
      }
      if (moduleName === 'exam-seating') {
        return apiJson({
          success: true,
          data: [
            {
              'Subject Code': '23CS2101R',
              'Subject Name': 'Data Structures & Algorithms',
              'Exam Date': '2026-09-02',
              Session: 'FN (09:30 AM - 12:30 PM)',
              'Room No': 'R-301',
              'Desk No': 'D-14',
            },
          ],
        });
      }
    }

    const executeScraper = async () => {
      let result;
      switch (moduleName) {
        case 'attendance':
          if (!academicYear || !semesterId)
            return apiJson(
              { success: false, error: 'Missing academicYear or semesterId' },
              { status: 400 }
            );
          result = await fetchAttendanceData(
            session,
            resolvedCsrf,
            academicYear,
            semesterId
          );
          break;
        case 'timetable':
          if (!academicYear || !semesterId)
            return apiJson(
              { success: false, error: 'Missing academicYear or semesterId' },
              { status: 400 }
            );
          result = await fetchTimetableData(
            session,
            resolvedCsrf,
            academicYear,
            semesterId
          );
          break;
        case 'marks':
          if (!academicYear || !semesterId)
            return apiJson(
              { success: false, error: 'Missing academicYear or semesterId' },
              { status: 400 }
            );
          result = await fetchMarksData(
            session,
            resolvedCsrf,
            academicYear,
            semesterId
          );
          break;
        case 'end-exam':
          if (!academicYear || !semesterId)
            return apiJson(
              { success: false, error: 'Missing academicYear or semesterId' },
              { status: 400 }
            );
          result = await fetchEndExamResults(
            session,
            resolvedCsrf,
            academicYear,
            semesterId
          );
          break;
        case 'profile':
          result = await fetchProfileData(session);
          break;
        case 'cgpa':
          result = await fetchCGPAData(
            session,
            resolvedCsrf,
            academicYear,
            semesterId
          );
          break;
        case 'fee':
          result = await fetchFeeData(session);
          break;
        default:
          if (ERP_ENDPOINTS[moduleName]) {
            result = await fetchGenericModuleData(
              session,
              ERP_ENDPOINTS[moduleName]
            );
          } else {
            return apiJson(
              { success: false, error: `Unknown module: ${moduleName}` },
              { status: 404 }
            );
          }
          break;
      }
      return result;
    };

    // If demo session, bypass queuing and caching
    if (session === DEMO_SESSION) {
      const demoResult = await executeScraper();
      return demoResult instanceof NextResponse
        ? demoResult
        : apiJson(demoResult);
    }

    const sessionKey = sessionValue ? sessionValue.slice(0, 32) : 'anon';
    const cacheKey = `${sessionKey}:${moduleName}:${academicYear || ''}:${semesterId || ''}`;

    // 1. Check server-side memory cache (45s TTL)
    const cached = serverProxyCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < 45_000) {
      return apiJson(cached.data);
    }

    // 2. Check in-flight deduplication
    const existingPromise = inFlightProxyRequests.get(cacheKey);
    if (existingPromise) {
      const dedupedResult = await existingPromise;
      return dedupedResult instanceof NextResponse
        ? dedupedResult
        : apiJson(dedupedResult);
    }

    // 3. Queue and throttle request per student session (ensuring >= 400ms spacing to ERP)
    const runPromise = throttleForSession(sessionKey, executeScraper);
    inFlightProxyRequests.set(cacheKey, runPromise);

    let result;
    try {
      result = await runPromise;
      if (
        result &&
        typeof result === 'object' &&
        !(result instanceof NextResponse)
      ) {
        serverProxyCache.set(cacheKey, { data: result, timestamp: Date.now() });
      }
    } finally {
      inFlightProxyRequests.delete(cacheKey);
    }

    return result instanceof NextResponse ? result : apiJson(result);
  } catch (error: unknown) {
    let modName = 'unknown';
    try {
      const resolved = await params;
      modName = resolved?.module || 'unknown';
    } catch {}
    console.error(`[erp-proxy/${modName}] Error:`, error);
    const errMessage = error instanceof Error ? error.message : '';

    // 0. ERP Rate Limit Check -> 429 Too Many Requests
    const isRateLimit =
      error instanceof ERPRateLimitError ||
      (error instanceof Error && error.name === 'ERPRateLimitError') ||
      errMessage.includes('Too many requests') ||
      errMessage.includes('Please try again in one minute') ||
      errMessage.includes('HTTP 429') ||
      errMessage.includes('status 429');
    if (isRateLimit) {
      return apiJson(
        {
          success: false,
          error:
            'Too many requests on official college ERP. Please wait 1 minute before retrying.',
          retryAfter: 60,
          isRateLimit: true,
        },
        {
          status: 429,
          headers: {
            'Retry-After': '60',
            'Cache-Control': 'no-store, max-age=0',
          },
        }
      );
    }

    // 1. Session Expiration Check -> 401 Unauthorized
    const isSessionExpired =
      errMessage.includes('Session expired') ||
      errMessage.includes('invalid ERP route');
    if (isSessionExpired) {
      return apiJson(
        { success: false, error: 'Session expired. Please re-login.' },
        { status: 401 }
      );
    }

    // 2. Timeout Check -> 504 Gateway Timeout
    const isTimeout =
      errMessage.includes('ETIMEDOUT') ||
      errMessage.includes('timeout') ||
      errMessage.includes('Timeout') ||
      (error instanceof Error && error.name === 'AbortError') ||
      (typeof DOMException !== 'undefined' &&
        error instanceof DOMException &&
        error.name === 'TimeoutError');

    if (isTimeout) {
      return apiJson(
        {
          success: false,
          error: 'ERP Gateway Timeout',
          details: 'The ERP server took too long to respond. Please try again.',
        },
        { status: 504 }
      );
    }

    // 3. Network / Upstream Proxy Failure -> 502 Bad Gateway
    return apiJson(
      {
        success: false,
        error: 'ERP Bad Gateway',
        details:
          errMessage ||
          'The ERP service could not complete the request. Please try again later.',
      },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ module: string }> }
) {
  return handleProxy(request, props);
}

export async function POST(
  request: NextRequest,
  props: { params: Promise<{ module: string }> }
) {
  return handleProxy(request, props);
}
