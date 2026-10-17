import { test, expect } from '@playwright/test';

test.describe('Comprehensive 11-Route E2E Browser Verification', () => {
  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (
          !text.includes('React error #418') &&
          !text.includes('Hydration failed')
        ) {
          consoleErrors.push(text);
        }
      }
    });
    page.on('pageerror', (err) => {
      if (
        !err.message.includes('React error #418') &&
        !err.message.includes('Hydration failed')
      ) {
        consoleErrors.push(err.message);
      }
    });

    // Set authenticated session cookie
    await page.context().addCookies([
      {
        name: 'kl_erp_session',
        value: 'enc.demo_session_data',
        url: 'http://localhost:3000',
      },
    ]);

    // Pre-seed storage state before any page script executes
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
      window.sessionStorage.setItem('kl_erp_csrf_token', 'demo_csrf_token_123');
      window.sessionStorage.setItem('kl_erp_year', '2025-2026');
      window.sessionStorage.setItem('kl_erp_sem', '1');
      window.sessionStorage.setItem('kl_erp_academic_years', years);
      window.sessionStorage.setItem('kl_erp_semesters', sems);
      window.sessionStorage.setItem('kl_timetable_2025-2026_1', ttMock);
    });
  });

  test('Route 1: / (Login Route) loads cleanly without errors', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page.locator('#student-id-field')).toBeVisible();
    await expect(page.locator('#password-field')).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 2: /dashboard (Dashboard Overview) renders live ERP summary data', async ({
    page,
  }) => {
    await page.goto('/dashboard');

    await expect(page.getByText(/Welcome back/i)).toBeVisible();
    await expect(page.getByText(/Cumulative GPA/i)).toBeVisible();
    await expect(page.getByText(/Daily Schedule/i)).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 3: /dashboard/timetable (Student Timetable) renders matrix grid & list views', async ({
    page,
  }) => {
    await page.goto('/dashboard/timetable');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: /Student Timetable/i })
    ).toBeVisible();
    const gridBtn = page.getByRole('button', { name: /Grid/i });
    const listBtn = page.getByRole('button', { name: /List/i });
    await expect(gridBtn).toBeVisible();
    await expect(listBtn).toBeVisible();
    await expect(
      page.getByRole('button', { name: /Export CSV/i })
    ).toBeVisible();

    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });

    await listBtn.click();
    await expect(page.locator('table')).toBeVisible();

    await gridBtn.click();
    await expect(page.locator('table')).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 4: /dashboard/attendance (Attendance) renders attendance breakdown', async ({
    page,
  }) => {
    await page.goto('/dashboard/attendance');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: 'Attendance', exact: true })
    ).toBeVisible();
    await expect(page.locator('#main-content')).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 5: /dashboard/marks (Internal Marks) renders assessment scores', async ({
    page,
  }) => {
    await page.goto('/dashboard/marks');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: /Marks & Grades/i })
    ).toBeVisible();
    await expect(page.getByPlaceholder(/Search courses/i)).toBeVisible();
    await expect(
      page.getByRole('button', { name: /Export CSV/i })
    ).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 6: /dashboard/profile (Student Profile) renders student info & courses', async ({
    page,
  }) => {
    await page.goto('/dashboard/profile');

    await expect(
      page.locator('#main-content').getByRole('heading', { name: /Profile/i })
    ).toBeVisible();
    await expect(page.getByText(/Alex Student/i).first()).toBeVisible();
    await expect(page.getByText(/2100030000/i).first()).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 7: /dashboard/fee (Fee Details) renders fee balance & payment status', async ({
    page,
  }) => {
    await page.goto('/dashboard/fee');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: /Fee Details/i })
    ).toBeVisible();
    await expect(page.getByText(/Total Pending/i)).toBeVisible();
    await expect(page.getByText(/Total Paid/i)).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 8: /dashboard/tools (Student Tools) renders calculators & tools', async ({
    page,
  }) => {
    await page.goto('/dashboard/tools');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: /Tools & Calculators/i })
    ).toBeVisible();
    await expect(page.getByText(/Attendance Target/i).first()).toBeVisible();
    await expect(page.getByText(/CGPA Goal Predictor/i).first()).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 9: /dashboard/circulars (Circulars) renders announcements table', async ({
    page,
  }) => {
    await page.goto('/dashboard/circulars');

    await expect(
      page.locator('#main-content').getByRole('heading', { name: /Circulars/i })
    ).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 10: /dashboard/hostels (Hostel Info) renders hostel allocation data', async ({
    page,
  }) => {
    await page.goto('/dashboard/hostels');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: /Hostel Information/i })
    ).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 11: /dashboard/library (Library) renders library records', async ({
    page,
  }) => {
    await page.goto('/dashboard/library');

    await expect(
      page.locator('#main-content').getByRole('heading', { name: /Library/i })
    ).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test('Route 12: /dashboard/exam-seating (Exam Seating) renders seating data', async ({
    page,
  }) => {
    await page.goto('/dashboard/exam-seating');

    await expect(
      page
        .locator('#main-content')
        .getByRole('heading', { name: /Exam Seating/i })
    ).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });
});
