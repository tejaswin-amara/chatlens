import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { encodeSession, decodeSession, ScraperSession } from '@/lib/session';
import { GET as captchaGET } from '@/app/api/captcha/route';
import { POST as loginPOST } from '@/app/api/login/route';
import {
  GET as erpProxyGET,
  POST as erpProxyPOST,
} from '@/app/api/erp-proxy/[module]/route';
import { GET as fetchPhotoGET } from '@/app/api/fetch-photo/route';
import { POST as aiChatPOST } from '@/app/api/ai/chat/route';

const TEST_SESSION: ScraperSession = {
  cookies: [
    { name: 'PHPSESSID', value: 'sess_prod_998877' },
    { name: 'kl_device', value: 'device_mac_112233' },
  ],
  csrfToken: 'csrf_test_live_token_777',
  userAgent: 'Mozilla/5.0 Challenger Test Suite',
};

test('Challenger M1 - API /api/captcha session emission', async () => {
  const response = await captchaGET();
  assert.strictEqual(
    response.status,
    200,
    'Captcha GET should return 200 status'
  );

  const emittedSessionId = response.headers.get('x-session-id');
  assert.ok(emittedSessionId, 'Captcha response must emit x-session-id header');
  assert.ok(
    emittedSessionId.startsWith('enc.'),
    'Emitted session ID must be encrypted standard format'
  );

  const decoded = await decodeSession(emittedSessionId);
  assert.ok(
    decoded.csrfToken,
    'Decoded session must contain a valid csrfToken'
  );
});

test('Challenger M1 - API /api/login session propagation (Headers vs Body vs Missing)', async () => {
  const validSessionId = await encodeSession(TEST_SESSION);

  // 1. Session passed via x-session-id header
  const reqHeader = new NextRequest('http://localhost:3000/api/login', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-session-id': validSessionId,
    },
    body: JSON.stringify({
      username: 'demo',
      password: 'password123',
      captcha: '8888',
    }),
  });
  const resHeader = await loginPOST(reqHeader);
  assert.strictEqual(resHeader.status, 200);
  const dataHeader = await resHeader.json();
  assert.strictEqual(dataHeader.success, true);
  assert.ok(
    dataHeader.sessionId,
    'Login response must return updated sessionId'
  );
  const decodedFromResHeader = await decodeSession(dataHeader.sessionId);
  assert.ok(
    decodedFromResHeader.cookies,
    'Decoded session should contain cookies'
  );

  // 2. Session passed via JSON body
  const reqBody = new NextRequest('http://localhost:3000/api/login', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      sessionId: validSessionId,
      username: 'demo',
      password: 'password123',
      captcha: '8888',
    }),
  });
  const resBody = await loginPOST(reqBody);
  assert.strictEqual(resBody.status, 200);
  const dataBody = await resBody.json();
  assert.strictEqual(dataBody.success, true);
  assert.ok(dataBody.sessionId);

  // 3. Missing session ID -> 400 Session expired
  const reqMissing = new NextRequest('http://localhost:3000/api/login', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      username: 'demo',
      password: 'password123',
      captcha: '8888',
    }),
  });
  const resMissing = await loginPOST(reqMissing);
  assert.strictEqual(resMissing.status, 400);
  const dataMissing = await resMissing.json();
  assert.strictEqual(dataMissing.success, false);
  assert.match(dataMissing.message, /Session expired/i);
});

test('Challenger M1 - API /api/erp-proxy/[module] session propagation channels', async () => {
  const customSession: ScraperSession = {
    cookies: [{ name: 'PHPSESSID', value: 'erp_proxy_test_sess' }],
    csrfToken: 'demo_csrf_9999',
  };
  const token = await encodeSession(customSession);
  const params = Promise.resolve({ module: 'attendance' });

  // 1. Session in x-session-id header
  const reqHeader = new NextRequest(
    'http://localhost:3000/api/erp-proxy/attendance?academicYear=2025-2026&semesterId=1',
    {
      method: 'GET',
      headers: { 'x-session-id': token },
    }
  );
  const resHeader = await erpProxyGET(reqHeader, { params });
  assert.strictEqual(resHeader.status, 200);

  // 2. Session in kl_erp_session cookie
  const reqCookie = new NextRequest(
    'http://localhost:3000/api/erp-proxy/attendance?academicYear=2025-2026&semesterId=1',
    {
      method: 'GET',
      headers: { cookie: `kl_erp_session=${token}` },
    }
  );
  const resCookie = await erpProxyGET(reqCookie, { params });
  assert.strictEqual(resCookie.status, 200);

  // 3. Session in POST body sessionId
  const reqBody = new NextRequest(
    'http://localhost:3000/api/erp-proxy/attendance',
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        sessionId: token,
        academicYear: '2025-2026',
        semesterId: '1',
      }),
    }
  );
  const resBody = await erpProxyPOST(reqBody, { params });
  assert.strictEqual(resBody.status, 200);

  // 4. Session in searchParams ?sessionId=
  const reqQuery = new NextRequest(
    `http://localhost:3000/api/erp-proxy/attendance?sessionId=${encodeURIComponent(token)}&academicYear=2025-2026&semesterId=1`,
    {
      method: 'GET',
    }
  );
  const resQuery = await erpProxyGET(reqQuery, { params });
  assert.strictEqual(resQuery.status, 200);
});

