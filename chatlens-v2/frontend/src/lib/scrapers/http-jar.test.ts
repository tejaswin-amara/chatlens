import test from 'node:test';
import assert from 'node:assert/strict';
import {
  cookieHeader,
  mergeSetCookies,
  jarToArray,
  arrayToJar,
  ERP_ENDPOINTS,
  ATTENDANCE_URL,
  fetchWithJar,
  CookieJar,
} from './http-jar';

test('cookieHeader converts jar dictionary to HTTP Cookie header string', () => {
  const jar: CookieJar = {
    PHPSESSID: 'sess123',
    kl_token: 'tok456',
  };

  const header = cookieHeader(jar);
  assert.strictEqual(header, 'PHPSESSID=sess123; kl_token=tok456');

  assert.strictEqual(cookieHeader({}), '');
});

test('jarToArray and arrayToJar bidirectional conversion', () => {
  const jar: CookieJar = {
    PHPSESSID: 'sess123',
    user_id: '1001',
  };

  const arr = jarToArray(jar);
  assert.deepEqual(arr, [
    { name: 'PHPSESSID', value: 'sess123' },
    { name: 'user_id', value: '1001' },
  ]);

  const reconstructed = arrayToJar(arr);
  assert.deepEqual(reconstructed, jar);

  assert.deepEqual(arrayToJar(undefined), {});
  assert.deepEqual(arrayToJar([]), {});
});

test('mergeSetCookies extracts cookies from Set-Cookie headers', () => {
  const jar: CookieJar = {};
  const mockHeaders = new Headers();
  mockHeaders.append(
    'Set-Cookie',
    'PHPSESSID=new_sess_789; Path=/; HttpOnly; Secure'
  );
  mockHeaders.append('Set-Cookie', 'remember_me=true; Path=/; SameSite=Lax');

  const mockResponse = new Response(null, { headers: mockHeaders });
  mergeSetCookies(jar, mockResponse);

  assert.strictEqual(jar.PHPSESSID, 'new_sess_789');
  assert.strictEqual(jar.remember_me, 'true');
});

test('fetchWithJar preserves cookies across same-origin redirects and converts POST 302 to GET', async () => {
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; method: string; cookie?: string }> = [];
  try {
    globalThis.fetch = (async (
      input: URL | RequestInfo,
      init?: RequestInit
    ) => {
      const url = String(input);
      calls.push({
        url,
        method: init?.method || 'GET',
        cookie: new Headers(init?.headers).get('Cookie') || undefined,
      });
      if (calls.length === 1) {
        return new Response(null, {
          status: 302,
          headers: {
            location: '/next',
            'Set-Cookie': 'PHPSESSID=refreshed; Path=/',
          },
        });
      }
      return new Response('ok', { status: 200 });
    }) as typeof fetch;

    const jar: CookieJar = { PHPSESSID: 'initial' };
    const response = await fetchWithJar(ATTENDANCE_URL, jar, {
      method: 'POST',
      body: 'academicYear=2025',
    });
    assert.strictEqual(response.status, 200);
    assert.strictEqual(jar.PHPSESSID, 'refreshed');
    assert.strictEqual(calls[0]?.method, 'POST');
    assert.strictEqual(calls[1]?.method, 'GET');
    assert.match(calls[1]?.cookie || '', /PHPSESSID=refreshed/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchWithJar rejects redirects outside the configured ERP origin', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = (async () =>
      new Response(null, {
        status: 302,
        headers: { location: 'https://evil.example/collect' },
      })) as typeof fetch;
    await assert.rejects(
      () => fetchWithJar(ATTENDANCE_URL, {}, { method: 'GET' }),
      /redirect left the configured origin/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('ERP_ENDPOINTS dictionary completeness and valid URLs', () => {
  const requiredModules = [
    'marks',
    'timetable',
    'fee',
    'profile',
    'cgpa',
    'end-exam',
    'exam-seating',
    'circulars',
    'hostel',
    'library',
  ];

  for (const mod of requiredModules) {
    assert.ok(mod in ERP_ENDPOINTS, `ERP_ENDPOINTS must include key '${mod}'`);
    assert.strictEqual(
      new URL(ERP_ENDPOINTS[mod]).hostname,
      'newerp.kluniversity.in',
      `Endpoint for '${mod}' must point to newerp.kluniversity.in`
    );
  }
});
