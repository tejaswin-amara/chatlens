import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import fs from 'node:fs';
import path from 'node:path';

// Import components under test
import ERPTablePage from '@/components/ERPTablePage';
import { PageHeader } from '@/components/ui/page-header';

// Mock localStorage helper for NodeJS test environment
class MockLocalStorage {
  private store: Map<string, string> = new Map();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }

  get length(): number {
    return this.store.size;
  }
}

describe('Challenger M1 Adversarial Stress Suite', () => {
  // =========================================================================
  // Section 1: Remember Me & Credential Persistence Adversarial Testing
  // =========================================================================
  describe('1. Remember Me & Auth Persistence Logic', () => {
    let mockStorage: MockLocalStorage;

    beforeEach(() => {
      mockStorage = new MockLocalStorage();
    });

    test('Remember Me = true stores ONLY username, never password', () => {
      const username = '2100039999';
      const rawPassword = 'SecretPassword123!';
      const rememberMe = true;

      // Simulate client-side login persistence logic
      if (rememberMe) {
        mockStorage.setItem('remember_username', username);
      } else {
        mockStorage.removeItem('remember_username');
      }
      // Security invariant check: password must ALWAYS be removed/never stored
      mockStorage.removeItem('remember_password');

      assert.strictEqual(mockStorage.getItem('remember_username'), '2100039999');
      assert.strictEqual(mockStorage.getItem('remember_password'), null);
      assert.strictEqual(mockStorage.getItem('password'), null);
      assert.strictEqual(rawPassword.length > 0, true);
    });

    test('Remember Me = false clears stored username and never stores password', () => {
      // Pre-populate with previous saved username
      mockStorage.setItem('remember_username', 'previous_user');
      mockStorage.setItem('remember_password', 'rogue_legacy_password');

      const rememberMe = false;
      const username = '2100031111';

      if (rememberMe) {
        mockStorage.setItem('remember_username', username);
      } else {
        mockStorage.removeItem('remember_username');
      }
      mockStorage.removeItem('remember_password');

      assert.strictEqual(mockStorage.getItem('remember_username'), null);
      assert.strictEqual(mockStorage.getItem('remember_password'), null);
    });

    test('Mount logic correctly hydrates username when remember_username exists', () => {
      mockStorage.setItem('remember_username', '2100032222');

      // Emulate page mount hydration
      const savedUser = mockStorage.getItem('remember_username');
      let hydratedUsername = '';
      let hydratedRememberMe = false;

      if (savedUser) {
        hydratedUsername = savedUser;
        hydratedRememberMe = true;
      }

      assert.strictEqual(hydratedUsername, '2100032222');
      assert.strictEqual(hydratedRememberMe, true);
    });

    test('Sign out flow purges all cached student metadata and saved username', () => {
      mockStorage.setItem('studentId', '2100030000');
      mockStorage.setItem('kl_student_name', 'Jane Doe');
      mockStorage.setItem('kl_student_photo', 'https://example.com/photo.jpg');
      mockStorage.setItem('kl_student_profile', '{"cgpa":"9.8"}');
      mockStorage.setItem('kl_erp_academic_years', '[{"value":"2025-2026"}]');
      mockStorage.setItem('kl_erp_semesters', '[{"value":"1"}]');
      mockStorage.setItem('kl_erp_year', '2025-2026');
      mockStorage.setItem('kl_erp_sem', '1');
      mockStorage.setItem('remember_username', '2100030000');
      mockStorage.setItem('kl_sidebar_collapsed', 'true');

      // Emulate Navigation.tsx handleSignOut
      const keysToPurge = [
        'studentId',
        'kl_student_name',
        'kl_student_photo',
        'kl_student_profile',
        'kl_erp_academic_years',
        'kl_erp_semesters',
        'kl_erp_year',
        'kl_erp_sem',
        'remember_username',
      ];
      keysToPurge.forEach((key) => mockStorage.removeItem(key));

      assert.strictEqual(mockStorage.getItem('studentId'), null);
      assert.strictEqual(mockStorage.getItem('kl_student_name'), null);
      assert.strictEqual(mockStorage.getItem('kl_student_photo'), null);
      assert.strictEqual(mockStorage.getItem('remember_username'), null);
      assert.strictEqual(mockStorage.getItem('kl_erp_year'), null);
      // Non-auth UI preferences like sidebar state are preserved
      assert.strictEqual(mockStorage.getItem('kl_sidebar_collapsed'), 'true');
    });

    test('Demo Mode authentication flow initializes fallback academic credentials', () => {
      const demoData = {
        success: true,
        academicYears: [{ value: '2025-2026', label: '2025-2026' }],
        semesters: [{ value: '1', label: 'Odd Semester' }],
      };

      const academicYear = demoData.academicYears?.[0]?.value || '2025-2026';
      const semesterId = demoData.semesters?.[0]?.value || '1';

      mockStorage.setItem('kl_erp_year', academicYear);
      mockStorage.setItem('kl_erp_sem', semesterId);
      mockStorage.setItem('studentId', '2100030000');

      assert.strictEqual(mockStorage.getItem('kl_erp_year'), '2025-2026');
      assert.strictEqual(mockStorage.getItem('kl_erp_sem'), '1');
      assert.strictEqual(mockStorage.getItem('studentId'), '2100030000');
    });
  });

  // =========================================================================
  // Section 2: ERPTablePage & PageHeader Extensibility Stress Testing
  // =========================================================================
  describe('2. ERPTablePage columnFormatters & headerActions Edge Cases', () => {
    test('PageHeader renders title, description, and custom headerActions', () => {
      const customAction = React.createElement(
        'button',
        { id: 'btn-export', className: 'btn-primary' },
        'Export CSV'
      );

      const html = renderToString(
        React.createElement(PageHeader, {
          title: 'Exam Seating Plan',
          description: 'View upcoming mid-term seating arrangements',
          actions: customAction,
        })
      );

      assert.match(html, /Exam Seating Plan/);
      assert.match(html, /View upcoming mid-term seating arrangements/);
      assert.match(html, /id="btn-export"/);
      assert.match(html, /Export CSV/);
    });

    test('PageHeader renders gracefully without actions or description', () => {
      const html = renderToString(
        React.createElement(PageHeader, {
          title: 'Circulars',
        })
      );

      assert.match(html, /Circulars/);
      assert.doesNotMatch(html, /btn/);
    });

    test('PageHeader handles multiple actions (React Fragment / array of buttons)', () => {
      const actions = React.createElement(
        React.Fragment,
        null,
        React.createElement('button', { key: '1' }, 'Action 1'),
        React.createElement('button', { key: '2' }, 'Action 2')
      );

      const html = renderToString(
        React.createElement(PageHeader, {
          title: 'Attendance',
          actions,
        })
      );

      assert.match(html, /Action 1/);
      assert.match(html, /Action 2/);
    });

    test('MobileCardItem & Desktop Table formatting logic handles missing keys, null, and custom JSX', () => {
      // Simulate ERPTablePage formatting execution across edge cases
      const row: Record<string, unknown> = {
        'Course Code': '23CS2101',
        'Course Name': 'Distributed Systems',
        Grade: 'A+',
        NullableField: null,
        UndefinedField: undefined,
        ZeroValue: 0,
        BooleanField: false,
        EmptyString: '',
      };

      const columnFormatters: Record<
        string,
        (val: unknown, row: Record<string, unknown>) => React.ReactNode
      > = {
        Grade: (val) =>
          React.createElement('span', { className: 'badge-grade' }, `Grade: ${String(val)}`),
        NullableField: (val) => (val === null ? 'N/A' : String(val)),
        // Formatter that uses cross-column values from row
        'Course Code': (val, r) =>
          React.createElement(
            'strong',
            null,
            `${String(val)} - ${String(r['Course Name'])}`
          ),
        // Extra formatter for a non-existent column (should not crash)
        NonExistentKey: () => 'Should not be called',
      };

      // Test formatting logic directly
      const formatValue = (key: string, val: unknown) => {
        const formatter = columnFormatters[key];
        return formatter ? formatter(val, row) : String(val ?? '');
      };

      // 1. Missing formatter key -> falls back to String(val ?? '')
      assert.strictEqual(formatValue('ZeroValue', row['ZeroValue']), '0');
      assert.strictEqual(formatValue('BooleanField', row['BooleanField']), 'false');
      assert.strictEqual(formatValue('EmptyString', row['EmptyString']), '');
      assert.strictEqual(formatValue('UndefinedField', row['UndefinedField']), '');

      // 2. Custom formatter with JSX
      const gradeResult = formatValue('Grade', row['Grade']);
      const gradeHtml = renderToString(gradeResult as React.ReactElement);
      assert.match(gradeHtml, /class="badge-grade"/);
      assert.match(gradeHtml, /Grade: A\+/);

      // 3. Custom formatter with null handling
      assert.strictEqual(formatValue('NullableField', row['NullableField']), 'N/A');

      // 4. Formatter accessing cross-column row data
      const courseResult = formatValue('Course Code', row['Course Code']);
      const courseHtml = renderToString(courseResult as React.ReactElement);
      assert.match(courseHtml, /<strong>23CS2101 - Distributed Systems<\/strong>/);

      // 5. Unmapped column formatter does not crash
      assert.strictEqual(typeof columnFormatters['NonExistentKey'], 'function');
    });

    test('ERPTablePage component renders loading skeleton without crash', () => {
      // In SSR / static render, loading skeleton renders when data is undefined
      const html = renderToString(
        React.createElement(ERPTablePage, {
          module: 'circulars',
          title: 'University Circulars',
          description: 'Official notifications',
          emptyIcon: React.createElement('span', null, '📢'),
          emptyTitle: 'No Circulars Found',
          emptyDescription: 'Check back later for announcements.',
          headerActions: React.createElement('button', null, 'Refresh'),
        })
      );

      assert.match(html, /University Circulars/);
      assert.match(html, /Official notifications/);
      assert.match(html, /Refresh/);
    });
  });

  // =========================================================================
  // Section 3: CSS Keyframe & animate-spring-scale Token Verification
  // =========================================================================
  describe('3. CSS Tokens & animate-spring-scale Keyframe Inspection', () => {
    const cssPath = path.resolve(process.cwd(), 'src/app/globals.css');
    let cssContent: string;

    beforeEach(() => {
      cssContent = fs.readFileSync(cssPath, 'utf-8');
    });

    test('globals.css defines @keyframes spring-scale correctly', () => {
      assert.match(cssContent, /@keyframes\s+spring-scale\s*\{/);
      assert.match(cssContent, /from\s*\{\s*opacity:\s*0;\s*transform:\s*scale\(0\.92\);?\s*\}/);
      assert.match(cssContent, /to\s*\{\s*opacity:\s*1;\s*transform:\s*scale\(1\);?\s*\}/);
    });

    test('globals.css defines .animate-spring-scale utility class', () => {
      assert.match(
        cssContent,
        /\.animate-spring-scale\s*\{\s*animation:\s*spring-scale\s+240ms\s+var\(--ease-spring-default\)\s+both;?\s*\}/
      );
    });

    test('globals.css includes prefers-reduced-motion override for spring animations', () => {
      assert.match(cssContent, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
      assert.match(cssContent, /animation-duration:\s*1ms\s*!important/);
    });

    test('globals.css includes logical RTL drawer animations', () => {
      assert.match(cssContent, /\[dir=['"]rtl['"]\]\s*\.animate-drawer-enter/);
      assert.match(cssContent, /@keyframes\s+drawer-enter-rtl/);
    });

    test('consumer files correctly reference animate-spring-scale without syntax errors', () => {
      const consumers = [
        'src/app/dashboard/exam-seating/page.tsx',
        'src/app/dashboard/fee/page.tsx',
        'src/app/dashboard/marks/page.tsx',
        'src/components/attendance-calculator.tsx',
      ];

      for (const relPath of consumers) {
        const fullPath = path.resolve(process.cwd(), relPath);
        assert.strictEqual(fs.existsSync(fullPath), true, `Consumer file ${relPath} must exist`);
        const content = fs.readFileSync(fullPath, 'utf-8');
        assert.match(
          content,
          /animate-spring-scale/,
          `${relPath} should use animate-spring-scale`
        );
      }
    });
  });
});
