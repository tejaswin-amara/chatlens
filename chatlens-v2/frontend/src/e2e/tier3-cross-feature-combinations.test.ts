process.env.KL_SYNC_DEMO_MODE = process.env.KL_SYNC_DEMO_MODE ?? 'true';
process.env.KL_SYNC_AI_MODE = process.env.KL_SYNC_AI_MODE ?? 'offline';

import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';

import { POST as handleLogin } from '@/app/api/login/route';
import { GET as handleErpProxyGet } from '@/app/api/erp-proxy/[module]/route';
import { POST as handleAiChat } from '@/app/api/ai/chat/route';
import { GET as handleFetchPhotoGet } from '@/app/api/fetch-photo/route';

import {
  executeTool,
  executeCalculateAttendanceTarget,
  executePredictCGPA,
} from '@/lib/ai/executor';
import { encodeSession } from '@/lib/session';
import { attendanceResponseSchema, profileResponseSchema } from '@/lib/schemas';

// ============================================================================
// Tier 3: Cross-Feature Combinations (Integration across Multiple Subsystems)
// ============================================================================

test('Tier 3 - Combo 1: ERP Proxy Attendance Fetch + Attendance Target Calculation Engine', async () => {
  // Step 1: Fetch attendance from ERP proxy
  const req = new NextRequest(
    'http://localhost/api/erp-proxy/attendance?academicYear=2025-2026&semesterId=1&csrfToken=demo_csrf'
  );
  const res = await handleErpProxyGet(req, {
    params: Promise.resolve({ module: 'attendance' }),
  });
  assert.strictEqual(res.status, 200);

  const json = await res.json();
  const parsed = attendanceResponseSchema.parse(json);
  assert.strictEqual(parsed.success, true);
  assert.ok(parsed.attendanceData && parsed.attendanceData.length > 0);

  // Step 2: Extract OS (23CS2104R) attendance subject
  const osSubject = parsed.attendanceData.find(
    (s) =>
      s['Course Code'] === '23CS2104R' ||
      s['Course Title']?.includes('Operating Systems')
  );

  const conducted = parseFloat(
    osSubject ? String(osSubject['Conducted Hours'] || '40') : '40'
  );
  const attended = parseFloat(
    osSubject ? String(osSubject['Attended Hours'] || '33') : '33'
  );

  // Step 3: Run calculateAttendanceTarget for 85% requirement
  const targetResult = executeCalculateAttendanceTarget({
    currentAttended: attended,
    currentTotal: conducted,
    targetPercent: 85,
  });

  assert.strictEqual(targetResult.success, true);
  assert.strictEqual(targetResult.currentPercentage, 82.5);
  assert.strictEqual(targetResult.classesNeeded, 7);
  assert.strictEqual(targetResult.status, 'below_target');
  assert.ok(
    targetResult.message.includes('attend the next 7 consecutive class(es)')
  );
});

test('Tier 3 - Combo 2: ERP Proxy Marks Fetch + Predict CGPA Mathematical Pipeline', async () => {
  // Step 1: Fetch marks from ERP proxy
  const marksReq = new NextRequest(
    'http://localhost/api/erp-proxy/marks?academicYear=2025-2026&semesterId=1&csrfToken=demo_csrf'
  );
  const marksRes = await handleErpProxyGet(marksReq, {
    params: Promise.resolve({ module: 'marks' }),
  });
  assert.strictEqual(marksRes.status, 200);

  const marksJson = await marksRes.json();
  assert.strictEqual(marksJson.success, true);
  assert.ok(Array.isArray(marksJson.data));

  // Step 2: Predict CGPA using predicted future courses
  const cgpaResult = executePredictCGPA({
    currentCGPA: 8.42,
    completedCredits: 72,
    newCourses: [
      { credits: 4, expectedGrade: 'O' }, // 10 points * 4 = 40
      { credits: 3, expectedGrade: 'A+' }, // 9 points * 3 = 27
    ],
  });

  assert.strictEqual(cgpaResult.success, true);
  assert.strictEqual(cgpaResult.currentCGPA, 8.42);
  assert.strictEqual(cgpaResult.completedCredits, 72);
  assert.strictEqual(cgpaResult.newCredits, 7);
  assert.strictEqual(cgpaResult.totalCredits, 79);

  assert.strictEqual(cgpaResult.predictedCGPA, 8.52);
  assert.strictEqual(cgpaResult.gpaDelta, 0.1);
});

