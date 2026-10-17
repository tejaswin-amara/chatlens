import * as cheerio from 'cheerio';
import { registerCourseTitles } from '../course-utils';
import {
  ERP_URL,
  LOGIN_URL,
  ATTENDANCE_URL,
  COURSE_LIST_URL,
  USER_AGENT,
  ScraperSession,
  CookieJar,
  arrayToJar,
  jarToArray,
  fetchWithJar,
  mergeSetCookies,
  parseGenericTable,
  checkRateLimitText,
} from './http-jar';

export interface CaptchaResponse {
  captchaImage: string;
  session: ScraperSession;
}

export async function getCaptcha(options?: {
  signal?: AbortSignal;
}): Promise<CaptchaResponse> {
  try {
    const jar: CookieJar = {};
    const signal = options?.signal || AbortSignal.timeout(8000);
    const loginRes = await fetchWithJar(LOGIN_URL, jar, { signal });
    const html = await loginRes.text();
    const $ = cheerio.load(html);

    let csrfToken = ($('input[name="_csrf"]').val() as string) || '';
    if (!csrfToken) {
      const csrfMatch = html.match(
        /name=["']_csrf["'][^>]*value=["']([^"']+)["']/i
      );
      if (csrfMatch) csrfToken = csrfMatch[1];
    }
    if (!csrfToken) {
      throw new Error(
        'CSRF Token not found (ERP login page structure may have changed)'
      );
    }

    let captchaSrc = $('#loginFormCaptcha-image').attr('src');
    if (!captchaSrc) {
      const m = html.match(/id="loginFormCaptcha-image"[^>]*src="([^"]+)"/);
      if (m) captchaSrc = m[1].replace(/&amp;/g, '&');
    }
    if (!captchaSrc) {
      throw new Error('Captcha element/source not found');
    }

    const captchaUrl = new URL(captchaSrc, LOGIN_URL).toString();
    const imageRes = await fetchWithJar(captchaUrl, jar, {
      extraHeaders: { Referer: LOGIN_URL },
      signal,
    });

    const imageBuffer = await imageRes.arrayBuffer();
    const captchaBase64 = `data:image/png;base64,${Buffer.from(imageBuffer).toString('base64')}`;

    return {
      captchaImage: captchaBase64,
      session: {
        cookies: jarToArray(jar),
        csrfToken,
        userAgent: USER_AGENT,
      },
    };
  } catch (error) {
    console.error('getCaptcha Error:', error);
    throw error;
  }
}

export interface SemesterOption {
  value: string;
  label: string;
}

export interface LoginResult {
  success: boolean;
  message: string;
  session: ScraperSession;
  csrfToken: string;
  academicYears: SemesterOption[];
  semesters: SemesterOption[];
  deviceId?: string;
  needsCaptchaRetry?: boolean;
}

const DEVICE_COOKIE = 'kl_erp_device_id';

export async function loginAndFetchSemesters(
  username: string,
  pass: string,
  captcha: string,
  session: ScraperSession,
  deviceId?: string
): Promise<LoginResult> {
  const jar = arrayToJar(session.cookies);
  if (deviceId) jar[DEVICE_COOKIE] = deviceId;

  const params = new URLSearchParams();
  params.append('_csrf', session.csrfToken);
  params.append('LoginForm[username]', username);
  params.append('LoginForm[password]', pass);
  params.append('LoginForm[captcha]', captcha.trim().toLowerCase());
  params.append('LoginForm[qr_code]', '');
  params.append('LoginForm[rememberMe]', '1');
  params.append('login-button', '');

  const loginRes = await fetchWithJar(LOGIN_URL, jar, {
    method: 'POST',
    extraHeaders: {
      'Content-Type': 'application/x-www-form-urlencoded',
      Origin: ERP_URL,
      Referer: LOGIN_URL,
    },
    body: params,
  });

  mergeSetCookies(jar, loginRes);

  let loginText = '';
  if (loginRes.status >= 300 && loginRes.status < 400) {
    const location = loginRes.headers.get('location');
    if (location) {
      const dest = new URL(location, LOGIN_URL)
        .toString()
        .replace(/^http:\/\//i, 'https://');
      await fetchWithJar(dest, jar);
    }
  } else {
    loginText = await loginRes.text();
  }

  const attendanceRes = await fetchWithJar(ATTENDANCE_URL, jar, {
    extraHeaders: { Referer: LOGIN_URL },
  });
  const attendanceHtml = await attendanceRes.text();

  const authenticated =
    /name=["'][^"']*academicyear[^"']*["']/i.test(attendanceHtml) ||
    /name=["'][^"']*semesterid[^"']*["']/i.test(attendanceHtml);

  if (!authenticated) {
    const $err = cheerio.load(loginText || attendanceHtml);
    const fieldErrors = $err(
      '.help-block, .help-block-error, .invalid-feedback, .alert-danger'
    )
      .map((_i, el) => $err(el).text().trim())
      .get()
      .filter(Boolean);
    const errText = fieldErrors.join(' | ');
    const $rendered = cheerio.load(loginText || '');
    $rendered('script, style, noscript').remove();
    const renderedText = $rendered.text();
    const signal = (errText + ' ' + renderedText).toLowerCase();
    const crashBody = (loginText || '').toLowerCase();

    const harvested = jar[DEVICE_COOKIE];
    const isTokenCrash =
      /unknown property|useraccesstoken|yiisoft|exception/.test(crashBody);
    if (isTokenCrash && harvested) {
      return {
        success: false,
        needsCaptchaRetry: true,
        deviceId: harvested,
        message:
          'First-time device setup with the ERP — please enter the new captcha once more to finish signing in.',
        session: {
          ...session,
          cookies: jarToArray(jar),
          csrfToken: session.csrfToken,
        },
        csrfToken: session.csrfToken,
        academicYears: [],
        semesters: [],
      };
    }
    if (isTokenCrash) {
      throw new Error(
        "KLU ERP server error during login (a bug on the university's side). Please refresh the captcha and try again."
      );
    }

    if (
      /incorrect username or password|invalid (username|password|login|credentials)|wrong password|password is incorrect|user (does not exist|not found)|account (is )?(locked|disabled|inactive|blocked)/.test(
        signal
      )
    ) {
      throw new Error('Incorrect username or password.');
    }

    if (
      /verification code is incorrect|invalid captcha|incorrect captcha|captcha (is )?(incorrect|invalid|wrong)/.test(
        signal
      )
    ) {
      throw new Error(
        'Captcha incorrect — please re-enter the captcha and try again.'
      );
    }

    throw new Error(
      errText
        ? `Login failed: ${errText}`
        : 'Login failed: the ERP rejected the request. Please refresh the captcha and try again.'
    );
  }

  const csrfTokenMatch = attendanceHtml.match(
    /name=["']_csrf["'][^>]*value=["']([^"']+)["']/i
  );
  const csrfToken = csrfTokenMatch ? csrfTokenMatch[1] : session.csrfToken;

  const $ = cheerio.load(attendanceHtml);

  const academicYears: SemesterOption[] = [];
  let selectedYearValue = '';
  $(
    'select[name="DynamicModel[academicyear]"], select[name="academicyear"], select[name*="[academicyear]"] option'
  )
    .first()
    .parent()
    .find('option')
    .each((_i, el) => {
      const value = $(el).attr('value');
      const label = $(el).text().trim();
      if (value) {
        academicYears.push({ value, label });
        if ($(el).attr('selected')) {
          selectedYearValue = value;
        }
      }
    });

  if (selectedYearValue) {
    const idx = academicYears.findIndex((y) => y.value === selectedYearValue);
    if (idx > -1) {
      const [selectedYear] = academicYears.splice(idx, 1);
      academicYears.unshift(selectedYear);
    }
  }

  const semesters: SemesterOption[] = [];
  let selectedSemValue = '';
  $(
    'select[name="DynamicModel[semesterid]"], select[name="semesterid"], select[name*="[semesterid]"] option'
  )
    .first()
    .parent()
    .find('option')
    .each((_i, el) => {
      const value = $(el).attr('value');
      const label = $(el).text().trim();
      if (value) {
        semesters.push({ value, label });
        if ($(el).attr('selected')) {
          selectedSemValue = value;
        }
      }
    });

  if (selectedSemValue) {
    const idx = semesters.findIndex((s) => s.value === selectedSemValue);
    if (idx > -1) {
      const [selectedSem] = semesters.splice(idx, 1);
      semesters.unshift(selectedSem);
    }
  }

  return {
    success: true,
    message: 'Login Successful',
    session: {
      ...session,
      cookies: jarToArray(jar),
      csrfToken,
    },
    csrfToken,
    academicYears,
    semesters,
    deviceId: jar[DEVICE_COOKIE],
  };
}

export async function fetchAttendanceData(
  session: ScraperSession,
  csrfToken: string,
  academicYear: string,
  semesterId: string
) {
  const jar = arrayToJar(session.cookies);
  const params = new URLSearchParams();
  params.append('_csrf', csrfToken);
  params.append('DynamicModel[academicyear]', academicYear);
  params.append('DynamicModel[semesterid]', semesterId);
  params.append('DynamicModel[semester]', semesterId);

  const res = await fetchWithJar(ATTENDANCE_URL, jar, {
    method: 'POST',
    body: params,
    signal: AbortSignal.timeout(25000),
    extraHeaders: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'X-Requested-With': 'XMLHttpRequest',
      Origin: ERP_URL,
      Referer: ATTENDANCE_URL,
    },
  });

  if (!res.ok) {
    throw new Error(`Attendance fetch failed with status ${res.status}`);
  }

  const text = await res.text();
  checkRateLimitText(text);
  if (
    text.includes('id="login-form"') ||
    text.includes(
      'action="https://newerp.kluniversity.in/index.php?r=site%2Flogin"'
    ) ||
    text.includes('action="/index.php?r=site%2Flogin"')
  ) {
    throw new Error('Session expired. Please login again.');
  }

  // Fetch course titles non-blockingly without throwing if optional route fails
  try {
    const courseListRes = await fetchWithJar(COURSE_LIST_URL, jar, {
      method: 'POST',
      body: params,
      signal: AbortSignal.timeout(10000),
      extraHeaders: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        Origin: ERP_URL,
        Referer: ATTENDANCE_URL,
      },
    });

    if (courseListRes.ok) {
      const courseListHtml = await courseListRes.text();
      const courseTitlesData = parseGenericTable(courseListHtml);
      registerCourseTitles(courseTitlesData);
    }
  } catch {
    // Non-critical course title registration failure
  }

  const attendanceData = parseGenericTable(text);
  registerCourseTitles(attendanceData);
  return {
    success: true,
    data: attendanceData,
  };
}
