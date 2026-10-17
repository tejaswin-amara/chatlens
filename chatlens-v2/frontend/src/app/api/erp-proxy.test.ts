import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { GET, POST } from './erp-proxy/[module]/route';

test('POST /api/erp-proxy/attendance fails when CSRF token is missing', async () => {
  const req = new NextRequest('http://localhost/api/erp-proxy/attendance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ academicYear: '2023-24', semesterId: 'EVEN' }),
  });

  const params = Promise.resolve({ module: 'attendance' });
  const res = await POST(req, { params });

  assert.strictEqual(res.status, 400);
  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.error, 'CSRF token missing');
});

test('POST /api/erp-proxy/attendance fails when academicYear or semesterId is missing', async () => {
  const req = new NextRequest('http://localhost/api/erp-proxy/attendance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ csrfToken: 'demo_csrf_token_123' }),
  });

  const params = Promise.resolve({ module: 'attendance' });
  const res = await POST(req, { params });

  assert.strictEqual(res.status, 400);
  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.error, 'Missing academicYear or semesterId');
});

test('GET /api/erp-proxy/unknown-module returns 404 Not Found', async () => {
  const req = new NextRequest('http://localhost/api/erp-proxy/unknown-module', {
    method: 'GET',
  });

  const params = Promise.resolve({ module: 'unknown-module' });
  const res = await GET(req, { params });

  assert.strictEqual(res.status, 404);
  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.ok(json.error.includes('Unknown module'));
});

test('POST /api/erp-proxy/attendance with demo session returns mock attendance payload', async () => {
  const req = new NextRequest('http://localhost/api/erp-proxy/attendance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      academicYear: '2023-24',
      semesterId: 'EVEN',
      csrfToken: 'demo_csrf_token_123',
    }),
  });

  const params = Promise.resolve({ module: 'attendance' });
  const res = await POST(req, { params });

  assert.strictEqual(res.status, 200);
  const json = await res.json();
  assert.strictEqual(json.success, true);
  assert.ok(Array.isArray(json.attendanceData));
  assert.ok(json.attendanceData.length > 0);
});

test('GET /api/erp-proxy/profile with demo session returns mock profile payload', async () => {
  const req = new NextRequest('http://localhost/api/erp-proxy/profile', {
    method: 'GET',
    headers: {
      cookie: 'kl_erp_session=enc.demo_session_data',
    },
  });

  const params = Promise.resolve({ module: 'profile' });
  const res = await GET(req, { params });

  assert.strictEqual(res.status, 200);
  const json = await res.json();
  assert.strictEqual(json.success, true);
  assert.ok(json.data);
  assert.strictEqual(json.data.name, 'Alex Student');
});

test('GET /api/erp-proxy/cgpa with demo session returns mock CGPA payload', async () => {
  const req = new NextRequest('http://localhost/api/erp-proxy/cgpa', {
    method: 'GET',
    headers: {
      cookie: 'kl_erp_session=enc.demo_session_data',
    },
  });

  const params = Promise.resolve({ module: 'cgpa' });
  const res = await GET(req, { params });

  assert.strictEqual(res.status, 200);
  const json = await res.json();
  assert.strictEqual(json.success, true);
  assert.ok(Array.isArray(json.data));
  assert.strictEqual(json.data[0].CGPA, '9.15');
});
