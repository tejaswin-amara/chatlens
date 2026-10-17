import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { POST } from './ai/chat/route';

test('POST /api/ai/chat returns 400 Bad Request when request body is not valid JSON', async () => {
  const req = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: 'invalid-json-{',
  });

  const res = await POST(req);
  assert.strictEqual(res.status, 400);

  const json = await res.json();
  assert.strictEqual(json.success, false);
  assert.strictEqual(json.error, 'Invalid JSON payload in request body');
});

test('POST /api/ai/chat returns 400 Bad Request when messages array is missing', async () => {
  const req = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ academicYear: '2025-2026' }),
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

test('POST /api/ai/chat processes natural language query and executes getAttendance tool', async () => {
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
  assert.ok(json.message);
  assert.strictEqual(json.message.role, 'assistant');
  assert.ok(typeof json.message.content === 'string');

  assert.ok(Array.isArray(json.toolCalls));
  assert.strictEqual(json.toolCalls[0].tool, 'getAttendance');
  assert.ok(json.toolCalls[0].result.success);
});

test('POST /api/ai/chat processes fee query and returns structured fee breakdown', async () => {
  const req = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [{ role: 'user', content: 'Show fee breakdown' }],
    }),
  });

  const res = await POST(req);
  assert.strictEqual(res.status, 200);

  const json = await res.json();
  assert.strictEqual(json.success, true);
  assert.ok(Array.isArray(json.toolCalls));
  assert.strictEqual(json.toolCalls[0].tool, 'getFeeDetails');
  assert.ok(json.toolCalls[0].result.breakdown);
});

test('POST /api/ai/chat handles session cookie propagation correctly', async () => {
  const req = new NextRequest('http://localhost/api/ai/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Cookie:
        'kl_erp_session=b64.eyJjb29raWVzIjpbXSwiY3NyZlRva2VuIjoiZGVtb19jc3JmXzEyMyJ9',
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: 'What classes do I have today?' }],
    }),
  });

  const res = await POST(req);
  assert.strictEqual(res.status, 200);

  const json = await res.json();
  assert.strictEqual(json.success, true);
  assert.ok(Array.isArray(json.toolCalls));
  assert.strictEqual(json.toolCalls[0].tool, 'getTimetable');
});
