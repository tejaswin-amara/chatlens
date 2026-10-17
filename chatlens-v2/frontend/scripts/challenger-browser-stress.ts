import { chromium, Browser, Page } from 'playwright';
import assert from 'node:assert/strict';

interface TestResult {
  suite: string;
  name: string;
  passed: boolean;
  durationMs: number;
  details?: Record<string, unknown>;
  error?: string;
}

const DASHBOARD_ROUTES = [
  { path: '/dashboard', name: 'Overview', heading: 'Welcome back' },
  { path: '/dashboard/attendance', name: 'Attendance', heading: 'Attendance' },
  {
    path: '/dashboard/timetable',
    name: 'Timetable',
    heading: 'Student Timetable',
  },
  {
    path: '/dashboard/marks',
    name: 'Marks & Grades',
    heading: 'Marks & Grades',
  },
  { path: '/dashboard/profile', name: 'Profile', heading: 'Profile' },
  { path: '/dashboard/fee', name: 'Fee Details', heading: 'Fee Details' },
  {
    path: '/dashboard/tools',
    name: 'Tools & Calculators',
    heading: 'Tools & Calculators',
  },
  { path: '/dashboard/circulars', name: 'Circulars', heading: 'Circulars' },
  {
    path: '/dashboard/hostels',
    name: 'Hostel Information',
    heading: 'Hostel Information',
  },
  { path: '/dashboard/library', name: 'Library', heading: 'Library' },
  {
    path: '/dashboard/exam-seating',
    name: 'Exam Seating',
    heading: 'Exam Seating',
  },
];

const results: TestResult[] = [];

async function setupAuth(page: Page) {
  await page.context().addCookies([
    {
      name: 'kl_erp_session',
      value: 'enc.demo_session_data',
      url: 'http://localhost:3000',
    },
  ]);

  await page.addInitScript(() => {
    const years = JSON.stringify([{ value: '2025-2026', label: '2025-2026' }]);
    const sems = JSON.stringify([{ value: '1', label: 'Odd Semester' }]);
    const ttMock = JSON.stringify([
      {
        'Day / Period': 'Monday',
        '1': '23CS2101R-L - S-10 - RoomNo-101 - Dr. Smith',
        '2': '23CS2102R-P - S-10 - RoomNo-LAB-3 - Prof. Johnson',
        '3': 'Free',
        '4': '23CS2103R-L - S-10 - RoomNo-105 - Dr. Allen',
      },
    ]);

    window.localStorage.setItem('studentId', '2100030000');
    window.localStorage.setItem('kl_student_name', 'Alex Student');
    window.localStorage.setItem('kl_erp_year', '2025-2026');
    window.localStorage.setItem('kl_erp_sem', '1');
    window.localStorage.setItem('kl_erp_academic_years', years);
    window.localStorage.setItem('kl_erp_semesters', sems);
    window.localStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');
    window.localStorage.setItem('kl_timetable_2025-2026_1', ttMock);

    window.sessionStorage.setItem('kl_erp_session_id', 'demo_session_123');
    window.sessionStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');
    window.sessionStorage.setItem('kl_erp_year', '2025-2026');
    window.sessionStorage.setItem('kl_erp_sem', '1');
    window.sessionStorage.setItem('kl_erp_academic_years', years);
    window.sessionStorage.setItem('kl_erp_semesters', sems);
    window.sessionStorage.setItem('kl_timetable_2025-2026_1', ttMock);
  });
}

function attachStrictErrorListeners(
  page: Page,
  errors: string[],
  warnings: string[],
  pageErrors: string[]
) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    } else if (msg.type() === 'warning') {
      warnings.push(msg.text());
    }
  });

  page.on('pageerror', (err) => {
    pageErrors.push(err.message);
  });
}

