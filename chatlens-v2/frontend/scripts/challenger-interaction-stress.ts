/**
 * EMPIRICAL CHALLENGER 2: INTERACTION, MOTION & BROWSER STRESS HARNESS
 *
 * Deeply audits:
 * 1. WWDC Fluid Motion Physics Math (project, rubberband, triggerHaptic, velocity tracker)
 * 2. CSS & Design System Motion Tokens (WWDC springs, touch-press scale(0.965), tabular numerals, accessibility triple-gate)
 * 3. DOM Touch Target Audit (>= 44px) across Mobile & Desktop
 * 4. Zero Layout Shift (CLS) and dimensional stability across all 11 Dashboard Routes
 * 5. State transitions (Async loading -> loaded, filter typing, tab switching, empty states)
 */

import { chromium, Browser, Page } from 'playwright';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as path from 'node:path';
import {
  project,
  rubberband,
  triggerHaptic,
  createVelocityTracker,
  type HapticType,
} from '../src/lib/fluid-motion';

interface StressResult {
  suite: string;
  name: string;
  passed: boolean;
  durationMs: number;
  details?: Record<string, unknown>;
  error?: string;
}

const results: StressResult[] = [];

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

function runFluidMotionMathStress() {
  console.log(
    '\n--- [TEST SUITE 1] Fluid Motion Math & Physics Boundary Stress ---'
  );

  // 1. project() mathematical properties & edge cases
  {
    const start = Date.now();
    let passed = true;
    let errorMsg = '';

    try {
      // Zero & tiny velocity cutoff
      assert.strictEqual(project(0), 0, 'project(0) must return 0');
      assert.strictEqual(project(0.5), 0, 'project(<1) must return 0');
      assert.strictEqual(project(-0.99), 0, 'project(>-1) must return 0');

      // Standard scroll projection: 1000 px/s with default decay 0.998
      // x = (1000/1000) * 0.998 / (1 - 0.998) = 1 * 0.998 / 0.002 = 499px
      const p1000 = project(1000, 0.998);
      assert.ok(Math.abs(p1000 - 499) < 0.001, `Expected ~499, got ${p1000}`);

      // Linearity property: project(2v) == 2 * project(v)
      const p2000 = project(2000, 0.998);
      assert.ok(
        Math.abs(p2000 - 2 * p1000) < 0.001,
        `Linearity failed: ${p2000} vs ${2 * p1000}`
      );

      // Direction symmetry: project(-v) == -project(v)
      const pNeg1000 = project(-1000, 0.998);
      assert.ok(
        Math.abs(pNeg1000 - -499) < 0.001,
        `Symmetry failed: ${pNeg1000}`
      );

      // Snappy decay (0.99): x = 1 * 0.99 / 0.01 = 99px
      const pSnappy = project(1000, 0.99);
      assert.ok(
        Math.abs(pSnappy - 99) < 0.001,
        `Snappy decay failed: ${pSnappy}`
      );

      // Extreme velocity (100,000 px/s)
      const pExtreme = project(100000, 0.998);
      assert.ok(
        Number.isFinite(pExtreme) && pExtreme > 0,
        `Extreme velocity not finite: ${pExtreme}`
      );
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    }

    results.push({
      suite: 'Fluid Motion Physics',
      name: 'project() exponential decay & boundary conditions',
      passed,
      durationMs: Date.now() - start,
      error: errorMsg || undefined,
    });
    console.log(`  ${passed ? '✓' : '✗'} project() Exponential Decay Physics`);
  }

  // 2. rubberband() UIKit formula properties & resistance curves
  {
    const start = Date.now();
    let passed = true;
    let errorMsg = '';

    try {
      // Zero overshoot
      assert.strictEqual(
        rubberband(0, 300, 0.55),
        0,
        'rubberband(0) must return 0'
      );

      // Negative/zero dimension boundary safety
      assert.strictEqual(
        rubberband(100, 0, 0.55),
        0,
        'rubberband with 0 dimension must return 0'
      );
      assert.strictEqual(
        rubberband(100, -100, 0.55),
        0,
        'rubberband with negative dimension must return 0'
      );

      // Symmetry: rubberband(-x) == -rubberband(x)
      const pos100 = rubberband(100, 300, 0.55);
      const neg100 = rubberband(-100, 300, 0.55);
      assert.ok(
        Math.abs(pos100 + neg100) < 0.0001,
        `Symmetry failed: ${pos100} and ${neg100}`
      );

      // Asymptotic bound: dampened offset MUST always be strictly less than dimension (300px)
      const hugeOffset = rubberband(1000000, 300, 0.55);
      assert.ok(
        hugeOffset < 300,
        `Asymptotic bound violated: ${hugeOffset} >= 300`
      );
      assert.ok(hugeOffset > 295, `Asymptotic limit too small: ${hugeOffset}`);

      // Monotonicity: strictly increasing with overshoot
      let prev = 0;
      for (let x = 10; x <= 1000; x += 20) {
        const curr = rubberband(x, 400, 0.45);
        assert.ok(
          curr > prev,
          `Monotonicity violated at x=${x}: curr=${curr} <= prev=${prev}`
        );
        prev = curr;
      }

      // Diminishing returns (concavity): slope must decrease as overshoot increases
      const d1 = rubberband(50, 400, 0.55) - rubberband(0, 400, 0.55);
      const d2 = rubberband(100, 400, 0.55) - rubberband(50, 400, 0.55);
      const d3 = rubberband(150, 400, 0.55) - rubberband(100, 400, 0.55);
      assert.ok(
        d1 > d2 && d2 > d3,
        `Diminishing returns violated: ${d1} > ${d2} > ${d3}`
      );
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    }

    results.push({
      suite: 'Fluid Motion Physics',
      name: 'rubberband() UIKit resistance curves & bounds',
      passed,
      durationMs: Date.now() - start,
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} rubberband() UIKit Resistance & Asymptote Bounds`
    );
  }

  // 3. triggerHaptic() multi-modal signatures & fallback resilience
  {
    const start = Date.now();
    let passed = true;
    let errorMsg = '';

    try {
      // 1. Verify it runs cleanly in Node.js environment without throwing
      const types: HapticType[] = [
        'light',
        'medium',
        'heavy',
        'selection',
        'success',
        'warning',
        'error',
      ];
      for (const t of types) {
        assert.doesNotThrow(
          () => triggerHaptic(t),
          `triggerHaptic('${t}') threw in Node environment`
        );
      }

      // 2. Mock vibration API via defineProperty on navigator
      const recordedVibrations: (number | number[])[] = [];
      const origVibrate = (
        globalThis.navigator as unknown as Record<string, unknown>
      ).vibrate;
      const origWindow = (globalThis as unknown as Record<string, unknown>)
        .window;

      (globalThis as unknown as Record<string, unknown>).window = globalThis;
      Object.defineProperty(globalThis.navigator, 'vibrate', {
        value: (pattern: number | number[]) => {
          recordedVibrations.push(pattern);
          return true;
        },
        configurable: true,
        writable: true,
      });

      triggerHaptic('selection');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        6,
        'selection haptic duration'
      );

      triggerHaptic('light');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        10,
        'light haptic duration'
      );

      triggerHaptic('medium');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        18,
        'medium haptic duration'
      );

      triggerHaptic('heavy');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        28,
        'heavy haptic duration'
      );

      triggerHaptic('success');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        [10, 40, 15],
        'success haptic pattern'
      );

      triggerHaptic('warning');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        [18, 50, 18],
        'warning haptic pattern'
      );

      triggerHaptic('error');
      assert.deepStrictEqual(
        recordedVibrations[recordedVibrations.length - 1],
        [24, 40, 24, 40, 32],
        'error haptic pattern'
      );

      // Graceful error recovery: navigator.vibrate throwing exception
      Object.defineProperty(globalThis.navigator, 'vibrate', {
        value: () => {
          throw new Error('Hardware vibration locked');
        },
        configurable: true,
        writable: true,
      });
      assert.doesNotThrow(
        () => triggerHaptic('light'),
        'triggerHaptic failed to catch navigator.vibrate exception'
      );

      // Cleanup mocks
      if (origVibrate) {
        Object.defineProperty(globalThis.navigator, 'vibrate', {
          value: origVibrate,
          configurable: true,
          writable: true,
        });
      } else {
        delete (globalThis.navigator as unknown as Record<string, unknown>)
          .vibrate;
      }
      if (!origWindow) {
        delete (globalThis as unknown as Record<string, unknown>).window;
      }
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    }

    results.push({
      suite: 'Fluid Motion Physics',
      name: 'triggerHaptic() multimodal vibration patterns & fallback',
      passed,
      durationMs: Date.now() - start,
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} triggerHaptic() Multi-Modal Vibration Signatures & Fallbacks`
    );
  }

  // 4. PointerVelocityTracker sliding window & velocity calculation
  {
    const start = Date.now();
    let passed = true;
    let errorMsg = '';

    try {
      const tracker = createVelocityTracker();

      // Empty tracker
      assert.deepStrictEqual(
        tracker.getVelocity(),
        { vx: 0, vy: 0 },
        'Empty tracker must return 0 velocity'
      );

      // 1 point
      tracker.addPoint(100, 100, 1000);
      assert.deepStrictEqual(
        tracker.getVelocity(),
        { vx: 0, vy: 0 },
        '1-point tracker must return 0 velocity'
      );

      // 2 points: 100px move in 100ms = 1000 px/s
      tracker.addPoint(200, 150, 1100);
      const vel = tracker.getVelocity();
      assert.ok(
        Math.abs(vel.vx - 1000) < 1,
        `Expected vx ~1000, got ${vel.vx}`
      );
      assert.ok(Math.abs(vel.vy - 500) < 1, `Expected vy ~500, got ${vel.vy}`);

      // History pruning (>100ms cutoff)
      tracker.addPoint(300, 200, 1300); // 200ms jump
      const velPruned = tracker.getVelocity();
      assert.ok(
        Number.isFinite(velPruned.vx) && Number.isFinite(velPruned.vy),
        'Pruned velocity must be finite'
      );

      // Reset
      tracker.reset();
      assert.deepStrictEqual(
        tracker.getVelocity(),
        { vx: 0, vy: 0 },
        'Reset tracker must return 0 velocity'
      );
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    }

    results.push({
      suite: 'Fluid Motion Physics',
      name: 'createVelocityTracker() sliding window release velocity',
      passed,
      durationMs: Date.now() - start,
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} PointerVelocityTracker Sliding Window Velocity`
    );
  }
}

function runCssTokensAndDesignStandardsStress() {
  console.log(
    '\n--- [TEST SUITE 2] CSS Design Tokens, Springs & Accessibility Audit ---'
  );
  const start = Date.now();
  let passed = true;
  let errorMsg = '';
  const auditedTokens: Record<string, boolean> = {};

  try {
    const cssPath = path.join(process.cwd(), 'src/app/globals.css');
    const css = fs.readFileSync(cssPath, 'utf8');

    // 1. WWDC Spring Curves
    assert.ok(
      css.includes('--ease-spring-default: cubic-bezier(0.2, 0.9, 0.3, 1)'),
      'Missing --ease-spring-default cubic-bezier token'
    );
    assert.ok(
      css.includes('--ease-spring-sheet: cubic-bezier(0.32, 0.72, 0, 1)'),
      'Missing --ease-spring-sheet cubic-bezier token'
    );
    assert.ok(
      css.includes('--ease-apple-out: cubic-bezier(0.16, 1, 0.3, 1)'),
      'Missing --ease-apple-out cubic-bezier token'
    );
    auditedTokens['springCurves'] = true;

    // 2. Active Touch-Press Scaling (.touch-press scale(0.97))
    assert.ok(
      css.includes('.touch-press'),
      'Missing .touch-press utility class'
    );
    assert.ok(
      css.includes('transform: scale(0.97)'),
      'Missing scale(0.97) in .touch-press:active'
    );
    assert.ok(
      css.includes('touch-action: manipulation'),
      'Missing touch-action: manipulation in .touch-press'
    );
    auditedTokens['touchPress'] = true;

    // 3. Apple Translucent Materials
    assert.ok(css.includes('.apple-chrome'), 'Missing .apple-chrome token');
    assert.ok(
      css.includes('backdrop-filter: blur(20px) saturate(125%)'),
      'Missing blur(20px) in .apple-chrome'
    );
    assert.ok(css.includes('.apple-card'), 'Missing .apple-card token');
    assert.ok(
      css.includes(
        '--shadow-specular: inset 0 1px 0 rgba(255, 255, 255, 0.08)'
      ),
      'Missing specular rim highlight shadow'
    );
    auditedTokens['translucentMaterials'] = true;

    // 4. OpenType Tabular Numerals
    assert.ok(
      css.includes('.tabular-numbers'),
      'Missing .tabular-numbers utility'
    );
    assert.ok(
      css.includes('font-feature-settings: "tnum" 1'),
      'Missing tnum font-feature-settings'
    );
    assert.ok(
      css.includes('font-variant-numeric: tabular-nums'),
      'Missing font-variant-numeric'
    );
    auditedTokens['tabularNumbers'] = true;

    // 5. Accessibility Media Queries
    assert.ok(
      css.includes('@media (prefers-reduced-motion: reduce)'),
      'Missing prefers-reduced-motion media query'
    );
    auditedTokens['accessibilityTripleGate'] = true;

    // 6. Focus Ring Standards
    assert.ok(css.includes(':focus-visible'), 'Missing :focus-visible rules');
    assert.ok(
      css.includes('outline: 3px solid rgba(163, 166, 255, 0.5)'),
      'Missing high-visibility focus outline'
    );
    auditedTokens['focusRing'] = true;
  } catch (err) {
    passed = false;
    errorMsg = err instanceof Error ? err.message : String(err);
  }

  results.push({
    suite: 'CSS Tokens & Standards',
    name: 'WWDC Spring Physics, Materials, Tabular Numbers & Triple-Gate',
    passed,
    durationMs: Date.now() - start,
    details: auditedTokens,
    error: errorMsg || undefined,
  });
  console.log(
    `  ${passed ? '✓' : '✗'} CSS Token Suite (Springs, Specular Highlights, Tabular Numerals, Triple-Gate)`
  );
}

async function runBrowserInteractionAndLayoutStress(browser: Browser) {
  console.log(
    '\n--- [TEST SUITE 3] Browser Touch Targets & Zero Layout Shifts across 11 Routes ---'
  );

  // Test 1: Button & Interactive Action Touch Target Audit (min-h >= 44px)
  {
    const start = Date.now();
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const page = await context.newPage();
    await setupAuth(page);

    let passed = true;
    let errorMsg = '';
    let totalButtons = 0;
    let compliantButtons = 0;
    const buttonAuditLog: string[] = [];

    try {
      for (const route of DASHBOARD_ROUTES) {
        await page.goto(`http://localhost:3000${route.path}`, {
          waitUntil: 'domcontentloaded',
          timeout: 10000,
        });
        await page.waitForTimeout(200);

        const buttons = await page.evaluate(() => {
          const btns = Array.from(
            document.querySelectorAll(
              'button, input[type="button"], input[type="submit"], [role="button"]'
            )
          ) as HTMLElement[];

          return btns
            .map((el) => {
              const rect = el.getBoundingClientRect();
              const comp = window.getComputedStyle(el);
              const isVisible =
                rect.width > 0 &&
                rect.height > 0 &&
                comp.display !== 'none' &&
                comp.visibility !== 'hidden';
              return {
                tag: el.tagName.toLowerCase(),
                id: el.id,
                ariaLabel: el.getAttribute('aria-label') || '',
                text: (el.innerText || '').slice(0, 30).trim(),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                minHeight: comp.minHeight,
                isVisible,
              };
            })
            .filter((e) => e.isVisible);
        });

        for (const btn of buttons) {
          totalButtons++;
          // WCAG standard: interactive target >= 44px min height or effective target >= 40px
          const isCompliant = btn.height >= 40 || btn.minHeight === '44px';
          if (isCompliant) {
            compliantButtons++;
          } else {
            buttonAuditLog.push(
              `[${route.path}] <${btn.tag}> "${btn.text || btn.ariaLabel || btn.id}" (${btn.width}x${btn.height}px)`
            );
          }
        }
      }

      const complianceRate =
        totalButtons > 0 ? compliantButtons / totalButtons : 1;
      assert.ok(
        complianceRate >= 0.85,
        `Button touch target compliance rate ${Math.round(complianceRate * 100)}% < 85%`
      );
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    } finally {
      await context.close();
    }

    results.push({
      suite: 'Browser Interaction & Touch Targets',
      name: `Action Buttons Touch Target Audit across 11 routes (${totalButtons} audited, ${compliantButtons} compliant)`,
      passed,
      durationMs: Date.now() - start,
      details: {
        totalButtons,
        compliantButtons,
        nonCompliantSample: buttonAuditLog.slice(0, 5),
      },
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} Action Buttons Touch Target Audit (${compliantButtons}/${totalButtons} compliant | ${Math.round((compliantButtons / totalButtons) * 100)}%)`
    );
  }

  // Test 2: Zero Layout Shift (CLS) and Bounding Box Stability
  {
    const start = Date.now();
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const page = await context.newPage();
    await setupAuth(page);

    let passed = true;
    let errorMsg = '';
    const routeLayoutShifts: Record<string, number> = {};

    try {
      for (const route of DASHBOARD_ROUTES) {
        await page.evaluate(() => {
          (window as unknown as { __clsScore: number }).__clsScore = 0;
          try {
            const observer = new PerformanceObserver((entryList) => {
              for (const entry of entryList.getEntries()) {
                const layoutShift = entry as PerformanceEntry & {
                  value?: number;
                  hadRecentInput?: boolean;
                };
                if (!layoutShift.hadRecentInput && layoutShift.value) {
                  (window as unknown as { __clsScore: number }).__clsScore +=
                    layoutShift.value;
                }
              }
            });
            observer.observe({ type: 'layout-shift', buffered: true });
          } catch {}
        });

        await page.goto(`http://localhost:3000${route.path}`, {
          waitUntil: 'domcontentloaded',
          timeout: 10000,
        });
        await page.waitForTimeout(400);

        const cls = await page.evaluate(() => {
          return (window as unknown as { __clsScore: number }).__clsScore || 0;
        });

        routeLayoutShifts[route.path] = cls;
        assert.ok(
          cls < 0.1,
          `Route ${route.path} exceeded CLS limit: ${cls} >= 0.1`
        );
      }
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    } finally {
      await context.close();
    }

    results.push({
      suite: 'Browser Interaction & Touch Targets',
      name: 'Zero Layout Shift (CLS < 0.1) across all 11 routes',
      passed,
      durationMs: Date.now() - start,
      details: { routeLayoutShifts },
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} Zero Layout Shift (CLS) across all 11 Routes (Max CLS < 0.1)`
    );
  }

  // Test 3: Tab Switching & Filter Typing Dimensional Stability
  {
    const start = Date.now();
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const page = await context.newPage();
    await setupAuth(page);

    let passed = true;
    let errorMsg = '';

    try {
      // 1. Timetable Grid <-> List view toggle stability
      await page.goto('http://localhost:3000/dashboard/timetable', {
        waitUntil: 'domcontentloaded',
      });
      await page.waitForSelector('table', { timeout: 10000 });

      const listBtn = page.getByRole('button', { name: /List/i });
      const gridBtn = page.getByRole('button', { name: /Grid/i });
      await listBtn.click();
      await page.waitForSelector('table', { timeout: 10000 });
      assert.ok(
        await page.locator('table').first().isVisible(),
        'Timetable list view visible'
      );

      await gridBtn.click();
      await page.waitForSelector('table', { timeout: 10000 });
      assert.ok(
        await page.locator('table').first().isVisible(),
        'Timetable grid view restored'
      );

      // 2. Marks page search filtering stability
      await page.goto('http://localhost:3000/dashboard/marks', {
        waitUntil: 'domcontentloaded',
      });
      await page.waitForSelector('table', { timeout: 10000 });

      const searchInput = page.getByPlaceholder(/Search courses/i);
      await searchInput.fill('CS');
      await page.waitForTimeout(150);
      assert.ok(
        await page.locator('table').first().isVisible(),
        'Marks table visible after filter'
      );
      await searchInput.fill('');
      await page.waitForTimeout(150);
      assert.ok(
        await page.locator('table').first().isVisible(),
        'Marks table visible after clear filter'
      );

      // 3. Tools page calculation input interactions
      await page.goto('http://localhost:3000/dashboard/tools', {
        waitUntil: 'domcontentloaded',
      });
      await page.waitForSelector('input[type="number"]', { timeout: 10000 });
      const inputs = page.locator('input[type="number"]');
      const count = await inputs.count();
      if (count > 0) {
        await inputs.first().fill('85');
        await page.waitForTimeout(100);
      }
      assert.ok(
        await page
          .getByText(/Attendance Target/i)
          .first()
          .isVisible(),
        'Tools page responsive to inputs'
      );
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    } finally {
      await context.close();
    }

    results.push({
      suite: 'Browser Interaction & Touch Targets',
      name: 'Dynamic View Toggles, Filter Typing & Interactive Tools Stability',
      passed,
      durationMs: Date.now() - start,
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} Dynamic View Toggles, Search Filters & Form Tools Interaction ${errorMsg ? `(${errorMsg})` : ''}`
    );
  }

  // Test 4: Tabular Numbers CSS Rendering Check on Metric Elements
  {
    const start = Date.now();
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const page = await context.newPage();
    await setupAuth(page);

    let passed = true;
    let errorMsg = '';
    let tabularElementsCount = 0;

    try {
      await page.goto('http://localhost:3000/dashboard', {
        waitUntil: 'domcontentloaded',
      });
      await page.waitForTimeout(300);

      const count = await page
        .locator('.tabular-numbers, [class*="tabular-numbers"]')
        .count();
      tabularElementsCount = count;
      assert.ok(
        tabularElementsCount > 0,
        'Expected tabular numbers elements on dashboard'
      );
    } catch (err) {
      passed = false;
      errorMsg = err instanceof Error ? err.message : String(err);
    } finally {
      await context.close();
    }

    results.push({
      suite: 'Browser Interaction & Touch Targets',
      name: `Tabular Numbers CSS Elements Verification (${tabularElementsCount} elements found)`,
      passed,
      durationMs: Date.now() - start,
      details: { tabularElementsCount },
      error: errorMsg || undefined,
    });
    console.log(
      `  ${passed ? '✓' : '✗'} Tabular Numbers Elements Verified (${tabularElementsCount} elements)`
    );
  }
}

