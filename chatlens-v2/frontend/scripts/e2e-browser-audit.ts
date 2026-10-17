import { chromium } from 'playwright';

interface RouteAuditResult {
  route: string;
  name: string;
  status: number;
  durationMs: number;
  headingText: string;
  svgIconCount: number;
  consoleErrors: string[];
  pageErrors: string[];
  passed: boolean;
}

async function runBrowserAudit() {
  console.log('='.repeat(80));
  console.log('🌐 KL-SYNC COMPREHENSIVE BROWSER VERIFICATION & AUDIT');
  console.log('='.repeat(80));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });

  const page = await context.newPage();

  const allConsoleMessages: { type: string; text: string; route: string }[] =
    [];
  let currentRoute = '/';

  page.on('console', (msg) => {
    allConsoleMessages.push({
      type: msg.type(),
      text: msg.text(),
      route: currentRoute,
    });
  });

  page.on('pageerror', (err) => {
    allConsoleMessages.push({
      type: 'pageerror',
      text: err.message,
      route: currentRoute,
    });
  });

  page.on('request', (req) => {
    if (
      req.url().includes('/api/login') ||
      req.url().includes('/api/captcha')
    ) {
      console.log(`  [REQ ${req.method()}] ${req.url()}`, req.postData() || '');
    }
  });

  page.on('response', async (res) => {
    if (
      res.url().includes('/api/login') ||
      res.url().includes('/api/captcha')
    ) {
      let bodyText = '';
      try {
        bodyText = await res.text();
      } catch {}
      console.log(
        `  [RES ${res.status()}] ${res.url()} ->`,
        bodyText.slice(0, 120)
      );
    }
  });

  // 1. Verify Interactive Authentication Flow
  console.log('\n[PHASE 1] Interactive UI Login Verification...');
  currentRoute = '/';
  const loginStart = Date.now();

  const captchaPromise = page.waitForResponse(
    (res) => res.url().includes('/api/captcha') && res.status() === 200,
    { timeout: 15000 }
  );

  await page.goto('http://localhost:3000/');
  await captchaPromise;
  await page.waitForTimeout(400);

  console.log('  ✓ Initial /api/captcha challenge received & state settled');

  const studentIdInput = page.locator('#student-id-field');
  const passwordInput = page.locator('#password-field');
  const captchaInput = page.locator('#captcha-field');
  const submitBtn = page.locator('button[type="submit"]');

  await studentIdInput.fill('2100030000');
  await passwordInput.fill('TestPassword123');

  let visualCaptchaValue = await captchaInput.inputValue();
  if (!visualCaptchaValue) {
    await captchaInput.fill('abcd');
    visualCaptchaValue = 'abcd';
  }

  console.log(
    `  ✓ Login form filled with Student ID: 2100030000, Captcha: ${visualCaptchaValue}`
  );

  // Wait for submit button to become enabled after PoW / captcha solving
  await page.waitForFunction(
    () => {
      const btn = document.querySelector(
        'button[type="submit"]'
      ) as HTMLButtonElement | null;
      return btn !== null && !btn.disabled;
    },
    { timeout: 10000 }
  );

  // Click submit and wait for navigation
  try {
    await Promise.all([
      page.waitForURL('**/dashboard', { timeout: 10000 }),
      submitBtn.click(),
    ]);
  } catch (err) {
    const alerts = await page.locator('[role="alert"]').allTextContents();
    console.log('  ⚠️ Alerts on page:', alerts);
    const formErr = await page
      .locator('.text-destructive, .text-red-500')
      .allTextContents();
    console.log('  ⚠️ Form errors:', formErr);
    throw err;
  }

  const loginDuration = Date.now() - loginStart;
  console.log(
    `  ✓ Successfully authenticated and navigated to /dashboard in ${loginDuration}ms`
  );

  // 2. Setup standard authenticated state
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

  // 3. Navigation across ALL 11 Dashboard Routes
  console.log('\n[PHASE 2] Route-by-Route Deep Inspection...');

  const routesToTest = [
    { route: '/dashboard', name: 'Overview', heading: 'Welcome back' },
    {
      route: '/dashboard/attendance',
      name: 'Attendance',
      heading: 'Attendance',
    },
    {
      route: '/dashboard/timetable',
      name: 'Timetable Matrix',
      heading: 'Student Timetable',
    },
    {
      route: '/dashboard/marks',
      name: 'Internal Marks',
      heading: 'Marks & Grades',
    },
    {
      route: '/dashboard/profile',
      name: 'Student Profile',
      heading: 'Profile',
    },
    { route: '/dashboard/fee', name: 'Fee Details', heading: 'Fee Details' },
    {
      route: '/dashboard/tools',
      name: 'Tools & Calculators',
      heading: 'Tools & Calculators',
    },
    {
      route: '/dashboard/circulars',
      name: 'Circulars & Notices',
      heading: 'Circulars',
    },
    { route: '/dashboard/hostels', name: 'Hostel Info', heading: 'Hostel' },
    { route: '/dashboard/library', name: 'Library', heading: 'Library' },
    {
      route: '/dashboard/exam-seating',
      name: 'Exam Seating',
      heading: 'Exam Seating',
    },
  ];

  const results: RouteAuditResult[] = [];

  for (const item of routesToTest) {
    currentRoute = item.route;
    const start = Date.now();
    const routeConsoleErrors: string[] = [];
    const routePageErrors: string[] = [];

    const consoleListener = (msg: {
      type: () => string;
      text: () => string;
    }) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (!text.includes('navigator.vibrate')) {
          routeConsoleErrors.push(text);
        }
      }
    };
    const pageErrorListener = (err: Error) => {
      routePageErrors.push(err.message);
    };

    page.on('console', consoleListener);
    page.on('pageerror', pageErrorListener);

    const response = await page.goto(`http://localhost:3000${item.route}`, {
      waitUntil: 'domcontentloaded',
      timeout: 10000,
    });
    await page.waitForTimeout(400);

    const status = response ? response.status() : 200;
    const durationMs = Date.now() - start;

    // Check SVG icons rendered
    const svgCount = await page.locator('svg').count();

    // Check main heading / content
    const headingElem = page
      .locator('#main-content')
      .getByRole('heading', { level: 1 })
      .first();
    let headingFound = '';
    try {
      if (await headingElem.isVisible()) {
        headingFound = (await headingElem.textContent()) || '';
      } else {
        headingFound =
          (await page
            .getByText(new RegExp(item.heading, 'i'))
            .first()
            .textContent()) || '';
      }
    } catch {
      headingFound = 'Not Found';
    }

    const passed =
      status >= 200 &&
      status < 400 &&
      routeConsoleErrors.length === 0 &&
      routePageErrors.length === 0 &&
      svgCount > 0;

    results.push({
      route: item.route,
      name: item.name,
      status,
      durationMs,
      headingText: headingFound.trim(),
      svgIconCount: svgCount,
      consoleErrors: routeConsoleErrors,
      pageErrors: routePageErrors,
      passed,
    });

    page.off('console', consoleListener);
    page.off('pageerror', pageErrorListener);

    const statusIcon = passed ? '✓' : '✗';
    console.log(
      `  ${statusIcon} [${status}] ${item.route.padEnd(26)} | Heading: "${headingFound.trim().slice(0, 20)}" | SVGs: ${svgCount} | Time: ${durationMs}ms | Errors: ${routeConsoleErrors.length}`
    );
    if (routeConsoleErrors.length > 0) {
      console.log(`    ⚠️ Console Errors (${routeConsoleErrors.length}):`);
      routeConsoleErrors
        .slice(0, 5)
        .forEach((err) => console.log(`       - ${err}`));
    }
    if (routePageErrors.length > 0) {
      console.log(`    ⚠️ Page Errors (${routePageErrors.length}):`);
      routePageErrors
        .slice(0, 5)
        .forEach((err) => console.log(`       - ${err}`));
    }
  }

  await browser.close();

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('AUDIT SUMMARY');
  console.log('='.repeat(80));
  const allPassed = results.every((r) => r.passed);
  const totalDuration = results.reduce((acc, r) => acc + r.durationMs, 0);

  console.log(`Total Routes Verified : ${results.length}`);
  console.log(
    `Passed Routes         : ${results.filter((r) => r.passed).length}`
  );
  console.log(
    `Failed Routes         : ${results.filter((r) => !r.passed).length}`
  );
  console.log(`Total Navigation Time : ${totalDuration}ms`);
  console.log(
    `Overall Result        : ${allPassed ? '🎉 100% PASSED' : '❌ FAILED'}`
  );

  if (!allPassed) {
    process.exit(1);
  }
}

runBrowserAudit().catch((err) => {
  console.error('Fatal audit error:', err);
  process.exit(1);
});
