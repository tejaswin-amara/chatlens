import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

import { AttendanceChart } from '@/app/dashboard/attendance/AttendanceChart';
import { GpaTrendChart } from '@/app/dashboard/marks/GpaTrendChart';
import { FeeBreakdownChart } from '@/app/dashboard/fee/FeeBreakdownChart';
import { AriaLiveRegion } from '@/components/ui/aria-live';
import { Toast } from '@/components/ui/toast';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';

describe('Challenger M2 - Empirical Chart & WCAG Verification', () => {
  describe('1. AttendanceChart Empirical Boundary & Edge Cases', () => {
    test('returns null for empty, null, or undefined data', () => {
      assert.strictEqual(
        renderToString(React.createElement(AttendanceChart, { data: [] })),
        ''
      );
      assert.strictEqual(
        renderToString(
          React.createElement(AttendanceChart, {
            data: null as unknown as Record<string, unknown>[],
          })
        ),
        ''
      );
      assert.strictEqual(
        renderToString(
          React.createElement(AttendanceChart, {
            data: undefined as unknown as Record<string, unknown>[],
          })
        ),
        ''
      );
    });

    test('renders correctly for a single entry dataset', () => {
      const singleData = [
        {
          'Course Code': 'CS101',
          'Subject Title': 'Computer Science',
          'Attendance %': '95%',
        },
      ];
      const html = renderToString(
        React.createElement(AttendanceChart, { data: singleData })
      );
      assert.match(html, /aria-label="Attendance Bar Chart"/);
      assert.match(html, /CS101/);
      assert.match(html, /95/);
      assert.match(html, /<rect/);
    });

    test('handles 0% and 100% boundary attendance percentages', () => {
      const boundaryData = [
        { 'Course Code': 'SUBJ0', 'Attendance %': '0%' },
        { 'Course Code': 'SUBJ100', 'Attendance %': '100%' },
      ];
      const html = renderToString(
        React.createElement(AttendanceChart, { data: boundaryData })
      );
      assert.match(html, /SUBJ0/);
      assert.match(html, /SUBJ100/);
      assert.match(html, /0/);
      assert.match(html, /100/);
    });

    test('handles unrecognized keys and truncated long course names safely', () => {
      const weirdData = [
        { UnknownField: 'EXCEEDINGLY_LONG_SUBJECT_TITLE_HERO', pct: 88 },
      ];
      const html = renderToString(
        React.createElement(AttendanceChart, { data: weirdData })
      );
      assert.match(html, /88/);
      assert.match(html, /EXCEEDINGL…/);
    });
  });

  describe('2. GpaTrendChart Empirical Boundary & Edge Cases', () => {
    test('returns null for empty, null, or undefined data', () => {
      assert.strictEqual(
        renderToString(React.createElement(GpaTrendChart, { data: [] })),
        ''
      );
      assert.strictEqual(
        renderToString(
          React.createElement(GpaTrendChart, {
            data: null as unknown as Record<string, unknown>[],
          })
        ),
        ''
      );
      assert.strictEqual(
        renderToString(
          React.createElement(GpaTrendChart, {
            data: undefined as unknown as Record<string, unknown>[],
          })
        ),
        ''
      );
    });

    test('renders single-entry dataset without division by zero', () => {
      const singleData = [{ 'Course Code': 'CS201', Marks: '85' }];
      const html = renderToString(
        React.createElement(GpaTrendChart, { data: singleData })
      );
      assert.match(html, /aria-label="GPA Performance Trend Chart"/);
      assert.match(html, /CS201/);
      assert.match(html, /85/);
      assert.match(html, /<circle/);
    });

    test('handles 0 score and 100 score boundary values correctly', () => {
      const boundaryData = [
        { 'Course Code': 'ZERO', Marks: '0' },
        { 'Course Code': 'MAX', Marks: '100' },
      ];
      const html = renderToString(
        React.createElement(GpaTrendChart, { data: boundaryData })
      );
      assert.match(html, /Max:.*100/);
      assert.match(html, />0</);
      assert.match(html, />100</);
    });
  });

  describe('3. FeeBreakdownChart Empirical Boundary & Edge Cases', () => {
    test('renders default 0 total/pending gracefully without crash or NaN', () => {
      const html = renderToString(
        React.createElement(FeeBreakdownChart, { data: [] })
      );
      assert.match(html, /100.*% Paid/);
      assert.match(html, /₹.*0/);
      assert.doesNotMatch(html, /NaN/);
    });

    test('renders single paid fee item accurately', () => {
      const singleData = [
        { 'Fee Type': 'Tuition', Amount: '45000', Status: 'PAID' },
      ];
      const html = renderToString(
        React.createElement(FeeBreakdownChart, { data: singleData })
      );
      assert.match(html, /100.*% Paid/);
      assert.match(html, /45,000/);
    });

    test('renders 100% unpaid/pending fee items accurately', () => {
      const unpaidData = [
        { 'Fee Type': 'Hostel', Amount: '20000', Status: 'UNPAID' },
      ];
      const html = renderToString(
        React.createElement(FeeBreakdownChart, { data: unpaidData })
      );
      assert.match(html, /0.*% Paid/);
      assert.match(html, /20,000/);
      assert.match(html, /Pending Due/);
    });

    test('formats large currency numbers correctly', () => {
      const largeData = [
        { 'Fee Type': 'Building Fund', Amount: '1000000', Status: 'PAID' },
      ];
      const html = renderToString(
        React.createElement(FeeBreakdownChart, { data: largeData })
      );
      assert.match(html, /1,000,000/);
    });
  });

  describe('4. WCAG 2.2 Accessibility Primitives Empirical Tests', () => {
    test('AriaLiveRegion renders polite and assertive containers with sr-only', () => {
      const html = renderToString(
        React.createElement(
          AriaLiveRegion,
          null,
          React.createElement('div', null, 'App Body')
        )
      );
      assert.match(html, /aria-live="polite"/);
      assert.match(html, /aria-live="assertive"/);
      assert.match(html, /aria-atomic="true"/);
      assert.match(html, /sr-only/);
    });

    test('Toast notification renders correct ARIA live priority and alert/status role', () => {
      const politeToast = renderToString(
        React.createElement(Toast, {
          toast: { id: '1', title: 'Saved', variant: 'success' },
          onDismiss: () => {},
        })
      );
      assert.match(politeToast, /role="status"/);
      assert.match(politeToast, /aria-live="polite"/);
      assert.match(politeToast, /min-w-\[44px\] min-h-\[44px\]/); // 44px touch target on dismiss button

      const assertiveToast = renderToString(
        React.createElement(Toast, {
          toast: { id: '2', title: 'Network Error', variant: 'destructive' },
          onDismiss: () => {},
        })
      );
      assert.match(assertiveToast, /role="alert"/);
      assert.match(assertiveToast, /aria-live="assertive"/);
    });

    test('Sheet component adheres to WCAG dialog accessibility standards', () => {
      const html = renderToString(
        React.createElement(
          Sheet,
          { open: true },
          React.createElement(
            SheetContent,
            { side: 'right' },
            React.createElement(
              SheetHeader,
              null,
              React.createElement(SheetTitle, null, 'Accessibility Test')
            ),
            React.createElement(SheetDescription, null, 'Test modal body')
          )
        )
      );
      assert.match(html, /role="dialog"/);
      assert.match(html, /aria-modal="true"/);
      assert.match(html, /aria-label="Close drawer"/);
      assert.match(html, /min-w-\[44px\] min-h-\[44px\]/);
    });
  });
});
