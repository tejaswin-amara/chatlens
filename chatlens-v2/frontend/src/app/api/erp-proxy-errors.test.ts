import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { GET, POST } from './erp-proxy/[module]/route';
import { encodeSession } from '@/lib/session';

test('POST /api/erp-proxy/attendance returns 504 Gateway Timeout when upstream fetch times out', async () => {
  const originalFetch = globalThis.fetch;
  try {
    // Mock fetch to simulate network timeout
    globalThis.fetch = async () => {
      const err = new Error('ETIMEDOUT: Connection timed out');
      err.name = 'TimeoutError';
      throw err;
    };

    const realSession = await encodeSession({
      cookies: [{ name: 'PHPSESSID', value: 'real_active_session_abc123' }],
      csrfToken: 'real_active_csrf_xyz789',
      userAgent: 'Mozilla/5.0',
    });

    const req = new NextRequest('http://localhost/api/erp-proxy/attendance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        cookie: `kl_erp_session=${realSession}`,
      },
      body: JSON.stringify({ academicYear: '2025-2026', semesterId: '1' }),
    });

    const params = Promise.resolve({ module: 'attendance' });
    const res = await POST(req, { params });

    assert.strictEqual(
      res.status,
      504,
      'Status code must be 504 Gateway Timeout'
    );
    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(json.error, 'ERP Gateway Timeout');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('POST /api/erp-proxy/attendance returns 502 Bad Gateway when upstream fetch fails', async () => {
  const originalFetch = globalThis.fetch;
  try {
    // Mock fetch to simulate connection failure / Bad Gateway
    globalThis.fetch = async () => {
      throw new TypeError('fetch failed: ECONNREFUSED 103.159.204.14:443');
    };

    const realSession = await encodeSession({
      cookies: [{ name: 'PHPSESSID', value: 'real_active_session_abc123' }],
      csrfToken: 'real_active_csrf_xyz789',
      userAgent: 'Mozilla/5.0',
    });

    const req = new NextRequest('http://localhost/api/erp-proxy/attendance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        cookie: `kl_erp_session=${realSession}`,
      },
      body: JSON.stringify({ academicYear: '2025-2026', semesterId: '1' }),
    });

    const params = Promise.resolve({ module: 'attendance' });
    const res = await POST(req, { params });

    assert.strictEqual(res.status, 502, 'Status code must be 502 Bad Gateway');
    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(json.error, 'ERP Bad Gateway');
    assert.ok(
      json.details.includes('ECONNREFUSED'),
      'Details should include underlying error message'
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('GET /api/erp-proxy/profile returns 401 Unauthorized when session is expired', async () => {
  const originalFetch = globalThis.fetch;
  try {
    // Mock fetch returning ERP login page HTML (session expired indicator)
    globalThis.fetch = async () => {
      return new Response(
        '<html><body><div id="login-form">Session Expired</div></body></html>',
        { status: 200 }
      );
    };

    const realSession = await encodeSession({
      cookies: [{ name: 'PHPSESSID', value: 'expired_session_123' }],
      csrfToken: 'expired_csrf_123',
      userAgent: 'Mozilla/5.0',
    });

    const req = new NextRequest('http://localhost/api/erp-proxy/profile', {
      method: 'GET',
      headers: {
        cookie: `kl_erp_session=${realSession}`,
      },
    });

    const params = Promise.resolve({ module: 'profile' });
    const res = await GET(req, { params });

    assert.strictEqual(res.status, 401, 'Status code must be 401 Unauthorized');
    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(json.error, 'Session expired. Please re-login.');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
