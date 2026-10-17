import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { POST } from './ai/chat/route';
import { TOOLS_REGISTRY } from '@/lib/ai/tools';
import { executeTool, processAIChat } from '@/lib/ai/executor';

describe('Challenger M3 Suite — AI Chat API Route (/api/ai/chat/route.ts)', () => {
  // 1. JSON Response Format
  test('1.1 JSON Response Format adheres strictly to Interface Contract 3', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'What is my attendance in OS?' }],
      }),
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 200);

    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.ok(json.message, 'Response body must contain message object');
    assert.strictEqual(json.message.role, 'assistant');
    assert.ok(
      typeof json.message.content === 'string' &&
        json.message.content.length > 0
    );
    assert.ok(
      Array.isArray(json.toolCalls),
      'toolCalls must be an array when tool is executed'
    );
  });

  // 2. Tool Call Execution Across All 7 Tools
  test('2.1 Tool execution: getAttendance', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'What is my attendance in OS?' }],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'getAttendance');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(Array.isArray(json.toolCalls[0].result.attendance));
  });

  test('2.2 Tool execution: getTimetable', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'What classes do I have today?' }],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'getTimetable');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(Array.isArray(json.toolCalls[0].result.schedule));
  });

  test('2.3 Tool execution: getMarks', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Show internal marks' }],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'getMarks');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(Array.isArray(json.toolCalls[0].result.marks));
  });

  test('2.4 Tool execution: getFeeDetails', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Show fee balance' }],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'getFeeDetails');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(json.toolCalls[0].result.breakdown);
  });

  test('2.5 Tool execution: getStudentProfile', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Show student profile info' }],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'getStudentProfile');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(json.toolCalls[0].result.profile);
  });

  test('2.6 Tool execution: calculateAttendanceTarget', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [
          { role: 'user', content: 'How many classes can I miss in OS?' },
        ],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'calculateAttendanceTarget');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(typeof json.toolCalls[0].result.message === 'string');
  });

  test('2.7 Tool execution: predictCGPA', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Predict CGPA for next semester' }],
      }),
    });
    const res = await POST(req);
    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'predictCGPA');
    assert.ok(json.toolCalls[0].result.success);
    assert.ok(typeof json.toolCalls[0].result.predictedCGPA === 'number');
  });

  // 3. Session Cookie Propagation & Resolution
  test('3.1 Session cookie propagation from request cookies', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Cookie:
          'kl_erp_session=b64.eyJjb29raWVzIjpbXSwiY3NyZlRva2VuIjoiZGVtb19jc3JmXzEyMyJ9',
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Show fee balance' }],
      }),
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 200);

    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.strictEqual(json.toolCalls[0].tool, 'getFeeDetails');
  });

  test('3.2 Session token resolution from x-session-id header fallback', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-session-id':
          'b64.eyJjb29raWVzIjpbXSwiY3NyZlRva2VuIjoiZGVtb19jc3JmXzEyMyJ9',
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Show fee balance' }],
      }),
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 200);
    const json = await res.json();
    assert.strictEqual(json.success, true);
  });

  // 4. Offline & Error Fallback
  test('4.1 Invalid JSON payload returns status 400 with success: false', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{ malformed-json',
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 400);

    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(json.error, 'Invalid JSON payload in request body');
  });

  test('4.2 Empty or missing messages array returns status 400', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [] }),
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 400);

    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(
      json.error,
      'Request body must contain a non-empty messages array'
    );
  });

  test('4.3 Invalid last message string content returns status 400', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [{ role: 'user', content: 12345 }] }),
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 400);

    const json = await res.json();
    assert.strictEqual(json.success, false);
    assert.strictEqual(
      json.error,
      'Last message in conversation must contain valid string content'
    );
  });

  test('4.4 Offline mode gracefully uses demo fallbacks without throwing 500 errors', async () => {
    const req = new NextRequest('http://localhost/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'What is my attendance?' }],
        sessionId: 'invalid_or_offline_session',
      }),
    });

    const res = await POST(req);
    assert.strictEqual(res.status, 200);

    const json = await res.json();
    assert.strictEqual(json.success, true);
    assert.ok(json.message.content.length > 0);
  });
});

describe('Challenger M3 Suite — Copilot UI Integration Contracts', () => {
  test('All 7 ERP tools are registered in TOOLS_REGISTRY', () => {
    assert.strictEqual(TOOLS_REGISTRY.length, 7);
    const names = TOOLS_REGISTRY.map((t) => t.name);
    const expected = [
      'getAttendance',
      'getTimetable',
      'getMarks',
      'getFeeDetails',
      'getStudentProfile',
      'calculateAttendanceTarget',
      'predictCGPA',
    ];
    for (const name of expected) {
      assert.ok(names.includes(name), `Missing tool ${name} in registry`);
    }
  });

  test('Natural language matcher returns valid intent for all UI suggestion chips', async () => {
    const queries = [
      'What is my attendance in OS?',
      'Show my schedule for today',
      'Show internal marks',
      'Show fee balance',
      'Show student profile info',
      'How many classes can I miss in OS?',
      'Predict CGPA for next semester',
    ];

    for (const query of queries) {
      const res = await processAIChat([{ role: 'user', content: query }]);
      assert.ok(
        res.toolCalls && res.toolCalls.length > 0,
        `Query "${query}" failed to produce tool call`
      );
      assert.ok(
        res.toolCalls[0].tool,
        `Query "${query}" returned empty toolName`
      );
    }
  });

  test('Calculators work deterministically with edge cases', async () => {
    // calculateAttendanceTarget below target
    const resBelow = await executeTool('calculateAttendanceTarget', {
      currentAttended: 15,
      currentTotal: 20,
      targetPercent: 90,
    });
    assert.strictEqual(resBelow.success, true);

    // predictCGPA valid inputs
    const resCGPA = await executeTool('predictCGPA', {
      currentCGPA: 8.5,
      completedCredits: 60,
      newCourses: [{ credits: 4, expectedGrade: 'O' }],
    });
    assert.strictEqual(resCGPA.success, true);
  });
});
