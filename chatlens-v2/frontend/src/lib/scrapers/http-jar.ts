import * as cheerio from 'cheerio';
import type { Element } from 'domhandler';

export const ERP_URL = 'https://newerp.kluniversity.in';
export const LOGIN_URL = `${ERP_URL}/index.php?r=site%2Flogin`;
export const ATTENDANCE_URL = `${ERP_URL}/index.php?r=studentattendance%2Fstudentdailyattendance%2Fsearchgetinput`;
export const COURSE_LIST_URL = `${ERP_URL}/index.php?r=studentattendance%2Fstudentdailyattendance%2Fcourselist`;

// ponytail: Object.create(null) prevents prototype-pollution via route params (e.g. /constructor)
export const ERP_ENDPOINTS: Record<string, string> = Object.assign(Object.create(null), {
  marks: `${ERP_URL}/index.php?r=studentinfo%2Fstudentendexamresult%2Fgetstudentinternalmarks`,
  timetable: `${ERP_URL}/index.php?r=timetables%2Funiversitymasteracademictimetableview%2Findexstudentindisearch`,
  fee: `${ERP_URL}/index.php?r=feepayments%2Fstudentfeeorderdetailsinfo%2Fmy_fee_orders`,
  profile: `${ERP_URL}/index.php?r=studentinfo%2Fstudentprofileinfo%2Fviewprofileindi`,
  cgpa: `${ERP_URL}/index.php?r=studentinfo%2Fstudentendexamresult%2Fsearchgetmycgpa`,
  'end-exam': `${ERP_URL}/index.php?r=studentinfo%2Fstudentendexamresult%2Fsemendresult`,
  'exam-seating': `${ERP_URL}/index.php?r=examsection%2Fexam-invigilator-student-room-allotment-info%2Fstud_my_seating_plan`,
  circulars: `${ERP_URL}/index.php?r=registraroffice%2Fregistrarofficecircularsvisibilitylistinfo%2Ftab_index_personal`,
  hostels: `${ERP_URL}/index.php?r=hostel%2Fhosteloccupancyinfo%2Fhostel-room-info`,
  hostel: `${ERP_URL}/index.php?r=hostel%2Fhosteloccupancyinfo%2Fhostel-room-info`,
  library: `${ERP_URL}/index.php?r=library%2Fborrowers%2Fmy_circulation_history`,
});

export const USER_AGENT =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

export interface ScraperSession {
  cookies: { name: string; value: string }[];
  csrfToken: string;
  userAgent?: string;
}

export type CookieJar = Record<string, string>;

export function getSetCookies(res: Response): string[] {
  return (
    res.headers.getSetCookie?.() ??
    res.headers.get('set-cookie')?.split(/,(?=\s*[^=;,]+=)/) ??
    []
  );
}

export function mergeSetCookies(jar: CookieJar, res: Response): void {
  for (const sc of getSetCookies(res)) {
    const firstSemi = sc.indexOf(';');
    const pair = (firstSemi > -1 ? sc.slice(0, firstSemi) : sc).trim();
    const eq = pair.indexOf('=');
    if (eq > -1) {
      const name = pair.slice(0, eq).trim();
      const value = pair.slice(eq + 1).trim();
      if (name) jar[name] = value;
    }
  }
}

export function cookieHeader(jar: CookieJar): string {
  return Object.entries(jar)
    .map(([k, v]) => `${k}=${v}`)
    .join('; ');
}

export function jarToArray(jar: CookieJar): { name: string; value: string }[] {
  return Object.entries(jar).map(([name, value]) => ({ name, value }));
}

export function arrayToJar(
  cookies?: { name: string; value: string }[] | null
): CookieJar {
  const jar: CookieJar = {};
  for (const c of cookies || []) {
    if (c && c.name) jar[c.name] = c.value;
  }
  return jar;
}

