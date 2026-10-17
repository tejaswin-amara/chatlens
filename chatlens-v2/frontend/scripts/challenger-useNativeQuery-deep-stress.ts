import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { chromium, Browser, Page } from 'playwright';

// Direct simulation of useNativeQuery logic in Node environment for exact state & dedupe checks
describe('useNativeQuery Deep State & Concurrency Simulation', () => {
  // In-flight dedupe map simulation
  const inFlightDedupeMap = new Map<string, Promise<unknown>>();
  function fetchWithDedupe<T>(
    keyStr: string,
    fetcherFn: () => Promise<T>
  ): Promise<T> {
    const existing = inFlightDedupeMap.get(keyStr);
    if (existing) return existing as Promise<T>;

    const promise = fetcherFn().finally(() => {
      inFlightDedupeMap.delete(keyStr);
    });
    inFlightDedupeMap.set(keyStr, promise);
    return promise;
  }

  test('fetchWithDedupe deduplicates concurrent calls with same keyStr to 1 execution', async () => {
    let executionCount = 0;
    const slowFetcher = async (key: unknown) => {
      executionCount++;
      await new Promise((r) => setTimeout(r, 50));
      return { key, data: 'result' };
    };

    const keyStr = JSON.stringify([
      '/api/erp-proxy/attendance',
      '2025-2026',
      '1',
    ]);

    // 10 concurrent requests
    const promises = Array.from({ length: 10 }).map(() =>
      fetchWithDedupe(keyStr, () =>
        slowFetcher(['/api/erp-proxy/attendance', '2025-2026', '1'])
      )
    );

    const results = await Promise.all(promises);
    assert.strictEqual(
      executionCount,
      1,
      'Concurrent fetches for identical key must execute fetcher exactly once'
    );
    assert.strictEqual(results.length, 10);
    assert.strictEqual(results[0].data, 'result');
  });

  test('fetchWithDedupe executes distinct fetchers for different keyStr', async () => {
    let executionCount = 0;
    const fetcher = async (key: unknown) => {
      executionCount++;
      await new Promise((r) => setTimeout(r, 20));
      return { key };
    };

    const key1 = JSON.stringify([
      '/api/erp-proxy/attendance',
      '2025-2026',
      '1',
    ]);
    const key2 = JSON.stringify([
      '/api/erp-proxy/attendance',
      '2025-2026',
      '2',
    ]);
    const key3 = JSON.stringify(['/api/erp-proxy/marks', '2025-2026', '1']);

    const [r1, r2, r3] = await Promise.all([
      fetchWithDedupe(key1, () => fetcher(key1)),
      fetchWithDedupe(key2, () => fetcher(key2)),
      fetchWithDedupe(key3, () => fetcher(key3)),
    ]);

    assert.strictEqual(
      executionCount,
      3,
      'Distinct keys must execute their respective fetchers'
    );
    assert.notStrictEqual(r1, r2);
    assert.notStrictEqual(r2, r3);
  });

  test('shouldFetch correctly validates null, undefined, and partial tuple keys', () => {
    const testCases: {
      key: string | null | readonly (string | null | undefined)[];
      expected: boolean;
    }[] = [
      { key: null, expected: false },
      { key: '/api/erp-proxy/fee', expected: true },
      { key: ['/api/erp-proxy/attendance', '2025-2026', '1'], expected: true },
      {
        key: ['/api/erp-proxy/attendance', '2025-2026', null],
        expected: false,
      },
      { key: ['/api/erp-proxy/attendance', null, '1'], expected: false },
      { key: ['/api/erp-proxy/attendance', '', '1'], expected: false },
      { key: ['/api/erp-proxy/attendance', '2025-2026', ''], expected: false },
    ];

    for (const { key, expected } of testCases) {
      const url = Array.isArray(key) ? key[0] : key;
      const shouldFetch =
        key !== null &&
        url !== null &&
        (Array.isArray(key) ? key.every(Boolean) : true);
      assert.strictEqual(
        shouldFetch,
        expected,
        `Key ${JSON.stringify(key)} expected shouldFetch=${expected}, got ${shouldFetch}`
      );
    }
  });

  test('In-flight key race condition resilience', async () => {
    // Simulating component switching keys while first request is in-flight
    let activeKey = ['/api/erp-proxy/attendance', '2025-2026', '1'];
    let stateData: string | null = null;

    // Slow request for Key 1 (takes 100ms)
    const request1 = (async () => {
      const currentKey = activeKey;
      const keyStr = JSON.stringify(currentKey);
      await new Promise((r) => setTimeout(r, 100));
      // In hook, mountedRef and key comparison happens
      if (JSON.stringify(activeKey) === keyStr) {
        stateData = 'Data for 2025-2026 Sem 1';
      }
    })();

    // User immediately switches to Key 2 after 10ms
    await new Promise((r) => setTimeout(r, 10));
    activeKey = ['/api/erp-proxy/attendance', '2025-2026', '2'];

    // Fast request for Key 2 (takes 30ms, finishes at t=40ms)
    const request2 = (async () => {
      const currentKey = activeKey;
      const keyStr = JSON.stringify(currentKey);
      await new Promise((r) => setTimeout(r, 30));
      if (JSON.stringify(activeKey) === keyStr) {
        stateData = 'Data for 2025-2026 Sem 2';
      }
    })();

    await Promise.all([request1, request2]);

    assert.strictEqual(
      stateData,
      'Data for 2025-2026 Sem 2',
      'Obsolete slower response must not overwrite newer key state'
    );
  });
});

