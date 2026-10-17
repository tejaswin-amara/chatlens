import {
  ERP_URL,
  ERP_ENDPOINTS,
  ScraperSession,
  arrayToJar,
  fetchWithJar,
  parseGenericTable,
  checkRateLimitText,
  ERPRateLimitError,
} from './http-jar';

export function isLikelyTimetableData(
  data: Record<string, unknown>[]
): boolean {
  if (!Array.isArray(data) || data.length === 0) return false;

  const dayPattern =
    /^\s*(mon|tue|wed|thu|fri|sat|sun|day\s*order|day\s*\d|do\s*\d|d\d)/i;
  const keys = Object.keys(data[0] || {});
  const hasPeriodHeaders =
    keys.filter(
      (k) => /^\d{1,2}$/.test(k.trim()) || /^period\s*\d{1,2}$/i.test(k.trim())
    ).length >= 3;
  const hasDayValues = data.some((row) =>
    Object.values(row).some((v) => dayPattern.test(String(v || '').trim()))
  );
  if (hasDayValues && (hasPeriodHeaders || keys.length >= 4)) return true;

  const dayHeaders = keys.filter((k) => dayPattern.test(k.trim())).length;
  if (dayHeaders >= 3) return true;

  const timetableKeywords = [
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday',
    'mon',
    'tue',
    'wed',
    'thu',
    'fri',
    'sat',
    'sun',
    'day order',
    'dayorder',
    'do 1',
    'do 2',
    'do 3',
    'do 4',
    'do 5',
    'do 6',
    'do 7',
    'time',
    'slot',
    'period',
    'course',
    'subject',
    'room',
    'faculty',
    'building',
    'ltp',
    'component',
    'section',
    'code',
    'hour',
    'timetable',
  ];

  const timeRegex = /\b(\d{1,2}:\d{2}|am|pm)\b/i;
  const courseCodeRegex = /\d{2}[A-Z]{2,5}\d{3,4}/i;
  const roomNoRegex = /roomno/i;

  let matchCount = 0;
  for (const row of data) {
    if (typeof row !== 'object' || row === null) continue;
    for (const key of Object.keys(row)) {
      const lowerKey = key.toLowerCase();
      if (timetableKeywords.some((kw) => lowerKey.includes(kw))) {
        matchCount++;
      }
      const val = String(row[key] || '').toLowerCase();
      if (
        timetableKeywords.some((kw) => val.includes(kw)) ||
        timeRegex.test(val)
      ) {
        matchCount++;
      }
      if (courseCodeRegex.test(val) || roomNoRegex.test(val)) {
        matchCount += 2;
      }
    }
  }

  const sampleJson = JSON.stringify(data).toLowerCase();
  const isSidebar =
    sampleJson.includes('my profile') ||
    sampleJson.includes('change password') ||
    sampleJson.includes('logout') ||
    sampleJson.includes('academic registration') ||
    sampleJson.includes('fee payments') ||
    sampleJson.includes('hostel management');

  if (isSidebar && matchCount < 8) return false;

  return matchCount >= 4;
}

