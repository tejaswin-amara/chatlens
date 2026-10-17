import { registerCourseTitles } from '../course-utils';
import {
  ERP_URL,
  ERP_ENDPOINTS,
  ScraperSession,
  arrayToJar,
  fetchWithJar,
  parseGenericTable,
  checkRateLimitText,
} from './http-jar';

export async function fetchMarksData(
  session: ScraperSession,
  csrfToken: string,
  academicYear: string,
  semesterId: string
) {
  const jar = arrayToJar(session.cookies);
  const params = new URLSearchParams();
  params.append('_csrf', csrfToken);
  params.append('DynamicModel[academicyear]', academicYear);
  params.append('DynamicModel[semester]', semesterId);
  params.append('DynamicModel[semesterid]', semesterId);

  const res = await fetchWithJar(ERP_ENDPOINTS['marks'], jar, {
    method: 'POST',
    body: params,
    signal: AbortSignal.timeout(25000),
    extraHeaders: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'X-Requested-With': 'XMLHttpRequest',
      Origin: ERP_URL,
      Referer: ERP_ENDPOINTS['marks'],
    },
  });

  if (!res.ok) {
    throw new Error(`ERP returned HTTP ${res.status}`);
  }

  const html = await res.text();
  checkRateLimitText(html);
  if (html.includes('id="login-form"')) {
    throw new Error('Session expired or invalid ERP route.');
  }
  const data = parseGenericTable(html);
  registerCourseTitles(data);
  return { success: true, data };
}

export async function fetchEndExamResults(
  session: ScraperSession,
  csrfToken: string,
  academicYear: string,
  semesterId: string
) {
  const jar = arrayToJar(session.cookies);
  const params = new URLSearchParams();
  params.append('_csrf', csrfToken);
  params.append('DynamicModel[academicyear]', academicYear);
  params.append('DynamicModel[semester]', semesterId);
  params.append('DynamicModel[semesterid]', semesterId);

  const res = await fetchWithJar(ERP_ENDPOINTS['end-exam'], jar, {
    method: 'POST',
    body: params,
    signal: AbortSignal.timeout(25000),
    extraHeaders: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'X-Requested-With': 'XMLHttpRequest',
      Origin: ERP_URL,
      Referer: ERP_ENDPOINTS['end-exam'],
    },
  });

  if (!res.ok) {
    throw new Error(`ERP returned HTTP ${res.status}`);
  }

  const html = await res.text();
  checkRateLimitText(html);
  if (html.includes('id="login-form"')) {
    throw new Error('Session expired or invalid ERP route.');
  }
  return { success: true, data: parseGenericTable(html) };
}

export async function fetchCGPAData(
  session: ScraperSession,
  csrfToken?: string,
  academicYear?: string,
  semesterId?: string
) {
  const jar = arrayToJar(session.cookies);
  const params = new URLSearchParams();
  if (csrfToken) params.append('_csrf', csrfToken);
  if (academicYear) params.append('DynamicModel[academicyear]', academicYear);
  if (semesterId) {
    params.append('DynamicModel[semester]', semesterId);
    params.append('DynamicModel[semesterid]', semesterId);
  }

  // Strategy 1: POST
  try {
    const res = await fetchWithJar(ERP_ENDPOINTS['cgpa'], jar, {
      method: 'POST',
      body: params,
      signal: AbortSignal.timeout(25000),
      extraHeaders: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        Origin: ERP_URL,
        Referer: ERP_ENDPOINTS['cgpa'],
      },
    });

    if (res.ok) {
      const html = await res.text();
      if (!html.includes('id="login-form"')) {
        const parsed = parseGenericTable(html);
        if (parsed && parsed.length > 0) {
          return { success: true, data: parsed };
        }
      }
    }
  } catch {}

  await new Promise((resolve) => setTimeout(resolve, 800));

  // Strategy 2: GET
  const getRes = await fetchWithJar(ERP_ENDPOINTS['cgpa'], jar, {
    method: 'GET',
    signal: AbortSignal.timeout(25000),
    extraHeaders: { Origin: ERP_URL, Referer: ERP_URL },
  });
  const html = await getRes.text();
  checkRateLimitText(html);
  if (html.includes('id="login-form"')) {
    throw new Error('Session expired or invalid ERP route.');
  }
  return { success: true, data: parseGenericTable(html) };
}