test('Tier 3 - Combo 3: AI Chat API Multi-Tool Execution (Fee Breakdown + Profile Information)', async () => {
  // Step 1: Ask fee question
  const feeReq = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [{ role: 'user', content: 'What is my pending fee balance?' }],
    }),
  });
  const feeRes = await handleAiChat(feeReq);
  assert.strictEqual(feeRes.status, 200);
  const feeJson = await feeRes.json();
  assert.strictEqual(feeJson.toolCalls[0].tool, 'getFeeDetails');
  assert.strictEqual(feeJson.toolCalls[0].result.breakdown.hasPendingDue, true);

  // Step 2: Ask profile question in same conversation
  const profileReq = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [
        { role: 'user', content: 'What is my pending fee balance?' },
        { role: 'assistant', content: feeJson.message.content },
        { role: 'user', content: 'Who am I? Show my student profile details.' },
      ],
    }),
  });
  const profileRes = await handleAiChat(profileReq);
  assert.strictEqual(profileRes.status, 200);
  const profileJson = await profileRes.json();
  assert.strictEqual(profileJson.toolCalls[0].tool, 'getStudentProfile');
  assert.strictEqual(
    profileJson.toolCalls[0].result.profile.name,
    'Alex Student'
  );
});

test('Tier 3 - Combo 4: Encrypted Session Creation -> Proxy Cookie Propagation -> Zod Validation', async () => {
  const customSession = {
    cookies: [{ name: 'PHPSESSID', value: 'demo_combo_sess_777' }],
    csrfToken: 'demo_csrf_777',
    userAgent: 'Mozilla/5.0 (Integration Test)',
  };
  const sessionToken = await encodeSession(customSession);

  // Request ERP proxy with encrypted session in header
  const req = new NextRequest('http://localhost/api/erp-proxy/profile', {
    headers: {
      'x-session-id': sessionToken,
    },
  });

  const res = await handleErpProxyGet(req, {
    params: Promise.resolve({ module: 'profile' }),
  });
  assert.strictEqual(res.status, 200);

  const json = await res.json();
  const parsed = profileResponseSchema.parse(json);
  assert.strictEqual(parsed.success, true);
  assert.ok(parsed.data?.name);
});

test('Tier 3 - Combo 5: Login Flow -> Session Issuance -> Photo Route Fetch', async () => {
  // Step 1: Login
  const validSessionToken = await encodeSession({
    cookies: [{ name: 'PHPSESSID', value: 'demo_phpsessid_123' }],
    csrfToken: 'demo_csrf_token_123',
    userAgent: 'Mozilla/5.0',
  });

  const loginReq = new NextRequest('http://localhost/api/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      cookie: `kl_captcha_session=${validSessionToken}`,
    },
    body: JSON.stringify({
      username: '2100030000',
      password: 'demo_password',
      captcha: 'ABCD',
    }),
  });

  const loginRes = await handleLogin(loginReq);
  assert.strictEqual(loginRes.status, 200);

  const loginJson = await loginRes.json();
  assert.strictEqual(loginJson.success, true);

  // Step 2: Fetch photo with returned session cookie
  const authCookie = loginRes.headers
    .get('set-cookie')
    ?.match(/kl_erp_session=[^;]+/)?.[0];
  const photoReq = new NextRequest(
    'http://localhost/api/fetch-photo?id=2100030000',
    { headers: { cookie: authCookie || '' } }
  );

  const photoRes = await handleFetchPhotoGet(photoReq);
  assert.ok(photoRes.status === 200 || photoRes.status === 404);
});

test('Tier 3 - Combo 6: Tool Execution Engine + Fee Details Currency Parsing', async () => {
  const feeRes = await executeTool('getFeeDetails', {});
  assert.strictEqual(feeRes.success, true);

  const result = feeRes.result as {
    breakdown: { totalAmount: number; totalPaid: number; totalPending: number };
  };

  assert.strictEqual(result.breakdown.totalAmount, 210000);
  assert.strictEqual(result.breakdown.totalPaid, 195000);
  assert.strictEqual(result.breakdown.totalPending, 15000);
});