export async function fetchTimetableData(
  session: ScraperSession,
  csrfToken: string,
  academicYear: string,
  semesterId: string
) {
  const jar = arrayToJar(session.cookies);
  const params = new URLSearchParams();
  params.append('_csrf', csrfToken);
  params.append(
    'UniversityMasterAcademicTimetableView[academicyear]',
    academicYear
  );
  params.append(
    'UniversityMasterAcademicTimetableView[semesterid]',
    semesterId
  );
  params.append('UniversityMasterAcademicTimetableView[semester]', semesterId);
  params.append('DynamicModel[academicyear]', academicYear);
  params.append('DynamicModel[semesterid]', semesterId);
  params.append('DynamicModel[semester]', semesterId);

  const primaryUrl = ERP_ENDPOINTS['timetable'];
  const fallbackUrls = [
    `${ERP_URL}/index.php?r=timetables%2Funiversitymasteracademictimetableview%2Findividualstudenttimetableget`,
    `${ERP_URL}/index.php?r=timetables%2Funiversitymasteracademictimetableview%2Fstudenttimetable`,
    `${ERP_URL}/index.php?r=studentattendance%2Fstudentdailyattendance%2Fstudenttimetable`,
  ];
  const candidateUrls = [primaryUrl, ...fallbackUrls];

  let data: Record<string, unknown>[] = [];
  let fallbackData: Record<string, unknown>[] = [];
  let detectedSessionExpired = false;

  function isSessionExpiredHtml(htmlText: string): boolean {
    if (!htmlText || typeof htmlText !== 'string') return false;
    return (
      htmlText.includes('id="login-form"') ||
      htmlText.includes(
        'action="https://newerp.kluniversity.in/index.php?r=site%2Flogin"'
      ) ||
      htmlText.includes('action="/index.php?r=site%2Flogin"') ||
      (/name="LoginForm\[/.test(htmlText) &&
        !htmlText.includes('UniversityMasterAcademicTimetableView'))
    );
  }

  for (const url of candidateUrls) {
    if (detectedSessionExpired || data.length > 0) break;

    // Strategy 1: POST with form params
    try {
      const res = await fetchWithJar(url, jar, {
        method: 'POST',
        body: params,
        signal: AbortSignal.timeout(25000),
        extraHeaders: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-Requested-With': 'XMLHttpRequest',
          Origin: ERP_URL,
          Referer: url,
        },
      });

      if (res.ok) {
        const html = await res.text();
        checkRateLimitText(html);
        if (isSessionExpiredHtml(html)) {
          detectedSessionExpired = true;
          throw new Error('Session expired or invalid ERP route.');
        }
        const parsed = parseGenericTable(html);
        if (parsed && parsed.length > 0) {
          if (fallbackData.length === 0) fallbackData = parsed;
          if (isLikelyTimetableData(parsed)) {
            data = parsed;
            break;
          }
        }
      }
    } catch (err: unknown) {
      if (
        err instanceof ERPRateLimitError ||
        (err instanceof Error && err.name === 'ERPRateLimitError')
      ) {
        throw err;
      }
      if (err instanceof Error && err.message?.includes('Session expired')) {
        throw err;
      }
      console.error(`POST strategy failed for timetable ${url}:`, err);
    }

    if (detectedSessionExpired || data.length > 0) break;

    await new Promise((resolve) => setTimeout(resolve, 800));

    // Strategy 2: GET with query parameters
    try {
      const getUrl = `${url}&UniversityMasterAcademicTimetableView[academicyear]=${academicYear}&UniversityMasterAcademicTimetableView[semesterid]=${semesterId}&DynamicModel[academicyear]=${academicYear}&DynamicModel[semesterid]=${semesterId}`;
      const getRes = await fetchWithJar(getUrl, jar, {
        method: 'GET',
        signal: AbortSignal.timeout(25000),
        extraHeaders: {
          Origin: ERP_URL,
          Referer: url,
        },
      });

      if (getRes.ok) {
        const getHtml = await getRes.text();
        checkRateLimitText(getHtml);
        if (isSessionExpiredHtml(getHtml)) {
          detectedSessionExpired = true;
          throw new Error('Session expired or invalid ERP route.');
        }
        const parsedGet = parseGenericTable(getHtml);
        if (parsedGet && parsedGet.length > 0) {
          if (fallbackData.length === 0) fallbackData = parsedGet;
          if (isLikelyTimetableData(parsedGet)) {
            data = parsedGet;
            break;
          }
        }
      }
    } catch (err: unknown) {
      if (
        err instanceof ERPRateLimitError ||
        (err instanceof Error && err.name === 'ERPRateLimitError')
      ) {
        throw err;
      }
      if (err instanceof Error && err.message?.includes('Session expired')) {
        throw err;
      }
      console.error(`GET params strategy failed for timetable ${url}:`, err);
    }

    if (detectedSessionExpired || data.length > 0) break;

    await new Promise((resolve) => setTimeout(resolve, 800));

    // Strategy 3: Plain GET (default session view)
    try {
      const plainGetRes = await fetchWithJar(url, jar, {
        method: 'GET',
        signal: AbortSignal.timeout(25000),
        extraHeaders: {
          Origin: ERP_URL,
          Referer: ERP_URL,
        },
      });

      if (plainGetRes.ok) {
        const plainGetHtml = await plainGetRes.text();
        checkRateLimitText(plainGetHtml);
        if (isSessionExpiredHtml(plainGetHtml)) {
          detectedSessionExpired = true;
          throw new Error('Session expired or invalid ERP route.');
        }
        const parsedPlain = parseGenericTable(plainGetHtml);
        if (parsedPlain && parsedPlain.length > 0) {
          if (fallbackData.length === 0) fallbackData = parsedPlain;
          if (isLikelyTimetableData(parsedPlain)) {
            data = parsedPlain;
            break;
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.message?.includes('Session expired')) {
        throw err;
      }
      console.error(`Plain GET strategy failed for timetable ${url}:`, err);
    }
  }

  if (detectedSessionExpired) {
    throw new Error('Session expired or invalid ERP route.');
  }

  const finalData = data.length > 0 ? data : fallbackData;
  return { success: true, data: finalData };
}
