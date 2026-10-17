import { chromium } from 'playwright';

async function reproduce() {
  console.log('='.repeat(80));
  console.log(
    '🔍 EMPIRICAL REPRODUCTION: useNativeQuery Infinite Request Loop'
  );
  console.log('='.repeat(80));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Auth setup
  await page.context().addCookies([
    {
      name: 'kl_erp_session',
      value:
        'b64.eyJjb29raWVzIjpbIHsgIm5hbWUiOiAiUEhQU0VTU0lEIiwgInZhbHVlIjogImRlbW9fcGhwc2Vzc2lkXzEyMyIgfSBdLCAiY3NyZlRva2VuIjogImRlbW9fY3NyZlRva2VuXzEyMyIsICJ1c2VyQWdlbnQiOiAiTW96aWxsYS81LjAiIH0=',
      url: 'http://localhost:3000',
    },
  ]);

  await page.addInitScript(() => {
    window.localStorage.setItem('studentId', '2100030000');
    window.localStorage.setItem('kl_student_name', 'Alex Student');
    window.localStorage.setItem('kl_erp_year', '2025-2026');
    window.localStorage.setItem('kl_erp_sem', '1');
    window.localStorage.setItem(
      'kl_erp_academic_years',
      JSON.stringify([{ value: '2025-2026', label: '2025-2026' }])
    );
    window.localStorage.setItem(
      'kl_erp_semesters',
      JSON.stringify([{ value: '1', label: 'Odd Semester' }])
    );
    window.localStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');
    window.sessionStorage.setItem('kl_erp_session_id', 'demo_session_123');
    window.sessionStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');
    window.sessionStorage.setItem('kl_erp_year', '2025-2026');
    window.sessionStorage.setItem('kl_erp_sem', '1');
    window.sessionStorage.setItem(
      'kl_erp_academic_years',
      JSON.stringify([{ value: '2025-2026', label: '2025-2026' }])
    );
    window.sessionStorage.setItem(
      'kl_erp_semesters',
      JSON.stringify([{ value: '1', label: 'Odd Semester' }])
    );
  });

  let requestCount = 0;
  const requests: { url: string; time: number }[] = [];
  const start = Date.now();

  page.on('request', (req) => {
    if (req.url().includes('/api/erp-proxy/')) {
      requestCount++;
      requests.push({ url: req.url(), time: Date.now() - start });
    }
  });

  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  console.log('Navigating to http://localhost:3000/dashboard/attendance...');
  await page.goto('http://localhost:3000/dashboard/attendance', {
    waitUntil: 'domcontentloaded',
  });

  // Observe for 3 seconds
  console.log('Observing network requests over 3000ms window...');
  await page.waitForTimeout(3000);

  await browser.close();

  console.log(`\nResults:`);
  console.log(
    `Total /api/erp-proxy/ requests intercepted in 3s: ${requestCount}`
  );
  console.log(`Console errors captured: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log(`Sample console error:`, consoleErrors[0]);
  }
  if (requestCount > 5) {
    console.log(
      `\n❌ CONFIRMED BUG: Page generated ${requestCount} network requests in 3 seconds (expected 1 request).`
    );
  } else {
    console.log(`\n✓ Normal behavior: ${requestCount} requests.`);
  }
}

reproduce().catch((err) => {
  console.error('Reproduction harness failure:', err);
  process.exit(1);
});