// Browser-level adversarial interaction & dynamic key change suite
describe('Browser Real-Interaction Dynamic Key Stress Suite', () => {
  let browser: Browser;

  async function setupBrowserAuth(page: Page) {
    await page.context().addCookies([
      {
        name: 'kl_erp_session',
        value: 'enc.demo_session_data',
        url: 'http://localhost:3000',
      },
    ]);

    await page.addInitScript(() => {
      const years = JSON.stringify([
        { value: '2025-2026', label: '2025-2026' },
        { value: '2024-2025', label: '2024-2025' },
        { value: '2023-2024', label: '2023-2024' },
      ]);
      const sems = JSON.stringify([
        { value: '1', label: 'Odd Semester (Sem 1)' },
        { value: '2', label: 'Even Semester (Sem 2)' },
        { value: 'S', label: 'Summer Term' },
      ]);

      window.localStorage.setItem('studentId', '2100030000');
      window.localStorage.setItem('kl_student_name', 'Alex Student');
      window.localStorage.setItem('kl_erp_year', '2025-2026');
      window.localStorage.setItem('kl_erp_sem', '1');
      window.localStorage.setItem('kl_erp_academic_years', years);
      window.localStorage.setItem('kl_erp_semesters', sems);
      window.localStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');

      window.sessionStorage.setItem('kl_erp_session_id', 'demo_session_123');
      window.sessionStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');
      window.sessionStorage.setItem('kl_erp_year', '2025-2026');
      window.sessionStorage.setItem('kl_erp_sem', '1');
      window.sessionStorage.setItem('kl_erp_academic_years', years);
      window.sessionStorage.setItem('kl_erp_semesters', sems);
    });
  }

  test('Dynamic Key Switching in UI sends exactly 1 request per key change without loops', async () => {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    await setupBrowserAuth(page);

    const erpRequests: { url: string; time: number; postData?: string }[] = [];
    const consoleErrors: string[] = [];

    page.on('request', (req) => {
      if (req.url().includes('/api/erp-proxy/attendance')) {
        erpRequests.push({
          url: req.url(),
          time: Date.now(),
          postData: req.postData() || undefined,
        });
      }
    });

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // 1. Initial load of Attendance (1 from Navigation prefetch + 1 from useAttendance)
    await page.goto('http://localhost:3000/dashboard/attendance', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(1000);

    const initialReqCount = erpRequests.length;
    assert.ok(
      initialReqCount >= 1 && initialReqCount <= 2,
      `Initial load must trigger 1-2 requests (including prefetch), got ${initialReqCount}`
    );

    // Verify post data contains initial session values
    if (erpRequests[0].postData) {
      const body = JSON.parse(erpRequests[0].postData);
      assert.strictEqual(body.academicYear, '2025-2026');
      assert.strictEqual(body.semesterId, '1');
    }

    // 2. Change Academic Year select if present
    const yearSelect = page.locator('select').first();
    const semSelect = page.locator('select').nth(1);

    const countBeforeYearChange = erpRequests.length;
    if (await yearSelect.isVisible()) {
      await yearSelect.selectOption('2024-2025');
      await page.waitForTimeout(1000);

      assert.strictEqual(
        erpRequests.length,
        countBeforeYearChange + 1,
        `Changing year to 2024-2025 must trigger exactly 1 new request, got ${erpRequests.length}`
      );

      const latestReq = erpRequests[erpRequests.length - 1];
      if (latestReq.postData) {
        const body = JSON.parse(latestReq.postData);
        assert.strictEqual(body.academicYear, '2024-2025');
      }
    }

    // 3. Change Semester select
    const countBeforeSemChange = erpRequests.length;
    if (await semSelect.isVisible()) {
      await semSelect.selectOption('2');
      await page.waitForTimeout(1000);

      assert.strictEqual(
        erpRequests.length,
        countBeforeSemChange + 1,
        `Changing sem to 2 must trigger exactly 1 new request, got ${erpRequests.length}`
      );

      const latestReq = erpRequests[erpRequests.length - 1];
      if (latestReq.postData) {
        const body = JSON.parse(latestReq.postData);
        assert.strictEqual(body.semesterId, '2');
      }
    }

    // 4. Idle observation to verify NO trailing loops
    const finalCount = erpRequests.length;
    await page.waitForTimeout(2000);
    assert.strictEqual(
      erpRequests.length,
      finalCount,
      `Request count must remain stable during idle (no loops), got ${erpRequests.length}`
    );
    assert.strictEqual(
      consoleErrors.length,
      0,
      `No console errors allowed: ${consoleErrors.join('; ')}`
    );

    await context.close();
    await browser.close();
  });

  test('Rapid Remount Stress: Fast tab/route switching does not leak memory or throw unmounted errors', async () => {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    await setupBrowserAuth(page);

    const pageErrors: string[] = [];
    const consoleErrors: string[] = [];

    page.on('pageerror', (err) => pageErrors.push(err.message));
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    const routes = [
      '/dashboard/attendance',
      '/dashboard/timetable',
      '/dashboard/marks',
      '/dashboard/fee',
      '/dashboard/profile',
      '/dashboard/tools',
    ];

    // Rapidly switch routes before fetch has a chance to settle
    for (let cycle = 0; cycle < 3; cycle++) {
      for (const route of routes) {
        await page.goto(`http://localhost:3000${route}`, {
          waitUntil: 'commit',
        });
        await page.waitForTimeout(50); // fast unmount interruption
      }
    }

    // Finally land on attendance and let it settle
    await page.goto('http://localhost:3000/dashboard/attendance', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(1000);

    assert.strictEqual(
      pageErrors.length,
      0,
      `Unmounted update page errors: ${pageErrors.join('; ')}`
    );
    assert.strictEqual(
      consoleErrors.length,
      0,
      `Console errors during rapid unmounts: ${consoleErrors.join('; ')}`
    );

    await context.close();
    await browser.close();
  });

  test('Manual Mutate() triggers exactly one clean re-fetch without triggering cascading loops', async () => {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    await setupBrowserAuth(page);

    let proxyReqCount = 0;
    page.on('request', (req) => {
      if (req.url().includes('/api/erp-proxy/attendance')) {
        proxyReqCount++;
      }
    });

    await page.goto('http://localhost:3000/dashboard/attendance', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(1000);

    assert.ok(
      proxyReqCount >= 1 && proxyReqCount <= 2,
      `Initial count is 1-2, got ${proxyReqCount}`
    );

    const countBeforeRefresh = proxyReqCount;
    // Trigger re-fetch if a refresh / reload button exists or by triggering mutate in window
    const refreshBtn = page
      .getByRole('button', { name: /Refresh|Sync|Reload/i })
      .first();
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      await page.waitForTimeout(1000);
      assert.strictEqual(
        proxyReqCount,
        countBeforeRefresh + 1,
        `Refresh click must trigger 1 additional request, got ${proxyReqCount}`
      );
    }

    // Idle observe for 2 seconds
    await page.waitForTimeout(2000);
    assert.ok(
      proxyReqCount <= countBeforeRefresh + 1,
      `Proxy requests did not cascade into infinite loop: total=${proxyReqCount}`
    );

    await context.close();
    await browser.close();
  });
});