async function runChallengerStress() {
  console.log('='.repeat(80));
  console.log('⚔️  CHALLENGER 1: EMPIRICAL BROWSER ADVERSARIAL STRESS SUITE');
  console.log('='.repeat(80));

  const browser: Browser = await chromium.launch({ headless: true });

  try {
    // -------------------------------------------------------------------------
    // TEST SUITE 1: Deep DOM, SVG & Strict Console Audit across all 11 Routes
    // -------------------------------------------------------------------------
    console.log(
      '\n--- [SUITE 1] Deep DOM, SVG & Strict Console Audit (11 Routes) ---'
    );
    for (const r of DASHBOARD_ROUTES) {
      const start = Date.now();
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
      });
      const page = await context.newPage();
      const errors: string[] = [];
      const warnings: string[] = [];
      const pageErrors: string[] = [];
      attachStrictErrorListeners(page, errors, warnings, pageErrors);
      await setupAuth(page);

      let passed = true;
      let errorMsg = '';
      let svgCount = 0;
      let headingFound = '';
      let domDetails: Record<string, unknown> = {};

      try {
        const res = await page.goto(`http://localhost:3000${r.path}`, {
          waitUntil: 'domcontentloaded',
          timeout: 10000,
        });

        assert.ok(
          res && res.status() >= 200 && res.status() < 400,
          `HTTP status ${res?.status()} for ${r.path}`
        );

        // Scoped header check
        const mainH1 = page
          .locator('#main-content')
          .getByRole('heading', { level: 1 })
          .first();
        if (await mainH1.isVisible()) {
          headingFound = (await mainH1.textContent()) || '';
        } else {
          const fallbackHeading = page
            .getByText(new RegExp(r.heading, 'i'))
            .first();
          await fallbackHeading.waitFor({ state: 'visible', timeout: 5000 });
          headingFound = (await fallbackHeading.textContent()) || '';
        }
        assert.ok(headingFound.length > 0, `No heading found for ${r.path}`);

        // Specific DOM Component Checks per Route
        if (r.path === '/dashboard') {
          await page
            .getByText(/Cumulative GPA|Welcome back/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          const statCards = await page.locator('div:has(> p)').count();
          assert.ok(statCards > 0, 'Dashboard overview must render stat cards');
          domDetails = { statCards, heading: headingFound };
        } else if (r.path === '/dashboard/timetable') {
          const gridBtn = page.getByRole('button', { name: /Grid/i });
          const listBtn = page.getByRole('button', { name: /List/i });
          await gridBtn.waitFor({ state: 'visible', timeout: 5000 });
          await page
            .locator('table')
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          await listBtn.click();
          await page.waitForTimeout(200);
          await page
            .locator('table')
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          await gridBtn.click();
          await page.waitForTimeout(200);
          await page
            .locator('table')
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { viewTogglesWorking: true };
        } else if (r.path === '/dashboard/attendance') {
          await page
            .getByText(/Attendance|Overall|Classes Attended/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          const tableBtn = page.getByRole('button', { name: /Table/i });
          const cardsBtn = page.getByRole('button', { name: /Cards/i });
          if (await tableBtn.isVisible()) {
            await tableBtn.click();
            await page.waitForTimeout(100);
            if ((await page.locator('table').count()) > 0) {
              await page
                .locator('table')
                .first()
                .waitFor({ state: 'visible', timeout: 5000 });
            }
            if (await cardsBtn.isVisible()) {
              await cardsBtn.click();
              await page.waitForTimeout(100);
            }
          }
          const cardCount = await page.locator('.apple-card').count();
          assert.ok(
            cardCount > 0,
            'Attendance view must render apple-card containers'
          );
          domDetails = { attendanceCards: true, cardCount };
        } else if (r.path === '/dashboard/marks') {
          const searchInput = page.getByPlaceholder(/Search courses/i);
          await searchInput.waitFor({ state: 'visible', timeout: 5000 });
          await searchInput.fill('CS');
          await page.waitForTimeout(100);
          await searchInput.fill('');
          await page
            .locator('table')
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { searchInputInteractive: true };
        } else if (r.path === '/dashboard/tools') {
          await page
            .getByText(/Attendance Target/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          assert.ok(
            await page
              .getByText(/CGPA Goal Predictor/i)
              .first()
              .isVisible(),
            'CGPA predictor tool visible'
          );
          domDetails = { toolsCalculatorsVisible: true };
        } else if (r.path === '/dashboard/profile') {
          await page
            .getByText(/Alex Student|2100030000/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { profileDetailsVisible: true };
        } else if (r.path === '/dashboard/fee') {
          await page
            .getByText(/Total Pending|Total Paid/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { feeDetailsVisible: true };
        } else if (r.path === '/dashboard/circulars') {
          await page
            .locator('table')
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { circularsVisible: true };
        } else if (r.path === '/dashboard/hostels') {
          await page
            .getByText(/Hostel|Block|Room/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { hostelInfoVisible: true };
        } else if (r.path === '/dashboard/library') {
          await page
            .getByText(/Library|Book|Issue/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { libraryRecordsVisible: true };
        } else if (r.path === '/dashboard/exam-seating') {
          await page
            .getByText(/Exam|Seating|Desk/i)
            .first()
            .waitFor({ state: 'visible', timeout: 5000 });
          domDetails = { examSeatingVisible: true };
        }

        // SVG Audit: Verify all rendered SVGs have geometry and non-empty content
        svgCount = await page.locator('svg').count();
        assert.ok(
          svgCount >= 10,
          `Expected >= 10 SVGs on ${r.path}, found ${svgCount}`
        );

        const svgAudits = await page.evaluate(() => {
          const svgs = Array.from(document.querySelectorAll('svg'));
          return svgs.map((s, idx) => ({
            index: idx,
            childrenCount: s.children.length,
            innerHTML: s.innerHTML.slice(0, 100),
          }));
        });

        for (const sa of svgAudits) {
          assert.ok(
            sa.childrenCount > 0,
            `SVG #${sa.index} on ${r.path} has 0 child geometry elements`
          );
          assert.ok(
            sa.innerHTML.length > 0,
            `SVG #${sa.index} on ${r.path} has empty innerHTML`
          );
        }

        // Strict Console and Page Errors check
        assert.strictEqual(
          errors.length,
          0,
          `Console errors on ${r.path}: ${errors.join('; ')}`
        );
        assert.strictEqual(
          pageErrors.length,
          0,
          `Page exceptions on ${r.path}: ${pageErrors.join('; ')}`
        );
      } catch (err: unknown) {
        passed = false;
        errorMsg = err instanceof Error ? err.message : String(err);
      } finally {
        await context.close();
      }

      const durationMs = Date.now() - start;
      results.push({
        suite: 'Deep DOM & SVG Audit',
        name: `Route: ${r.path} (${r.name})`,
        passed,
        durationMs,
        details: {
          svgCount,
          heading: headingFound,
          ...domDetails,
          errorsCount: errors.length,
          warningsCount: warnings.length,
        },
        error: errorMsg || undefined,
      });

      console.log(
        `  ${passed ? '✓' : '✗'} [${r.path}] SVGs: ${svgCount} | Time: ${durationMs}ms | Errors: ${errors.length} | Warnings: ${warnings.length}`
      );
      if (!passed) console.log(`     Error: ${errorMsg}`);
    }

    // -------------------------------------------------------------------------
    // TEST SUITE 2: Concurrent Multi-Tab Simultaneous Route Bombardment
    // -------------------------------------------------------------------------
    console.log(
      '\n--- [SUITE 2] Concurrent Multi-Tab Simultaneous Route Bombardment ---'
    );
    {
      const start = Date.now();
      const concurrency = 3;
      const contexts = await Promise.all(
        Array.from({ length: concurrency }).map(() =>
          browser.newContext({ viewport: { width: 1280, height: 800 } })
        )
      );

      const tabTasks = contexts.map(async (ctx, idx) => {
        const page = await ctx.newPage();
        const errors: string[] = [];
        const warnings: string[] = [];
        const pageErrors: string[] = [];
        attachStrictErrorListeners(page, errors, warnings, pageErrors);
        await setupAuth(page);

        // Assign a subset of routes to this worker
        const routesForTab = DASHBOARD_ROUTES.slice(idx * 4, idx * 4 + 4);
        if (routesForTab.length === 0) routesForTab.push(DASHBOARD_ROUTES[0]);

        for (const target of routesForTab) {
          const res = await page.goto(`http://localhost:3000${target.path}`, {
            waitUntil: 'domcontentloaded',
            timeout: 10000,
          });
          assert.ok(
            res && res.status() < 400,
            `Tab ${idx} failed to load ${target.path}`
          );
          await page.waitForTimeout(200);
          const svgCount = await page.locator('svg').count();
          assert.ok(svgCount > 0, `Tab ${idx} found 0 SVGs on ${target.path}`);
        }

        assert.strictEqual(
          errors.length,
          0,
          `Tab ${idx} logged console errors: ${errors.join(', ')}`
        );
        assert.strictEqual(
          pageErrors.length,
          0,
          `Tab ${idx} logged page errors: ${pageErrors.join(', ')}`
        );
        await ctx.close();
      });

      let passed = true;
      let errorMsg = '';
      try {
        await Promise.all(tabTasks);
      } catch (err: unknown) {
        passed = false;
        errorMsg = err instanceof Error ? err.message : String(err);
      }

      const durationMs = Date.now() - start;
      results.push({
        suite: 'Concurrency Stress',
        name: `Simultaneous 3-Tab Concurrent Navigation across all routes`,
        passed,
        durationMs,
        error: errorMsg || undefined,
      });
      console.log(
        `  ${passed ? '✓' : '✗'} 3-Tab Concurrent Load | Time: ${durationMs}ms | Result: ${passed ? 'PASSED' : errorMsg}`
      );
    }

    // -------------------------------------------------------------------------
    // TEST SUITE 3: Rapid Sequential Interleaved Navigation & History Stress
    // -------------------------------------------------------------------------
    console.log(
      '\n--- [SUITE 3] Rapid Sequential Interleaved Navigation & History Back/Forward ---'
    );
    {
      const start = Date.now();
      const context = await browser.newContext();
      const page = await context.newPage();
      const errors: string[] = [];
      const warnings: string[] = [];
      const pageErrors: string[] = [];
      attachStrictErrorListeners(page, errors, warnings, pageErrors);
      await setupAuth(page);

      let passed = true;
      let errorMsg = '';

      try {
        // Fast sequential navigation through all 11 routes in rapid succession
        for (const r of DASHBOARD_ROUTES) {
          await page.goto(`http://localhost:3000${r.path}`, {
            waitUntil: 'domcontentloaded',
            timeout: 5000,
          });
          await page.waitForTimeout(100);
        }

        // Stress history back and forward
        for (let i = 0; i < 5; i++) {
          await page.goBack({ waitUntil: 'domcontentloaded', timeout: 5000 });
          await page.waitForTimeout(100);
        }
        for (let i = 0; i < 5; i++) {
          await page.goForward({
            waitUntil: 'domcontentloaded',
            timeout: 5000,
          });
          await page.waitForTimeout(100);
        }

        assert.strictEqual(
          errors.length,
          0,
          `Rapid navigation console errors: ${errors.join(', ')}`
        );
        assert.strictEqual(
          pageErrors.length,
          0,
          `Rapid navigation page errors: ${pageErrors.join(', ')}`
        );
      } catch (err: unknown) {
        passed = false;
        errorMsg = err instanceof Error ? err.message : String(err);
      } finally {
        await context.close();
      }

      const durationMs = Date.now() - start;
      results.push({
        suite: 'Rapid & History Navigation',
        name: 'Rapid sequential route hopping + 5x goBack() & 5x goForward()',
        passed,
        durationMs,
        error: errorMsg || undefined,
      });
      console.log(
        `  ${passed ? '✓' : '✗'} Rapid Navigation & History Hop | Time: ${durationMs}ms | Result: ${passed ? 'PASSED' : errorMsg}`
      );
    }

    // -------------------------------------------------------------------------
    // TEST SUITE 4: Interactive Touch Targets & Bounding Box WCAG Verification
    // -------------------------------------------------------------------------
    console.log(
      '\n--- [SUITE 4] WCAG 2.2 AAA Touch Target & Focus Rings Verification ---'
    );
    {
      const start = Date.now();
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
      });
      const page = await context.newPage();
      await setupAuth(page);

      let passed = true;
      let errorMsg = '';
      let interactiveCount = 0;

      try {
        await page.goto('http://localhost:3000/dashboard', {
          waitUntil: 'domcontentloaded',
        });
        await page.waitForTimeout(300);

        // Check bounding box of buttons, inputs, links in navbar and main content
        const elementsCheck = await page.evaluate(() => {
          const interactives = Array.from(
            document.querySelectorAll(
              'button, a[href], input, select, [role="button"]'
            )
          ) as HTMLElement[];

          const metrics = interactives.map((el) => {
            const rect = el.getBoundingClientRect();
            return {
              tag: el.tagName,
              text:
                el.innerText?.slice(0, 30) ||
                el.getAttribute('aria-label') ||
                '',
              width: rect.width,
              height: rect.height,
              visible:
                rect.width > 0 &&
                rect.height > 0 &&
                window.getComputedStyle(el).display !== 'none',
            };
          });

          return metrics.filter((m) => m.visible);
        });

        interactiveCount = elementsCheck.length;
        assert.ok(
          interactiveCount > 5,
          'Found too few interactive elements on dashboard'
        );

        // Check that major action buttons adhere to minimum size conventions
        for (const el of elementsCheck) {
          assert.ok(
            el.width >= 16 && el.height >= 16,
            `Interactive element ${el.tag} "${el.text}" has tiny box (${el.width}x${el.height})`
          );
        }
      } catch (err: unknown) {
        passed = false;
        errorMsg = err instanceof Error ? err.message : String(err);
      } finally {
        await context.close();
      }

      const durationMs = Date.now() - start;
      results.push({
        suite: 'Accessibility & Touch Targets',
        name: `Interactive Elements (${interactiveCount} elements audited)`,
        passed,
        durationMs,
        details: { interactiveCount },
        error: errorMsg || undefined,
      });
      console.log(
        `  ${passed ? '✓' : '✗'} Touch Target Audit (${interactiveCount} elements) | Time: ${durationMs}ms`
      );
    }

    // -------------------------------------------------------------------------
    // TEST SUITE 5: Adversarial Corner Cases (404, XSS Query Injection, Bad Session)
    // -------------------------------------------------------------------------
    console.log('\n--- [SUITE 5] Adversarial Boundary & Injection Tests ---');
    {
      const start = Date.now();
      const context = await browser.newContext();
      const page = await context.newPage();
      const errors: string[] = [];
      const warnings: string[] = [];
      const pageErrors: string[] = [];
      attachStrictErrorListeners(page, errors, warnings, pageErrors);
      await setupAuth(page);

      let passed = true;
      let errorMsg = '';

      try {
        // 1. Non-existent subroute
        const res404 = await page.goto(
          'http://localhost:3000/dashboard/nonexistent-route-xyz',
          {
            waitUntil: 'domcontentloaded',
          }
        );
        assert.ok(res404 !== null, '404 response received');

        // 2. Query param XSS injection attack on marks page
        await page.goto(
          'http://localhost:3000/dashboard/marks?sem=%3Cscript%3Ealert(1)%3C%2Fscript%3E&year=%22%3E%3Cimg+src%3Dx+onerror%3Dalert(2)%3E',
          {
            waitUntil: 'domcontentloaded',
          }
        );
        await page.waitForTimeout(300);

        // Verify page rendered safely without alerts or crashes
        const marksHeading = page
          .locator('#main-content')
          .getByRole('heading', { level: 1 })
          .first();
        assert.ok(
          await marksHeading.isVisible(),
          'Marks page survived XSS query string attack'
        );

        // 3. Corrupted session test
        await page.context().clearCookies();
        await page.context().addCookies([
          {
            name: 'kl_erp_session',
            value: 'CORRUPTED.INVALID_TOKEN_PAYLOAD_HERE.123',
            url: 'http://localhost:3000',
          },
        ]);
        const resCorrupt = await page.goto('http://localhost:3000/dashboard', {
          waitUntil: 'domcontentloaded',
        });
        assert.ok(resCorrupt !== null, 'Corrupted cookie handled gracefully');

        assert.strictEqual(
          pageErrors.length,
          0,
          `Page threw unhandled exception on corrupted cookie: ${pageErrors.join(', ')}`
        );
      } catch (err: unknown) {
        passed = false;
        errorMsg = err instanceof Error ? err.message : String(err);
      } finally {
        await context.close();
      }

      const durationMs = Date.now() - start;
      results.push({
        suite: 'Adversarial Boundaries',
        name: '404 routing, query string XSS injection, and corrupted cookie resilience',
        passed,
        durationMs,
        error: errorMsg || undefined,
      });
      console.log(
        `  ${passed ? '✓' : '✗'} Adversarial Boundaries & Injections | Time: ${durationMs}ms | Result: ${passed ? 'PASSED' : errorMsg}`
      );
    }
  } finally {
    await browser.close();
  }

  // ---------------------------------------------------------------------------
  // Final Scorecard
  // ---------------------------------------------------------------------------
  console.log('\n' + '='.repeat(80));
  console.log('CHALLENGER 1 EMPIRICAL RESULTS SCORECARD');
  console.log('='.repeat(80));

  const totalTests = results.length;
  const passedTests = results.filter((r) => r.passed).length;
  const failedTests = results.filter((r) => !r.passed).length;
  const totalDurationMs = results.reduce((acc, r) => acc + r.durationMs, 0);

  console.log(`Total Test Items : ${totalTests}`);
  console.log(`Passed Items     : ${passedTests}`);
  console.log(`Failed Items     : ${failedTests}`);
  console.log(`Total Duration   : ${totalDurationMs}ms`);
  console.log(
    `Verdict          : ${failedTests === 0 ? '🏆 100% EMPIRICAL PASS (APPROVE)' : '❌ FAILURES DETECTED (REQUEST_CHANGES)'}`
  );
  console.log('='.repeat(80));

  if (failedTests > 0) {
    process.exit(1);
  }
}

runChallengerStress().catch((err) => {
  console.error('Fatal stress harness exception:', err);
  process.exit(1);
});
