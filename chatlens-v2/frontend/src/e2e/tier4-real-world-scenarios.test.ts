process.env.KL_SYNC_DEMO_MODE = process.env.KL_SYNC_DEMO_MODE ?? 'true';
process.env.KL_SYNC_AI_MODE = process.env.KL_SYNC_AI_MODE ?? 'offline';

import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';

// Route Handlers
import { GET as handleCaptchaGet } from '@/app/api/captcha/route';
import { POST as handleLogin } from '@/app/api/login/route';
import { GET as handleErpProxyGet } from '@/app/api/erp-proxy/[module]/route';
import { POST as handleAiChat } from '@/app/api/ai/chat/route';
import { GET as handleFetchPhotoGet } from '@/app/api/fetch-photo/route';

// Zod Schemas & AI Executor
import {
  attendanceResponseSchema,
  feeResponseSchema,
  profileDataSchema,
} from '@/lib/schemas';
import { executeTool } from '@/lib/ai/executor';

// ============================================================================
// Tier 4: Real-World Scenarios (End-to-End User Workflows)
// ============================================================================

test('Tier 4 - Scenario 1: Complete Student Login & Multi-Module Dashboard Synchronization', async () => {
  // Step 1: Initial Captcha Challenge Fetch
  const captchaRes = await handleCaptchaGet();
  assert.strictEqual(captchaRes.status, 200);

  const captchaData = await captchaRes.json();
  assert.ok(captchaData.captchaImage);
  const captchaCookie =
    captchaRes.headers
      .get('set-cookie')
      ?.match(/kl_captcha_session=[^;]+/)?.[0] || '';
  assert.ok(captchaCookie.length > 0);

  // Step 2: Student Login Submission
  const loginReq = new NextRequest('http://localhost/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie: captchaCookie },
    body: JSON.stringify({
      username: '2100030000',
      password: 'student_password_123',
      captcha: captchaData.solvedCaptcha || '8888',
    }),
  });
  const loginRes = await handleLogin(loginReq);
  assert.strictEqual(loginRes.status, 200);
  const loginData = await loginRes.json();
  assert.strictEqual(loginData.success, true);
  const authCookie =
    loginRes.headers.get('set-cookie')?.match(/kl_erp_session=[^;]+/)?.[0] ||
    '';
  assert.ok(authCookie.length > 0);

  // Step 3: Parallel Data Synchronization across all ERP Modules
  const [attRes, ttRes, marksRes, feeRes, profileRes] = await Promise.all([
    handleErpProxyGet(
      new NextRequest(
        'http://localhost/api/erp-proxy/attendance?academicYear=2025-2026&semesterId=1',
        {
          headers: { cookie: authCookie },
        }
      ),
      { params: Promise.resolve({ module: 'attendance' }) }
    ),
    handleErpProxyGet(
      new NextRequest(
        'http://localhost/api/erp-proxy/timetable?academicYear=2025-2026&semesterId=1',
        {
          headers: { cookie: authCookie },
        }
      ),
      { params: Promise.resolve({ module: 'timetable' }) }
    ),
    handleErpProxyGet(
      new NextRequest(
        'http://localhost/api/erp-proxy/marks?academicYear=2025-2026&semesterId=1',
        {
          headers: { cookie: authCookie },
        }
      ),
      { params: Promise.resolve({ module: 'marks' }) }
    ),
    handleErpProxyGet(
      new NextRequest('http://localhost/api/erp-proxy/fee', {
        headers: { cookie: authCookie },
      }),
      { params: Promise.resolve({ module: 'fee' }) }
    ),
    handleErpProxyGet(
      new NextRequest('http://localhost/api/erp-proxy/profile', {
        headers: { cookie: authCookie },
      }),
      { params: Promise.resolve({ module: 'profile' }) }
    ),
  ]);

  // Step 4: Validate all response statuses & Zod schemas
  assert.strictEqual(attRes.status, 200);
  assert.strictEqual(ttRes.status, 200);
  assert.strictEqual(marksRes.status, 200);
  assert.strictEqual(feeRes.status, 200);
  assert.strictEqual(profileRes.status, 200);

  const attJson = await attRes.json();
  const feeJson = await feeRes.json();
  const profileJson = await profileRes.json();

  assert.strictEqual(attendanceResponseSchema.parse(attJson).success, true);
  assert.strictEqual(feeResponseSchema.parse(feeJson).success, true);
  assert.strictEqual(
    profileDataSchema.parse(profileJson.data || profileJson).success,
    true
  );

  // Step 5: Student Profile Photo Fetching
  const photoReq = new NextRequest(
    'http://localhost/api/fetch-photo?id=2100030000',
    {
      headers: { cookie: authCookie },
    }
  );
  const photoRes = await handleFetchPhotoGet(photoReq);
  assert.ok(photoRes.status === 200 || photoRes.status === 404);
});

