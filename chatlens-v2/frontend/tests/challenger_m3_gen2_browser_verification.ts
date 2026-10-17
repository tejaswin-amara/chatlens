import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { chromium, Browser, Page } from 'playwright';
import {
  decodeSession,
  encodeSession,
  isDemoSession,
} from '../src/lib/session';
import { DEMO_SESSION } from '../src/lib/fixtures';

describe('Milestone 3 Empirical Challenger 2 Verification Suite', () => {
  let browser: Browser;

  before(async () => {
    browser = await chromium.launch({ headless: true });
  });

  after(async () => {
    if (browser) await browser.close();
  });

  describe('1. Route Guard & Middleware Security', () => {
    test('Unauthenticated access to /dashboard redirects to login page (/)', async () => {
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await page.goto('http://localhost:3000/dashboard');
        await page.waitForURL('http://localhost:3000/');
        assert.strictEqual(new URL(page.url()).pathname, '/');
      } finally {
        await context.close();
      }
    });

    test('Unauthenticated access to /dashboard/attendance redirects to /', async () => {
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await page.goto('http://localhost:3000/dashboard/attendance');
        await page.waitForURL('http://localhost:3000/');
        assert.strictEqual(new URL(page.url()).pathname, '/');
      } finally {
        await context.close();
      }
    });

    test('Unauthenticated access to /dashboard/marks redirects to /', async () => {
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await page.goto('http://localhost:3000/dashboard/marks');
        await page.waitForURL('http://localhost:3000/');
        assert.strictEqual(new URL(page.url()).pathname, '/');
      } finally {
        await context.close();
      }
    });
  });

  describe('2. SSRF & Path Traversal Deep Security Probe (/api/fetch-photo)', () => {
    test('Rejects request without session with 401 Unauthorized', async () => {
      const res = await fetch(
        'http://localhost:3000/api/fetch-photo?id=2100030000'
      );
      assert.strictEqual(res.status, 401);
    });

    test('Rejects path traversal via relative dots in id', async () => {
      const demoToken = await encodeSession(DEMO_SESSION);
      const res = await fetch(
        'http://localhost:3000/api/fetch-photo?id=../../etc/passwd',
        {
          headers: { Cookie: `kl_erp_session=${demoToken}` },
        }
      );
      assert.strictEqual(res.status, 400);
    });

    test('Rejects arbitrary absolute URL in path (SSRF prevention)', async () => {
      const demoToken = await encodeSession(DEMO_SESSION);
      const res = await fetch(
        'http://localhost:3000/api/fetch-photo?path=https://attacker.com/evil.jpg',
        {
          headers: { Cookie: `kl_erp_session=${demoToken}` },
        }
      );
      assert.strictEqual(res.status, 400);
    });

    test('Rejects path traversal via %2e encoded dots in path', async () => {
      const demoToken = await encodeSession(DEMO_SESSION);
      const res = await fetch(
        'http://localhost:3000/api/fetch-photo?path=/uploads/%2e%2e/etc/passwd',
        {
          headers: { Cookie: `kl_erp_session=${demoToken}` },
        }
      );
      assert.strictEqual(res.status, 400);
    });

    test('Rejects protocol-relative path (//169.254.169.254/secret)', async () => {
      const demoToken = await encodeSession(DEMO_SESSION);
      const res = await fetch(
        'http://localhost:3000/api/fetch-photo?path=//169.254.169.254/latest/meta-data',
        {
          headers: { Cookie: `kl_erp_session=${demoToken}` },
        }
      );
      assert.strictEqual(res.status, 400);
    });

    test('Returns SVG dummy photo for demo session', async () => {
      const demoToken = await encodeSession(DEMO_SESSION);
      const res = await fetch(
        'http://localhost:3000/api/fetch-photo?id=2100030000',
        {
          headers: { Cookie: `kl_erp_session=${demoToken}` },
        }
      );
      assert.strictEqual(res.status, 200);
      assert.ok(res.headers.get('content-type')?.includes('image/svg+xml'));
      const text = await res.text();
      assert.ok(text.includes('<svg'));
    });
  });

  describe('3. Browser Navigation & Non-Existent Routes Stress Test', () => {
    async function setupAuthenticatedPage(page: Page) {
      await page.context().addCookies([
        {
          name: 'kl_erp_session',
          value:
            'b64.eyJjb29raWVzIjpbIHsgIm5hbWUiOiAiUEhQU0VTU0lEIiwgInZhbHVlIjogImRlbW9fcGhwc2Vzc2lkXzEyMyIgfSBdLCAiY3NyZlRva2VuIjogImRlbW9fY3NyZlRva2VuXzEyMyIsICJ1c2VyQWdlbnQiOiAiTW96aWxsYS81LjAiIH0=',
          url: 'http://localhost:3000',
        },
      ]);

      await page.addInitScript(() => {
        const years = JSON.stringify([
          { value: '2025-2026', label: '2025-2026' },
        ]);
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
        window.sessionStorage.setItem(
          'kl_erp_csrf_token',
          'demo_csrf_token_123'
        );
        window.sessionStorage.setItem('kl_erp_year', '2025-2026');
        window.sessionStorage.setItem('kl_erp_sem', '1');
        window.sessionStorage.setItem('kl_erp_academic_years', years);
        window.sessionStorage.setItem('kl_erp_semesters', sems);
        window.sessionStorage.setItem('kl_timetable_2025-2026_1', ttMock);
      });
    }

    test('Navigates sequentially across all valid dashboard routes with 0 console errors', async () => {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
      });
      const page = await context.newPage();
      const consoleErrors: string[] = [];
      const pageErrors: string[] = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });
      page.on('pageerror', (err) => {
        pageErrors.push(err.message);
      });

      await setupAuthenticatedPage(page);

      const routes = [
        '/dashboard',
        '/dashboard/attendance',
        '/dashboard/timetable',
        '/dashboard/marks',
        '/dashboard/profile',
        '/dashboard/fee',
        '/dashboard/tools',
        '/dashboard/circulars',
        '/dashboard/hostels',
        '/dashboard/library',
        '/dashboard/exam-seating',
      ];

      for (const route of routes) {
        const res = await page.goto(`http://localhost:3000${route}`, {
          waitUntil: 'domcontentloaded',
        });
        assert.ok(
          res && res.status() < 400,
          `Route ${route} returned status ${res?.status()}`
        );
        await page.waitForTimeout(150);
        const svgCount = await page.locator('svg').count();
        assert.ok(svgCount > 0, `Expected SVGs on ${route}, found 0`);
      }

      assert.strictEqual(
        consoleErrors.length,
        0,
        `Console errors logged: ${consoleErrors.join(', ')}`
      );
      assert.strictEqual(
        pageErrors.length,
        0,
        `Page errors logged: ${pageErrors.join(', ')}`
      );

      await context.close();
    });

    test('Handles unmapped routes (/dashboard/analytics & /dashboard/courses) gracefully with 404', async () => {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
      });
      const page = await context.newPage();
      const pageErrors: string[] = [];

      page.on('pageerror', (err) => {
        pageErrors.push(err.message);
      });

      await setupAuthenticatedPage(page);

      // Navigate to /dashboard/analytics
      const res1 = await page.goto(
        'http://localhost:3000/dashboard/analytics',
        { waitUntil: 'domcontentloaded' }
      );
      assert.ok(res1 !== null);
      assert.strictEqual(res1.status(), 404);

      // Navigate to /dashboard/courses
      const res2 = await page.goto('http://localhost:3000/dashboard/courses', {
        waitUntil: 'domcontentloaded',
      });
      assert.ok(res2 !== null);
      assert.strictEqual(res2.status(), 404);

      assert.strictEqual(
        pageErrors.length,
        0,
        `Unhandled exceptions on 404 routes: ${pageErrors.join(', ')}`
      );

      await context.close();
    });
  });

  describe('4. Session Cryptography & Resilience', () => {
    test('Roundtrips session encryption with AES-256-GCM', async () => {
      const token = await encodeSession(DEMO_SESSION);
      assert.ok(token.startsWith('enc.') || token.startsWith('b64.'));
      const decoded = await decodeSession(token);
      assert.deepStrictEqual(decoded.cookies, DEMO_SESSION.cookies);
      assert.strictEqual(decoded.csrfToken, DEMO_SESSION.csrfToken);
    });

    test('Gracefully falls back to demo session on tampered ciphertext', async () => {
      const tampered = 'enc.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
      const decoded = await decodeSession(tampered);
      assert.ok(decoded !== null);
      assert.ok(isDemoSession(decoded));
    });
  });
});
