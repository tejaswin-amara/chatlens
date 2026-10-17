import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import {
  fetchWithJar,
  checkRateLimitText,
  ERPRateLimitError,
  ATTENDANCE_URL,
  CookieJar,
} from './http-jar';
import { encodeSession } from '@/lib/session';
import { POST } from '@/app/api/erp-proxy/[module]/route';

test('checkRateLimitText throws ERPRateLimitError on official ERP rate limit strings', () => {
  assert.throws(
    () =>
      checkRateLimitText('Too many requests. Please try again in one minute.'),
    (err: unknown) => {
      assert.ok(err instanceof ERPRateLimitError);
      assert.strictEqual(err.retryAfter, 60);
      assert.match(err.message, /Too many requests/);
      return true;
    }
  );

  assert.throws(
    () =>
      checkRateLimitText(
        '<html><body><h1>Too many requests</h1><p>Please try again in 1 minute</p></body></html>'
      ),
    (err: unknown) => err instanceof ERPRateLimitError
  );

  // Clean HTML without rate limit should not throw
  assert.doesNotThrow(() =>
    checkRateLimitText('<table><tr><td>Normal Attendance</td></tr></table>')
  );
});

test('fetchWithJar detects HTTP 429 and throws ERPRateLimitError with retryAfter header', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = (async () => {
      return new Response(
        'Too many requests. Please try again in one minute.',
        {
          status: 429,
          headers: { 'Retry-After': '90' },
        }
      );
    }) as typeof fetch;

    const jar: CookieJar = { PHPSESSID: 'test_session' };
    await assert.rejects(
      async () => {
        await fetchWithJar(ATTENDANCE_URL, jar);
      },
      (err: unknown) => {
        assert.ok(err instanceof ERPRateLimitError);
        assert.strictEqual(err.retryAfter, 90);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('ERP proxy route converts ERPRateLimitError to HTTP 429 with Retry-After header', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = (async () => {
      return new Response(
        'Too many requests. Please try again in one minute.',
        {
          status: 429,
          headers: { 'Retry-After': '60' },
        }
      );
    }) as typeof fetch;

    const encoded = await encodeSession({
      cookies: [{ name: 'PHPSESSID', value: 'sess_live' }],
      csrfToken: 'csrf_live',
    });

    const req = new NextRequest('http://localhost/api/erp-proxy/attendance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        academicYear: '2025-2026',
        semesterId: '1',
        sessionId: encoded,
      }),
    });

    const res = await POST(req, {
      params: Promise.resolve({ module: 'attendance' }),
    });

    assert.strictEqual(res.status, 429);
    assert.strictEqual(res.headers.get('Retry-After'), '60');

    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(json.isRateLimit, true);
    assert.strictEqual(json.retryAfter, 60);
    assert.match(json.error, /Too many requests/i);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
