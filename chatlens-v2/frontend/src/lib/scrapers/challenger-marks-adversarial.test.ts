import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { NextRequest } from 'next/server';
import { fetchMarksData, fetchEndExamResults, fetchCGPAData } from './marks';
import { ScraperSession, ERP_ENDPOINTS } from './http-jar';
import { executeGetMarks, executeTool, processAIChat } from '@/lib/ai/executor';
import { GET, POST } from '@/app/api/erp-proxy/[module]/route';
import { DEMO_MARKS } from '@/lib/fixtures';

describe('Empirical Challenger Suite: Marks Scraper & Ponytail Debt Neutralization', () => {
  const testSession: ScraperSession = {
    cookies: [{ name: 'PHPSESSID', value: 'sess_challenger_test_999' }],
    csrfToken: 'csrf_challenger_token_abc',
  };

  const sampleHtmlTable = `
    <html>
      <body>
        <table class="table table-bordered">
          <thead>
            <tr>
              <th>Course Code</th>
              <th>Course Title</th>
              <th>Internal 1</th>
              <th>Internal 2</th>
              <th>Assignment</th>
              <th>Total Marks</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>25CS1302E</td>
              <td>Operating Systems</td>
              <td>22</td>
              <td>24</td>
              <td>10</td>
              <td>56</td>
            </tr>
            <tr>
              <td>23CS2101R</td>
              <td>Data Structures & Algorithms</td>
              <td>20</td>
              <td>23</td>
              <td>9</td>
              <td>52</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
  `;

  test('fetchMarksData sends both DynamicModel[semester] and DynamicModel[semesterid]', async () => {
    const originalFetch = globalThis.fetch;
    let capturedUrl = '';
    const capturedBodies: URLSearchParams[] = [];

    try {
      globalThis.fetch = async (
        input: RequestInfo | URL,
        init?: RequestInit
      ) => {
        capturedUrl = input.toString();
        if (init?.body instanceof URLSearchParams) {
          capturedBodies.push(init.body);
        } else if (typeof init?.body === 'string') {
          capturedBodies.push(new URLSearchParams(init.body));
        }

        return new Response(sampleHtmlTable, {
          status: 200,
          headers: { 'Content-Type': 'text/html; charset=UTF-8' },
        });
      };

      const result = await fetchMarksData(
        testSession,
        'csrf_test_val_123',
        '2025-2026',
        '2'
      );

      assert.strictEqual(result.success, true);
      assert.strictEqual(Array.isArray(result.data), true);
      assert.strictEqual(result.data.length, 2);
      assert.strictEqual(result.data[0]['Course Code'], '25CS1302E');
      assert.strictEqual(result.data[0]['Total Marks'], '56');

      assert.strictEqual(capturedUrl, ERP_ENDPOINTS['marks']);
      const capturedBody = capturedBodies[0];
      assert.ok(capturedBody !== undefined, 'Body must be captured');

      // Assert parameter binding
      assert.strictEqual(capturedBody.get('_csrf'), 'csrf_test_val_123');
      assert.strictEqual(
        capturedBody.get('DynamicModel[academicyear]'),
        '2025-2026'
      );
      assert.strictEqual(capturedBody.get('DynamicModel[semester]'), '2');
      assert.strictEqual(capturedBody.get('DynamicModel[semesterid]'), '2');

      // Assert uniqueness / exact count of keys
      assert.strictEqual(
        capturedBody.getAll('DynamicModel[semester]').length,
        1
      );
      assert.strictEqual(
        capturedBody.getAll('DynamicModel[semesterid]').length,
        1
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('fetchEndExamResults sends both DynamicModel[semester] and DynamicModel[semesterid]', async () => {
    const originalFetch = globalThis.fetch;
    let capturedUrl = '';
    const capturedBodies: URLSearchParams[] = [];

    try {
      globalThis.fetch = async (
        input: RequestInfo | URL,
        init?: RequestInit
      ) => {
        capturedUrl = input.toString();
        if (init?.body instanceof URLSearchParams) {
          capturedBodies.push(init.body);
        } else if (typeof init?.body === 'string') {
          capturedBodies.push(new URLSearchParams(init.body));
        }

        return new Response(sampleHtmlTable, {
          status: 200,
          headers: { 'Content-Type': 'text/html; charset=UTF-8' },
        });
      };

      const result = await fetchEndExamResults(
        testSession,
        'csrf_end_exam_token',
        '2024-2025',
        'EVEN'
      );

      assert.strictEqual(result.success, true);
      assert.strictEqual(capturedUrl, ERP_ENDPOINTS['end-exam']);
      const capturedBody = capturedBodies[0];
      assert.ok(capturedBody !== undefined);

      assert.strictEqual(capturedBody.get('_csrf'), 'csrf_end_exam_token');
      assert.strictEqual(
        capturedBody.get('DynamicModel[academicyear]'),
        '2024-2025'
      );
      assert.strictEqual(capturedBody.get('DynamicModel[semester]'), 'EVEN');
      assert.strictEqual(capturedBody.get('DynamicModel[semesterid]'), 'EVEN');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('fetchCGPAData handles full parameters and dual binding in POST strategy', async () => {
    const originalFetch = globalThis.fetch;
    const capturedBodies: URLSearchParams[] = [];

    try {
      globalThis.fetch = async (
        _input: RequestInfo | URL,
        init?: RequestInit
      ) => {
        if (init?.body instanceof URLSearchParams) {
          capturedBodies.push(init.body);
        } else if (typeof init?.body === 'string') {
          capturedBodies.push(new URLSearchParams(init.body));
        }

        const cgpaHtml = `
          <table>
            <thead><tr><th>Semester</th><th>SGPA</th><th>CGPA</th></tr></thead>
            <tbody><tr><td>1</td><td>9.20</td><td>9.20</td></tr></tbody>
          </table>
        `;
        return new Response(cgpaHtml, { status: 200 });
      };

      const result = await fetchCGPAData(
        testSession,
        'csrf_cgpa_tok',
        '2025-2026',
        '1'
      );

      assert.strictEqual(result.success, true);
      const capturedBody = capturedBodies[0];
      assert.ok(capturedBody !== undefined);
      assert.strictEqual(capturedBody.get('_csrf'), 'csrf_cgpa_tok');
      assert.strictEqual(
        capturedBody.get('DynamicModel[academicyear]'),
        '2025-2026'
      );
      assert.strictEqual(capturedBody.get('DynamicModel[semester]'), '1');
      assert.strictEqual(capturedBody.get('DynamicModel[semesterid]'), '1');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('fetchCGPAData handles empty optional parameters gracefully without undefined strings', async () => {
    const originalFetch = globalThis.fetch;
    const capturedBodies: URLSearchParams[] = [];
    let getCalled = false;

    try {
      globalThis.fetch = async (
        _input: RequestInfo | URL,
        init?: RequestInit
      ) => {
        if (init?.method === 'POST') {
          if (init.body instanceof URLSearchParams) {
            capturedBodies.push(init.body);
          }
          // Simulate POST returning empty or not-found table to trigger Strategy 2 (GET)
          return new Response('<div>No records</div>', { status: 200 });
        }

        if (init?.method === 'GET') {
          getCalled = true;
          const cgpaHtml = `
            <table>
              <thead><tr><th>Semester</th><th>CGPA</th></tr></thead>
              <tbody><tr><td>All</td><td>8.95</td></tr></tbody>
            </table>
          `;
          return new Response(cgpaHtml, { status: 200 });
        }

        return new Response('', { status: 404 });
      };

      const result = await fetchCGPAData(testSession);

      assert.strictEqual(result.success, true);
      assert.strictEqual(getCalled, true, 'Should fallback to GET strategy');
      const capturedBody = capturedBodies[0];
      assert.ok(capturedBody !== undefined);
      assert.strictEqual(capturedBody.has('_csrf'), false);
      assert.strictEqual(capturedBody.has('DynamicModel[academicyear]'), false);
      assert.strictEqual(capturedBody.has('DynamicModel[semester]'), false);
      assert.strictEqual(capturedBody.has('DynamicModel[semesterid]'), false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('Stress test: Special characters and Unicode in semester & academic year', async () => {
    const originalFetch = globalThis.fetch;
    const capturedBodies: URLSearchParams[] = [];

    try {
      globalThis.fetch = async (
        _input: RequestInfo | URL,
        init?: RequestInit
      ) => {
        if (init?.body instanceof URLSearchParams) {
          capturedBodies.push(init.body);
        } else if (typeof init?.body === 'string') {
          capturedBodies.push(new URLSearchParams(init.body));
        }
        return new Response(sampleHtmlTable, { status: 200 });
      };

      const complexYear = '2025/2026 (Spl)';
      const complexSem = 'SEM-1 & 2 [Odd/Even] #100%';
      const complexCsrf = 'csrf+token/with=equals&amp';

      await fetchMarksData(testSession, complexCsrf, complexYear, complexSem);

      const capturedBody = capturedBodies[0];
      assert.ok(capturedBody !== undefined);
      assert.strictEqual(capturedBody.get('_csrf'), complexCsrf);
      assert.strictEqual(
        capturedBody.get('DynamicModel[academicyear]'),
        complexYear
      );
      assert.strictEqual(
        capturedBody.get('DynamicModel[semester]'),
        complexSem
      );
      assert.strictEqual(
        capturedBody.get('DynamicModel[semesterid]'),
        complexSem
      );

      // Verify that URLSearchParams.toString() correctly encodes and reconstructs without corruption
      const serialized = capturedBody.toString();
      const reconstructed = new URLSearchParams(serialized);
      assert.strictEqual(reconstructed.get('_csrf'), complexCsrf);
      assert.strictEqual(
        reconstructed.get('DynamicModel[academicyear]'),
        complexYear
      );
      assert.strictEqual(
        reconstructed.get('DynamicModel[semester]'),
        complexSem
      );
      assert.strictEqual(
        reconstructed.get('DynamicModel[semesterid]'),
        complexSem
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('fetchMarksData and fetchEndExamResults throw on session expiration (id="login-form")', async () => {
    const originalFetch = globalThis.fetch;
    const loginHtml = `<html><body><form id="login-form"></form></body></html>`;

    try {
      globalThis.fetch = async () => new Response(loginHtml, { status: 200 });

      await assert.rejects(
        () => fetchMarksData(testSession, 'csrf', '2025-26', '1'),
        { message: 'Session expired or invalid ERP route.' }
      );

      await assert.rejects(
        () => fetchEndExamResults(testSession, 'csrf', '2025-26', '1'),
        { message: 'Session expired or invalid ERP route.' }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('Downstream AI Executor integration: executeGetMarks & executeTool getMarks', async () => {
    // 1. Demo Mode
    const demoResult = await executeGetMarks({}, { isDemo: true });
    assert.strictEqual(demoResult.success, true);
    assert.strictEqual(demoResult.marks.length, DEMO_MARKS.length);

    // 2. Dispatcher executeTool getMarks
    const toolExec = await executeTool('getMarks', {}, { isDemo: true });
    assert.strictEqual(toolExec.success, true);
    assert.strictEqual(toolExec.tool, 'getMarks');
    const toolRes = toolExec.result as { marks: unknown[] };
    assert.ok(Array.isArray(toolRes.marks));

    // 3. AI Chat Offline Matcher for Marks
    const aiChatRes = await processAIChat([
      {
        role: 'user',
        content: 'What are my internal marks in Operating Systems?',
      },
    ]);
    assert.ok(aiChatRes.assistantResponseText.length > 0);
    assert.ok(
      aiChatRes.toolCalls.some((tc) => tc.tool === 'getMarks'),
      'AI Chat should trigger getMarks tool call'
    );
  });

  test('Downstream ERP Proxy API Route integration: /api/erp-proxy/[module]', async () => {
    // 1. POST /api/erp-proxy/marks with demo session
    const postReq = new NextRequest('http://localhost/api/erp-proxy/marks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        academicYear: '2025-2026',
        semesterId: '1',
        csrfToken: 'demo_csrf',
      }),
    });
    const postRes = await POST(postReq, {
      params: Promise.resolve({ module: 'marks' }),
    });
    assert.strictEqual(postRes.status, 200);
    const postJson = await postRes.json();
    assert.strictEqual(postJson.success, true);
    assert.ok(Array.isArray(postJson.data));

    // 2. GET /api/erp-proxy/marks with query params
    const getReq = new NextRequest(
      'http://localhost/api/erp-proxy/marks?academicYear=2025-2026&semesterId=1&csrfToken=demo_csrf',
      { method: 'GET' }
    );
    const getRes = await GET(getReq, {
      params: Promise.resolve({ module: 'marks' }),
    });
    assert.strictEqual(getRes.status, 200);
    const getJson = await getRes.json();
    assert.strictEqual(getJson.success, true);
    assert.ok(Array.isArray(getJson.data));

    // 3. Parameter alias flexibility (academic_year & semester_id)
    const aliasReq = new NextRequest(
      'http://localhost/api/erp-proxy/marks?academic_year=2025-2026&semester_id=1&_csrf=demo_csrf',
      { method: 'GET' }
    );
    const aliasRes = await GET(aliasReq, {
      params: Promise.resolve({ module: 'marks' }),
    });
    assert.strictEqual(aliasRes.status, 200);

    // 4. Missing required parameters -> 400 Bad Request
    const badReq = new NextRequest('http://localhost/api/erp-proxy/marks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csrfToken: 'demo_csrf' }),
    });
    const badRes = await POST(badReq, {
      params: Promise.resolve({ module: 'marks' }),
    });
    assert.strictEqual(badRes.status, 400);
    const badJson = await badRes.json();
    assert.strictEqual(badJson.error, 'Missing academicYear or semesterId');

    // 5. POST /api/erp-proxy/end-exam with demo session
    const endExamReq = new NextRequest(
      'http://localhost/api/erp-proxy/end-exam',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          academicYear: '2025-2026',
          semesterId: 'EVEN',
          csrfToken: 'demo_csrf',
        }),
      }
    );
    const endExamRes = await POST(endExamReq, {
      params: Promise.resolve({ module: 'end-exam' }),
    });
    // In demo session for end-exam, fetchEndExamResults is called or demo fallback handled
    assert.ok([200, 502].includes(endExamRes.status));
  });

  test('Verification: Zero ponytail debt comments in src/lib/scrapers/marks.ts', () => {
    const marksFilePath = join(
      process.cwd(),
      'src',
      'lib',
      'scrapers',
      'marks.ts'
    );
    const content = readFileSync(marksFilePath, 'utf-8');
    const ponytailDebtPattern = /(#|\/\/)\s*ponytail:/i;
    assert.strictEqual(
      ponytailDebtPattern.test(content),
      false,
      'src/lib/scrapers/marks.ts must NOT contain any ponytail: comments'
    );
  });
});