export class ERPRateLimitError extends Error {
  readonly retryAfter: number;
  constructor(
    message = 'Too many requests. Please try again in one minute.',
    retryAfter = 60
  ) {
    super(message);
    this.name = 'ERPRateLimitError';
    this.retryAfter = retryAfter;
  }
}

export function checkRateLimitText(html: string): void {
  if (
    html.includes('Too many requests') ||
    html.includes('Please try again in one minute') ||
    html.includes('try again in 1 minute')
  ) {
    throw new ERPRateLimitError();
  }
}

export async function fetchWithJar(
  url: string,
  jar: CookieJar,
  init: RequestInit & { extraHeaders?: Record<string, string> } = {},
  maxRedirects = 5
): Promise<Response> {
  const initialUrl = new URL(url);
  if (initialUrl.origin !== ERP_URL) {
    throw new Error('ERP request URL is outside the configured origin');
  }

  let currentUrl = initialUrl.toString();
  let method = (init.method || 'GET').toUpperCase();
  let body = init.body;

  for (let i = 0; i <= maxRedirects; i++) {
    const headers: Record<string, string> = {
      'User-Agent': USER_AGENT,
      Connection: 'keep-alive',
      ...(init.extraHeaders || {}),
    };
    const cookies = cookieHeader(jar);
    if (cookies) headers['Cookie'] = cookies;
    if (body && method !== 'GET' && method !== 'HEAD') {
      headers['Content-Type'] =
        headers['Content-Type'] || 'application/x-www-form-urlencoded';
    }

    const res = await fetch(currentUrl, {
      method,
      headers,
      body: method === 'GET' || method === 'HEAD' ? undefined : body,
      redirect: 'manual',
      signal: init.signal || AbortSignal.timeout(25000),
    });

    mergeSetCookies(jar, res);

    const status = res.status;
    if (status === 429) {
      const retryHeader = res.headers.get('Retry-After');
      const retrySec = retryHeader ? parseInt(retryHeader, 10) || 60 : 60;
      throw new ERPRateLimitError(
        'Too many requests. Please try again in one minute.',
        retrySec
      );
    }

    const location = res.headers.get('location');
    if (status >= 300 && status < 400 && location) {
      const nextUrl = new URL(location, currentUrl);
      nextUrl.protocol = 'https:';
      if (nextUrl.origin !== ERP_URL) {
        throw new Error('ERP redirect left the configured origin');
      }
      currentUrl = nextUrl.toString();
      if (status === 303 || status === 302 || status === 301) {
        method = 'GET';
        body = undefined;
      }
      continue;
    }
    return res;
  }
  throw new Error('Too many redirects while contacting the ERP');
}

