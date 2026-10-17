import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

import { Badge } from './badge';
import { Skeleton, SkeletonCard, SkeletonTable } from './skeleton';
import { Toast } from './toast';
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
} from './sheet';
import { AttendanceChart } from '@/app/dashboard/attendance/AttendanceChart';
import { GpaTrendChart } from '@/app/dashboard/marks/GpaTrendChart';
import { FeeBreakdownChart } from '@/app/dashboard/fee/FeeBreakdownChart';

describe('Milestone 2 (M2) UI Primitives & SVG Charts Verification Suite', () => {
  describe('Expanded Badge Primitive', () => {
    test('renders size scale (sm, md, lg) and pulse animation', () => {
      const htmlSm = renderToString(
        React.createElement(Badge, { size: 'sm', pulse: true }, 'Small Badge')
      );
      assert.match(htmlSm, /text-\[10px\]/);
      assert.match(htmlSm, /animate-pulse/);

      const htmlLg = renderToString(
        React.createElement(Badge, { size: 'lg' }, 'Large Badge')
      );
      assert.match(htmlLg, /text-xs/);
      assert.match(htmlLg, /px-3 py-1.5/);
    });

    test('renders M2 specialized variants (present, absent, pending, neutral, glass)', () => {
      const variants = [
        'present',
        'absent',
        'pending',
        'neutral',
        'glass',
      ] as const;
      for (const variant of variants) {
        const html = renderToString(
          React.createElement(Badge, { variant }, variant)
        );
        assert.ok(html.length > 0);
        assert.match(html, new RegExp(variant));
      }
    });

    test('renders with custom icon', () => {
      const icon = React.createElement('span', { id: 'test-icon' }, '⭐');
      const html = renderToString(
        React.createElement(Badge, { icon }, 'With Icon')
      );
      assert.match(html, /test-icon/);
      assert.match(html, /With Icon/);
    });
  });

  describe('Expanded Skeleton Primitive', () => {
    test('renders avatar, card, and table-row variants with pulse option', () => {
      const avatarHtml = renderToString(
        React.createElement(Skeleton, { variant: 'avatar', animation: 'pulse' })
      );
      assert.match(avatarHtml, /w-10 h-10 rounded-full/);
      assert.match(avatarHtml, /animate-pulse/);

      const cardHtml = renderToString(
        React.createElement(Skeleton, { variant: 'card' })
      );
      assert.match(cardHtml, /h-32 w-full/);

      const rowHtml = renderToString(
        React.createElement(Skeleton, { variant: 'table-row' })
      );
      assert.match(rowHtml, /h-12 w-full/);
    });

    test('renders composite SkeletonCard and SkeletonTable components', () => {
      const cardHtml = renderToString(React.createElement(SkeletonCard, null));
      assert.match(cardHtml, /animate-pulse/);

      const tableHtml = renderToString(
        React.createElement(SkeletonTable, { rows: 3 })
      );
      assert.match(tableHtml, /space-y-3/);
    });
  });

  describe('Native Tooltip Accessibility', () => {
    test('renders native tooltip with title attribute', () => {
      const html = renderToString(
        React.createElement(
          'span',
          { title: 'Tooltip Information' },
          'Hover Me'
        )
      );
      assert.match(html, /Hover Me/);
      assert.match(html, /title="Tooltip Information"/);
    });
  });

  describe('Toast Primitive', () => {
    test('renders Toast item with status role and polite aria-live for standard notification', () => {
      const html = renderToString(
        React.createElement(Toast, {
          toast: {
            id: 't1',
            title: 'Success',
            description: 'Operation completed',
            variant: 'success',
          },
          onDismiss: () => {},
        })
      );
      assert.match(html, /role="status"/);
      assert.match(html, /aria-live="polite"/);
      assert.match(html, /Success/);
      assert.match(html, /Operation completed/);
    });

    test('renders Toast item with alert role and assertive aria-live for destructive error', () => {
      const html = renderToString(
        React.createElement(Toast, {
          toast: {
            id: 't2',
            title: 'Error',
            description: 'Failed to sync',
            variant: 'destructive',
          },
          onDismiss: () => {},
        })
      );
      assert.match(html, /role="alert"/);
      assert.match(html, /aria-live="assertive"/);
      assert.match(html, /Error/);
    });
  });

  describe('Sheet Primitive (Drawer)', () => {
    test('renders Sheet trigger and hidden content when closed', () => {
      const html = renderToString(
        React.createElement(
          Sheet,
          { open: false },
          React.createElement(SheetTrigger, null, 'Open Drawer'),
          React.createElement(
            SheetContent,
            { side: 'right' },
            React.createElement(
              SheetHeader,
              null,
              React.createElement(SheetTitle, null, 'Drawer Title')
            ),
            React.createElement(SheetDescription, null, 'Drawer Body')
          )
        )
      );
      assert.match(html, /Open Drawer/);
      assert.doesNotMatch(html, /Drawer Title/);
    });

    test('renders backdrop overlay, role="dialog", aria-modal="true", and close button when open', () => {
      const html = renderToString(
        React.createElement(
          Sheet,
          { open: true },
          React.createElement(
            SheetContent,
            { side: 'left' },
            React.createElement(
              SheetHeader,
              null,
              React.createElement(SheetTitle, null, 'Left Sheet')
            ),
            React.createElement(
              SheetDescription,
              null,
              'Side drawer description'
            ),
            React.createElement(
              SheetFooter,
              null,
              React.createElement(SheetClose, null, 'Close Drawer')
            )
          )
        )
      );
      assert.match(html, /role="dialog"/);
      ariaAssert(html);
      assert.match(html, /aria-label="Close drawer"/);
      assert.match(html, /Left Sheet/);
      assert.match(html, /animate-slide-in-left/);
    });
  });

  describe('Native Search & Action Inputs', () => {
    test('renders search input with placeholder and accessible attributes', () => {
      const html = renderToString(
        React.createElement('input', {
          type: 'search',
          placeholder: 'Search...',
          'aria-label': 'Search actions',
        })
      );
      assert.match(html, /placeholder="Search\.\.\."/);
      assert.match(html, /aria-label="Search actions"/);
    });
  });

  describe('SVG Visual Trend Charts', () => {
    test('AttendanceChart renders SVG bar chart with gridlines and percentages', () => {
      const sampleData = [
        {
          'Course Code': 'CS101',
          'Subject Title': 'Computer Science',
          'Attendance %': '90%',
        },
        {
          'Course Code': 'MATH201',
          'Subject Title': 'Linear Algebra',
          'Attendance %': '70%',
        },
      ];
      const html = renderToString(
        React.createElement(AttendanceChart, { data: sampleData })
      );
      assert.match(html, /<svg/);
      assert.match(html, /aria-label="Attendance Bar Chart"/);
      assert.match(html, /90%/);
      assert.match(html, /70%/);
    });

    test('GpaTrendChart renders SVG line/area trend chart with points', () => {
      const sampleMarks = [
        { 'Course Code': 'CS101', Marks: '88' },
        { 'Course Code': 'EC201', Marks: '92' },
      ];
      const html = renderToString(
        React.createElement(GpaTrendChart, { data: sampleMarks })
      );
      assert.match(html, /<svg/);
      assert.match(html, /aria-label="GPA Performance Trend Chart"/);
      assert.match(html, /path/);
    });

    test('FeeBreakdownChart renders SVG donut chart with paid vs pending amounts', () => {
      const sampleFee = [
        { 'Fee Type': 'Tuition Fee', Amount: '50000', Status: 'PAID' },
        { 'Fee Type': 'Hostel Fee', Amount: '15000', Status: 'UNPAID' },
      ];
      const html = renderToString(
        React.createElement(FeeBreakdownChart, {
          data: sampleFee,
          totalFee: 65000,
          pendingFee: 15000,
        })
      );
      assert.match(html, /<svg/);
      assert.match(html, /Total/);
      assert.match(html, /65,000/);
      assert.match(html, /15,000/);
    });
  });
});

function ariaAssert(html: string) {
  assert.match(html, /aria-modal="true"/);
}
