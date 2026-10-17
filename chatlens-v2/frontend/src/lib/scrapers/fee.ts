import {
  ERP_URL,
  ERP_ENDPOINTS,
  ScraperSession,
  arrayToJar,
  fetchWithJar,
  parseGenericTable,
  checkRateLimitText,
} from './http-jar';

export async function fetchFeeData(session: ScraperSession) {
  const jar = arrayToJar(session.cookies);
  const res = await fetchWithJar(ERP_ENDPOINTS['fee'], jar, {
    method: 'GET',
    signal: AbortSignal.timeout(25000),
    extraHeaders: { Origin: ERP_URL, Referer: ERP_URL },
  });
  const html = await res.text();
  checkRateLimitText(html);
  if (html.includes('id="login-form"')) {
    throw new Error('Session expired or invalid ERP route.');
  }
  return { success: true, data: parseGenericTable(html) };
}

export async function fetchGenericModuleData(
  session: ScraperSession,
  targetUrl: string
) {
  const jar = arrayToJar(session.cookies);

  const res = await fetchWithJar(targetUrl, jar, {
    method: 'GET',
    signal: AbortSignal.timeout(25000),
    extraHeaders: {
      Origin: ERP_URL,
      Referer: ERP_URL,
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

  return {
    success: true,
    data: data,
    rawHtmlLength: html.length,
  };
}
