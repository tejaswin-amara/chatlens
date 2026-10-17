import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { fetchMarksData, fetchEndExamResults, fetchCGPAData } from './marks';
import { ERP_ENDPOINTS, ERP_URL, ScraperSession } from './http-jar';

describe('Marks Scraper Parameter Serialization & Dual Binding Suite', () => {
  const sampleSession: ScraperSession = {
    cookies: [
      { name: 'PHPSESSID', value: 'mock_sess_abc123' },
      { name: 'kl_token', value: 'mock_token_xyz789' },
    ],
    csrfToken: 'initial_csrf_token_123',
    userAgent: 'MockUserAgent/1.0',
  };

  const sampleHtmlTable = `
    <table class="table">
      <thead>
        <tr>
          <th>Course Code</th>
          <th>Course Title</th>
          <th>Component</th>
          <th>Marks</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>25CS1302E</td>
          <td>Database Management Systems</td>
          <td>In-Sem-1</td>
          <td>24.5</td>
        </tr>
      </tbody>
    </table>
  `;

  it('fetchMarksData serializes both DynamicModel[semester] and DynamicModel[semesterid] in POST body', async () => {
    let capturedUrl = '';
    let capturedMethod = '';
    let capturedHeaders: Record<string, string> = {};
    let capturedBody: string = '';

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      capturedMethod = init?.method || 'GET';
      capturedHeaders = (init?.headers as Record<string, string>) || {};
      if (init?.body instanceof URLSearchParams) {
        capturedBody = init.body.toString();
      } else if (typeof init?.body === 'string') {
        capturedBody = init.body;
      }
      return new Response(sampleHtmlTable, {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      });
    };

    try {
      const res = await fetchMarksData(
        sampleSession,
        'csrf_test_token_999',
        '2024-2025',
        '2'
      );

      assert.strictEqual(res.success, true);
      assert.strictEqual(capturedUrl, ERP_ENDPOINTS['marks']);
      assert.strictEqual(capturedMethod, 'POST');
      assert.strictEqual(
        capturedHeaders['Content-Type'],
        'application/x-www-form-urlencoded; charset=UTF-8'
      );
      assert.strictEqual(capturedHeaders['X-Requested-With'], 'XMLHttpRequest');
      assert.strictEqual(capturedHeaders['Origin'], ERP_URL);

      // Verify deserialization from URLSearchParams standard representation
      const parsedBody = new URLSearchParams(capturedBody);
      assert.strictEqual(parsedBody.get('_csrf'), 'csrf_test_token_999');
      assert.strictEqual(
        parsedBody.get('DynamicModel[academicyear]'),
        '2024-2025'
      );
      assert.strictEqual(parsedBody.get('DynamicModel[semester]'), '2');
      assert.strictEqual(parsedBody.get('DynamicModel[semesterid]'), '2');

      // Verify raw percent-encoded wire payload representation
      assert.ok(
        capturedBody.includes('DynamicModel%5Bsemester%5D=2'),
        'Wire payload must contain percent-encoded DynamicModel[semester]'
      );
      assert.ok(
        capturedBody.includes('DynamicModel%5Bsemesterid%5D=2'),
        'Wire payload must contain percent-encoded DynamicModel[semesterid]'
      );
      assert.ok(
        capturedBody.includes('DynamicModel%5Bacademicyear%5D=2024-2025'),
        'Wire payload must contain percent-encoded DynamicModel[academicyear]'
      );

      // Verify parsed data table content
      assert.strictEqual(res.data.length, 1);
      assert.strictEqual(res.data[0]['Course Code'], '25CS1302E');
      assert.strictEqual(res.data[0]['Marks'], '24.5');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('fetchEndExamResults serializes both DynamicModel[semester] and DynamicModel[semesterid]', async () => {
    let capturedUrl = '';
    let capturedMethod = '';
    let capturedBody = '';

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      capturedMethod = init?.method || 'GET';
      if (init?.body instanceof URLSearchParams) {
        capturedBody = init.body.toString();
      }
      return new Response(sampleHtmlTable, {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      });
    };

    try {
      const res = await fetchEndExamResults(
        sampleSession,
        'csrf_end_exam_token',
        '2023-2024',
        'ODD_SEM_1'
      );

      assert.strictEqual(res.success, true);
      assert.strictEqual(capturedUrl, ERP_ENDPOINTS['end-exam']);
      assert.strictEqual(capturedMethod, 'POST');

      const parsedBody = new URLSearchParams(capturedBody);
      assert.strictEqual(parsedBody.get('_csrf'), 'csrf_end_exam_token');
      assert.strictEqual(
        parsedBody.get('DynamicModel[academicyear]'),
        '2023-2024'
      );
      assert.strictEqual(parsedBody.get('DynamicModel[semester]'), 'ODD_SEM_1');
      assert.strictEqual(
        parsedBody.get('DynamicModel[semesterid]'),
        'ODD_SEM_1'
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('fetchCGPAData handles full parameter payload with dual semester binding', async () => {
    let capturedBody = '';
    let capturedUrl = '';

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      if (init?.body instanceof URLSearchParams) {
        capturedBody = init.body.toString();
      }
      return new Response(sampleHtmlTable, {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      });
    };

    try {
      const res = await fetchCGPAData(
        sampleSession,
        'csrf_cgpa_tok',
        '2024-2025',
        'SEM_2'
      );

      assert.strictEqual(res.success, true);
      assert.strictEqual(capturedUrl, ERP_ENDPOINTS['cgpa']);

      const parsedBody = new URLSearchParams(capturedBody);
      assert.strictEqual(parsedBody.get('_csrf'), 'csrf_cgpa_tok');
      assert.strictEqual(
        parsedBody.get('DynamicModel[academicyear]'),
        '2024-2025'
      );
      assert.strictEqual(parsedBody.get('DynamicModel[semester]'), 'SEM_2');
      assert.strictEqual(parsedBody.get('DynamicModel[semesterid]'), 'SEM_2');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('fetchCGPAData gracefully handles omitted/undefined parameters without dangling keys', async () => {
    let capturedBody = '';

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (
      _input: RequestInfo | URL,
      init?: RequestInit
    ) => {
      if (init?.body instanceof URLSearchParams) {
        capturedBody = init.body.toString();
      }
      return new Response(sampleHtmlTable, {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      });
    };

    try {
      // Call with no optional params
      await fetchCGPAData(sampleSession);
      assert.strictEqual(
        capturedBody,
        '',
        'Empty body when no parameters provided'
      );

      // Call with only csrfToken
      await fetchCGPAData(sampleSession, 'only_csrf');
      assert.strictEqual(capturedBody, '_csrf=only_csrf');

      // Call with only semesterId
      await fetchCGPAData(sampleSession, undefined, undefined, 'sem_only_3');
      const parsedBody = new URLSearchParams(capturedBody);
      assert.strictEqual(parsedBody.get('_csrf'), null);
      assert.strictEqual(parsedBody.get('DynamicModel[academicyear]'), null);
      assert.strictEqual(
        parsedBody.get('DynamicModel[semester]'),
        'sem_only_3'
      );
      assert.strictEqual(
        parsedBody.get('DynamicModel[semesterid]'),
        'sem_only_3'
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('fetchCGPAData falls back from failed POST to GET strategy', async () => {
    const fetchCalls: { url: string; method: string }[] = [];

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method || 'GET';
      fetchCalls.push({ url, method });

      if (method === 'POST') {
        // Simulate POST failure or empty table
        return new Response('<div>No data available</div>', { status: 200 });
      } else {
        // Simulate GET strategy success
        return new Response(sampleHtmlTable, { status: 200 });
      }
    };

    try {
      const res = await fetchCGPAData(
        sampleSession,
        'csrf_fallback',
        '2024-2025',
        '1'
      );
      assert.strictEqual(res.success, true);
      assert.strictEqual(fetchCalls.length, 2);
      assert.strictEqual(fetchCalls[0].method, 'POST');
      assert.strictEqual(fetchCalls[1].method, 'GET');
      assert.strictEqual(res.data.length, 1);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('handles adversarial edge-case parameter values (special characters, spaces, punctuation)', async () => {
    let capturedBody = '';

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (
      _input: RequestInfo | URL,
      init?: RequestInit
    ) => {
      if (init?.body instanceof URLSearchParams) {
        capturedBody = init.body.toString();
      }
      return new Response(sampleHtmlTable, { status: 200 });
    };

    try {
      const specialCsrf = 'csrf+token/with=special&chars==';
      const specialYear = '2024-2025 (Special / Fast-Track & Honors)';
      const specialSem = 'SEM [1] & {2} = TEST #42';

      await fetchMarksData(sampleSession, specialCsrf, specialYear, specialSem);

      const parsed = new URLSearchParams(capturedBody);
      assert.strictEqual(parsed.get('_csrf'), specialCsrf);
      assert.strictEqual(parsed.get('DynamicModel[academicyear]'), specialYear);
      assert.strictEqual(parsed.get('DynamicModel[semester]'), specialSem);
      assert.strictEqual(parsed.get('DynamicModel[semesterid]'), specialSem);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('handles empty string parameter values correctly', async () => {
    let capturedBody = '';

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (
      _input: RequestInfo | URL,
      init?: RequestInit
    ) => {
      if (init?.body instanceof URLSearchParams) {
        capturedBody = init.body.toString();
      }
      return new Response(sampleHtmlTable, { status: 200 });
    };

    try {
      await fetchMarksData(sampleSession, '', '', '');

      const parsed = new URLSearchParams(capturedBody);
      assert.strictEqual(parsed.get('_csrf'), '');
      assert.strictEqual(parsed.get('DynamicModel[academicyear]'), '');
      assert.strictEqual(parsed.get('DynamicModel[semester]'), '');
      assert.strictEqual(parsed.get('DynamicModel[semesterid]'), '');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('throws error when ERP returns HTTP error status', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      return new Response('Internal Server Error', { status: 500 });
    };

    try {
      await assert.rejects(
        async () => {
          await fetchMarksData(sampleSession, 'csrf', '2024-2025', '1');
        },
        {
          name: 'Error',
          message: 'ERP returned HTTP 500',
        }
      );

      await assert.rejects(
        async () => {
          await fetchEndExamResults(sampleSession, 'csrf', '2024-2025', '1');
        },
        {
          name: 'Error',
          message: 'ERP returned HTTP 500',
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('throws error when ERP returns session expired login form HTML', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      return new Response(
        '<html><body><form id="login-form">Please sign in</form></body></html>',
        { status: 200 }
      );
    };

    try {
      await assert.rejects(
        async () => {
          await fetchMarksData(sampleSession, 'csrf', '2024-2025', '1');
        },
        {
          name: 'Error',
          message: 'Session expired or invalid ERP route.',
        }
      );

      await assert.rejects(
        async () => {
          await fetchEndExamResults(sampleSession, 'csrf', '2024-2025', '1');
        },
        {
          name: 'Error',
          message: 'Session expired or invalid ERP route.',
        }
      );

      await assert.rejects(
        async () => {
          await fetchCGPAData(sampleSession, 'csrf', '2024-2025', '1');
        },
        {
          name: 'Error',
          message: 'Session expired or invalid ERP route.',
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