test('Challenger M1 - API /api/fetch-photo session extraction', async () => {
  const token = await encodeSession(TEST_SESSION);

  // 1. Missing session -> 401 Unauthorized
  const reqNoSession = new NextRequest(
    'http://localhost:3000/api/fetch-photo?id=2100030000'
  );
  const resNoSession = await fetchPhotoGET(reqNoSession);
  assert.strictEqual(resNoSession.status, 401);

  // 2. Session in x-session-id header
  const reqHeader = new NextRequest(
    'http://localhost:3000/api/fetch-photo?id=2100030000',
    {
      headers: { 'x-session-id': token },
    }
  );
  const resHeader = await fetchPhotoGET(reqHeader);
  // Returns 404 because upstream ERP photo is unreachable during offline unit test, but passes auth check (not 401)
  assert.notStrictEqual(
    resHeader.status,
    401,
    'Request with valid session should pass auth check'
  );
});

test('Challenger M1 - API /api/ai/chat session propagation & execution context', async () => {
  const token = await encodeSession(TEST_SESSION);

  // 1. Session in body.sessionId
  const reqBody = new NextRequest('http://localhost:3000/api/ai/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      sessionId: token,
      messages: [{ role: 'user', content: 'What is my attendance?' }],
    }),
  });
  const resBody = await aiChatPOST(reqBody);
  assert.strictEqual(resBody.status, 200);
  const dataBody = await resBody.json();
  assert.strictEqual(dataBody.success, true);

  // 2. Session in x-session-id header
  const reqHeader = new NextRequest('http://localhost:3000/api/ai/chat', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-session-id': token,
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: 'Show my timetable' }],
    }),
  });
  const resHeader = await aiChatPOST(reqHeader);
  assert.strictEqual(resHeader.status, 200);
  const dataHeader = await resHeader.json();
  assert.strictEqual(dataHeader.success, true);
});

test('Challenger M1 - Multi-Hop Session Round-Trip Chain Simulation', async () => {
  // Step 1: GET /api/captcha -> get initial token S1
  const captchaRes = await captchaGET();
  const tokenS1 = captchaRes.headers.get('x-session-id')!;
  assert.ok(tokenS1, 'S1 token acquired');

  // Step 2: POST /api/login with token S1 -> get updated token S2
  const loginReq = new NextRequest('http://localhost:3000/api/login', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-session-id': tokenS1,
    },
    body: JSON.stringify({
      username: 'demo',
      password: 'password123',
      captcha: '8888',
    }),
  });
  const loginRes = await loginPOST(loginReq);
  const loginData = await loginRes.json();
  const tokenS2 = loginData.sessionId;
  assert.ok(tokenS2, 'S2 token acquired from login response');

  // Verify S2 can be decoded and holds valid structure
  const decodedS2 = await decodeSession(tokenS2);
  assert.ok(decodedS2.csrfToken, 'S2 CSRF token intact');

  // Step 3: POST /api/erp-proxy/attendance with token S2
  const erpReq = new NextRequest(
    'http://localhost:3000/api/erp-proxy/attendance',
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        sessionId: tokenS2,
        academicYear: '2025-2026',
        semesterId: '1',
      }),
    }
  );
  const erpRes = await erpProxyPOST(erpReq, {
    params: Promise.resolve({ module: 'attendance' }),
  });
  assert.strictEqual(erpRes.status, 200);

  // Step 4: GET /api/fetch-photo with token S2 in header
  const photoReq = new NextRequest(
    'http://localhost:3000/api/fetch-photo?id=2100030000',
    {
      headers: { 'x-session-id': tokenS2 },
    }
  );
  const photoRes = await fetchPhotoGET(photoReq);
  assert.notStrictEqual(
    photoRes.status,
    401,
    'Photo request with S2 header passed auth'
  );

  // Step 5: POST /api/ai/chat with token S2
  const chatReq = new NextRequest('http://localhost:3000/api/ai/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      sessionId: tokenS2,
      messages: [{ role: 'user', content: 'What is my profile?' }],
    }),
  });
  const chatRes = await aiChatPOST(chatReq);
  assert.strictEqual(chatRes.status, 200);
  const chatData = await chatRes.json();
  assert.strictEqual(chatData.success, true);
});