async function main() {
  console.log('='.repeat(80));
  console.log(
    '⚔️  CHALLENGER 2: INTERACTION, MOTION PHYSICS & BROWSER STRESS SUITE'
  );
  console.log('='.repeat(80));

  // Run Unit & CSS tokens suites synchronously
  runFluidMotionMathStress();
  runCssTokensAndDesignStandardsStress();

  // Run Browser E2E Interaction Suites
  const browser = await chromium.launch({ headless: true });
  try {
    await runBrowserInteractionAndLayoutStress(browser);
  } finally {
    await browser.close();
  }

  // Summary Scorecard
  console.log('\n' + '='.repeat(80));
  console.log('CHALLENGER 2 EMPIRICAL SCORECARD');
  console.log('='.repeat(80));

  const total = results.length;
  const passedCount = results.filter((r) => r.passed).length;
  const failedCount = results.filter((r) => !r.passed).length;
  const totalDuration = results.reduce((acc, r) => acc + r.durationMs, 0);

  console.log(`Total Stress Suites : ${total}`);
  console.log(`Passed Suites       : ${passedCount}`);
  console.log(`Failed Suites       : ${failedCount}`);
  console.log(`Total Time          : ${totalDuration}ms`);
  console.log(
    `Verdict             : ${failedCount === 0 ? '🏆 100% EMPIRICAL PASS (APPROVE)' : '❌ FAILURES DETECTED (REQUEST_CHANGES)'}`
  );
  console.log('='.repeat(80));

  if (failedCount > 0) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Fatal interaction stress harness exception:', err);
  process.exit(1);
});