test('Tier 4 - Scenario 2: At-Risk Attendance Warning & Target Remediation Workflow', async () => {
  // Student submits query: "What is my OS attendance and how many classes do I need for 85%?"
  const chatReq = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [
        {
          role: 'user',
          content:
            'What is my OS attendance and how many classes do I need for 85%?',
        },
      ],
    }),
  });

  const chatRes = await handleAiChat(chatReq);
  assert.strictEqual(chatRes.status, 200);

  const json = await chatRes.json();
  assert.strictEqual(json.success, true);
  assert.strictEqual(json.message.role, 'assistant');
  assert.ok(Array.isArray(json.toolCalls));

  // Verify tool calls performed
  const toolNames = json.toolCalls.map((tc: { tool: string }) => tc.tool);
  assert.ok(
    toolNames.includes('getAttendance') ||
      toolNames.includes('calculateAttendanceTarget')
  );

  // Direct calculation check for OS attendance remediation
  const attRes = await executeTool('getAttendance', { subject: 'OS' });
  const attData = attRes.result as {
    attendance: Array<{ 'Attended Hours': string; 'Conducted Hours': string }>;
  };
  const osCourse = attData.attendance[0];

  const targetCalc = await executeTool('calculateAttendanceTarget', {
    currentAttended: parseFloat(osCourse['Attended Hours']),
    currentTotal: parseFloat(osCourse['Conducted Hours']),
    targetPercent: 85,
  });

  const calcResult = targetCalc.result as {
    classesNeeded: number;
    currentPercentage: number;
  };
  assert.strictEqual(calcResult.currentPercentage, 82.5);
  assert.strictEqual(calcResult.classesNeeded, 7);
});

test('Tier 4 - Scenario 3: Academic Goal Setting & CGPA Roadmap Generation', async () => {
  const chatReq = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [
        {
          role: 'user',
          content:
            'Predict my CGPA if I get O grade in 4-credit Machine Learning and A+ grade in 3-credit Cloud Computing.',
        },
      ],
    }),
  });

  const chatRes = await handleAiChat(chatReq);
  assert.strictEqual(chatRes.status, 200);

  const json = await chatRes.json();
  assert.strictEqual(json.success, true);
  assert.ok(Array.isArray(json.toolCalls));
  assert.strictEqual(json.toolCalls[0].tool, 'predictCGPA');

  const predictResult = json.toolCalls[0].result as {
    predictedCGPA: number;
    gpaDelta: number;
    totalCredits: number;
  };

  assert.ok(predictResult.predictedCGPA > 0);
  assert.ok(predictResult.totalCredits > 72);
});

test('Tier 4 - Scenario 4: Financial Balance Audit & Payment Breakdown Alert', async () => {
  const chatReq = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [
        {
          role: 'user',
          content: 'Do I have any pending fee dues or balance?',
        },
      ],
    }),
  });

  const chatRes = await handleAiChat(chatReq);
  assert.strictEqual(chatRes.status, 200);

  const json = await chatRes.json();
  assert.strictEqual(json.success, true);
  assert.ok(Array.isArray(json.toolCalls));
  assert.strictEqual(json.toolCalls[0].tool, 'getFeeDetails');

  const feeBreakdown = json.toolCalls[0].result.breakdown as {
    totalPending: number;
    hasPendingDue: boolean;
    items: Array<{ Status: string; 'Fee Type': string }>;
  };

  assert.strictEqual(feeBreakdown.hasPendingDue, true);
  assert.strictEqual(feeBreakdown.totalPending, 15000);
  assert.ok(feeBreakdown.items.some((item) => item.Status === 'PENDING'));
});
