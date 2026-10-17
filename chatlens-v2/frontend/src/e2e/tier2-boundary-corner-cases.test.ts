process.env.KL_SYNC_DEMO_MODE = process.env.KL_SYNC_DEMO_MODE ?? 'true';
process.env.KL_SYNC_AI_MODE = process.env.KL_SYNC_AI_MODE ?? 'offline';

import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';

// API Route Imports
import { POST as handleLogin } from '@/app/api/login/route';
import { GET as handleErpProxyGet } from '@/app/api/erp-proxy/[module]/route';
import { POST as handleAiChat } from '@/app/api/ai/chat/route';

// AI Tool & Execution Engine Imports
import {
  executeTool,
  executeCalculateAttendanceTarget,
  executePredictCGPA,
  processAIChat,
} from '@/lib/ai/executor';
import { encodeSession } from '@/lib/session';

// ============================================================================
// Tier 2: Boundary & Corner Cases (Empty Inputs, Missing Params, Error Statuses)
// ============================================================================

test('Tier 2 - Boundary 1: NL Intent Parser handles empty, whitespace, and unmapped inputs', async () => {
  const r1 = await processAIChat([{ role: 'user', content: '' }]);
  assert.strictEqual(r1.toolCalls.length, 0);

  const r2 = await processAIChat([{ role: 'user', content: '   ' }]);
  assert.strictEqual(r2.toolCalls.length, 0);

  const r3 = await processAIChat([
    { role: 'user', content: 'random gibberish hello 12345' },
  ]);
  assert.strictEqual(r3.toolCalls.length, 0);
  assert.ok(r3.assistantResponseText.includes('I am KL Sync Copilot'));
});

test('Tier 2 - Boundary 2: ERP Proxy returns 400 when academicYear or semesterId is missing', async () => {
  const req = new NextRequest(
    'http://localhost/api/erp-proxy/attendance?academicYear=2025-2026&csrfToken=demo_csrf'
  );
  const res = await handleErpProxyGet(req, {
    params: Promise.resolve({ module: 'attendance' }),
  });
  assert.strictEqual(res.status, 400);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.error, 'Missing academicYear or semesterId');
});

test('Tier 2 - Boundary 3: ERP Proxy returns 404 for completely unknown module name', async () => {
  const req = new NextRequest(
    'http://localhost/api/erp-proxy/non-existent-module'
  );
  const res = await handleErpProxyGet(req, {
    params: Promise.resolve({ module: 'non-existent-module' }),
  });
  assert.strictEqual(res.status, 404);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.ok(json.error.includes('Unknown module'));
});

test('Tier 2 - Boundary 4: AI Chat API returns 400 on malformed JSON payload', async () => {
  const req = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{"messages": [ invalid json payload',
  });

  const res = await handleAiChat(req);
  assert.strictEqual(res.status, 400);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.error, 'Invalid JSON payload in request body');
});

test('Tier 2 - Boundary 5: AI Chat API returns 400 when messages array is missing or empty', async () => {
  // Missing messages
  const req1 = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'hello' }),
  });
  const res1 = await handleAiChat(req1);
  assert.strictEqual(res1.status, 400);

  // Empty messages array
  const req2 = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: [] }),
  });
  const res2 = await handleAiChat(req2);
  assert.strictEqual(res2.status, 400);
});

test('Tier 2 - Boundary 6: Attendance Target calculator validates zero total & negative bounds via Zod', () => {
  assert.throws(() => {
    executeCalculateAttendanceTarget({ currentAttended: 5, currentTotal: 0 });
  });

  assert.throws(() => {
    executeCalculateAttendanceTarget({ currentAttended: -1, currentTotal: 10 });
  });

  assert.throws(() => {
    executeCalculateAttendanceTarget({
      currentAttended: 10,
      currentTotal: 10,
      targetPercent: 105,
    });
  });
});

test('Tier 2 - Boundary 7: Predict CGPA tool validates bounds (CGPA > 10, negative credits, empty courses)', () => {
  assert.throws(() => {
    executePredictCGPA({
      currentCGPA: 10.5,
      completedCredits: 50,
      newCourses: [{ credits: 3, expectedGrade: 'O' }],
    });
  });

  assert.throws(() => {
    executePredictCGPA({
      currentCGPA: 8.0,
      completedCredits: -5,
      newCourses: [{ credits: 3, expectedGrade: 'O' }],
    });
  });

  assert.throws(() => {
    executePredictCGPA({
      currentCGPA: 8.0,
      completedCredits: 50,
      newCourses: [],
    });
  });
});

test('Tier 2 - Boundary 8: executeTool returns error object on unknown tool name', async () => {
  const result = await executeTool('fakeToolName', { arg: 123 });
  assert.strictEqual(result.success, false);
  assert.strictEqual(result.tool, 'fakeToolName');
  assert.ok(result.error);
  assert.ok(result.error.includes('Unknown tool name'));
});

test('Tier 2 - Boundary 9: Login API returns 400 when missing username, password, or captcha', async () => {
  const req = new NextRequest('http://localhost/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: '2100030000',
      // missing password and captcha
      captchaToken: 'demo_token',
      sessionId: 'session_123',
    }),
  });

  const res = await handleLogin(req);
  assert.strictEqual(res.status, 400);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.message, 'Missing required fields');
});

test('Tier 2 - Boundary 10: Login API returns 400 when x-session-id and body.sessionId are missing', async () => {
  const req = new NextRequest('http://localhost/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: '2100030000',
      password: 'password123',
      captcha: 'ABCD',
      captchaToken: 'demo_token',
    }),
  });

  const res = await handleLogin(req);
  assert.strictEqual(res.status, 400);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.message, 'Session expired. Please refresh captcha.');
});

test('Tier 2 - Boundary 11: Login API returns 400 when captchaToken verification fails', async () => {
  const validSession = await encodeSession({
    cookies: [{ name: 'PHPSESSID', value: 'real_sess' }],
    csrfToken: 'real_csrf',
    userAgent: 'Mozilla/5.0',
  });

  const req = new NextRequest('http://localhost/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'realuser_non_demo',
      password: 'password123',
      captcha: 'ABCD',
      captchaToken: 'invalid_token_99999',
      sessionId: validSession,
    }),
  });

  const res = await handleLogin(req);
  assert.strictEqual(res.status, 400);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(
    json.message,
    'Captcha verification failed. Please try again.'
  );
});

test('Tier 2 - Boundary 12: executeGetAttendance subject filter handles case-insensitivity and sub-strings', async () => {
  const res = await executeTool('getAttendance', {
    subject: 'DATA structures',
  });
  assert.strictEqual(res.success, true);
  const result = res.result as { attendance: Array<{ 'Course Code': string }> };
  assert.ok(result.attendance.length > 0);
  assert.strictEqual(result.attendance[0]['Course Code'], '23CS2101R');
});