export function parseGenericTable(
  html: string | null | undefined
): Record<string, unknown>[] {
  if (!html || typeof html !== 'string' || html.trim() === '') {
    return [];
  }

  const trimmedInput = html.trim();
  if (
    (trimmedInput.startsWith('{') && trimmedInput.endsWith('}')) ||
    (trimmedInput.startsWith('[') && trimmedInput.endsWith(']'))
  ) {
    try {
      const parsedJson = JSON.parse(trimmedInput);
      if (Array.isArray(parsedJson)) {
        if (
          parsedJson.every((item) => typeof item === 'object' && item !== null)
        ) {
          return parsedJson;
        }
      } else if (typeof parsedJson === 'object' && parsedJson !== null) {
        for (const key of [
          'html',
          'data',
          'content',
          'body',
          'table',
          'response',
        ]) {
          if (
            typeof parsedJson[key] === 'string' &&
            parsedJson[key].includes('<table')
          ) {
            return parseGenericTable(parsedJson[key]);
          }
        }
        for (const key of ['data', 'rows', 'result', 'items']) {
          if (
            Array.isArray(parsedJson[key]) &&
            parsedJson[key].every(
              (item: unknown) => typeof item === 'object' && item !== null
            )
          ) {
            return parsedJson[key] as Record<string, unknown>[];
          }
        }
      }
    } catch {
      // Not JSON, continue with HTML table parsing
    }
  }

  const $clean = cheerio.load(html);
  $clean('script, style, noscript').remove();
  const cleanHtml = $clean.html() || '';

  if (cleanHtml.trim() === '') {
    return [];
  }

  const $ = cheerio.load(cleanHtml);
  const tables = $('table');

  if (tables.length === 0) {
    return [];
  }

  function getDirectRows($table: cheerio.Cheerio<Element>): Element[] {
    const rows: Element[] = [];
    $table.children().each((_i: number, child: Element) => {
      const tag = child.tagName?.toLowerCase();
      if (tag === 'tr') {
        rows.push(child);
      } else if (tag === 'tbody' || tag === 'thead' || tag === 'tfoot') {
        $(child)
          .children('tr')
          .each((_j: number, trChild: Element) => {
            rows.push(trChild);
          });
      }
    });
    return rows;
  }

  function getNodeText($cell: cheerio.Cheerio<Element>): string {
    const $clone = $cell.clone();
    $clone.find('script, style, noscript').remove();
    $clone.find('br').replaceWith('\n');
    return $clone
      .text()
      .split('\n')
      .map((line) => line.replace(/\s+/g, ' ').trim())
      .filter(Boolean)
      .join('\n');
  }

  function getNodeHref($cell: cheerio.Cheerio<Element>): string | null {
    const a = $cell.find('a[href]').first();
    if (a.length > 0) {
      const href = a.attr('href');
      return href ? href.trim() : null;
    }
    return null;
  }

  let bestRows: Record<string, unknown>[] = [];
  let maxColsFound = 0;

  tables.each((_tIdx: number, tableElem: Element) => {
    const $table = $(tableElem);
    const allTrs = getDirectRows($table);

    if (allTrs.length === 0) return;

    let headers: string[] = [];
    let dataRowStartIndex = 0;

    const firstTr = $(allTrs[0]);
    const ths = firstTr.children('th');
    if (ths.length > 0) {
      headers = ths.map((_i: number, el: Element) => getNodeText($(el))).get();
      dataRowStartIndex = 1;
    } else {
      const tds = firstTr.children('td');
      if (tds.length > 0) {
        headers = tds
          .map((_i: number, el: Element) => getNodeText($(el)))
          .get();
        dataRowStartIndex = 1;
      }
    }

    headers = headers.map((h, idx) => {
      const clean = h.trim();
      return clean !== '' ? clean : `column_${idx + 1}`;
    });

    const counts: Record<string, number> = {};
    headers = headers.map((h) => {
      counts[h] = (counts[h] || 0) + 1;
      return counts[h] > 1 ? `${h}_${counts[h]}` : h;
    });

    const currentTableData: Record<string, unknown>[] = [];

    for (let i = dataRowStartIndex; i < allTrs.length; i++) {
      const $row = $(allTrs[i]);
      const cells = $row.children('td, th');

      if (cells.length === 0) continue;

      const rowObj: Record<string, unknown> = {};
      let hasValue = false;

      cells.each((cIdx: number, cellElem: Element) => {
        const $cell = $(cellElem);
        const colName = headers[cIdx] || `column_${cIdx + 1}`;
        const cellText = getNodeText($cell);
        const href = getNodeHref($cell);

        if (cellText !== '') hasValue = true;

        if (href) {
          rowObj[colName] = cellText;
          rowObj[`${colName}_href`] = href;
        } else {
          rowObj[colName] = cellText;
        }
      });

      if (hasValue) {
        currentTableData.push(rowObj);
      }
    }

    if (
      currentTableData.length > bestRows.length ||
      (currentTableData.length === bestRows.length &&
        headers.length > maxColsFound)
    ) {
      bestRows = currentTableData;
      maxColsFound = headers.length;
    }
  });

  return bestRows;
}
