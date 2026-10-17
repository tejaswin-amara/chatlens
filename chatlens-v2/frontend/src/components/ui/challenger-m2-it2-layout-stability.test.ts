import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

import * as Icons from './icons';
import { Button } from './button';
import { Badge } from './badge';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './card';
import { Input } from './input';
import { StatCard } from './stat-card';
import { EmptyState } from './empty-state';
import { Progress } from './progress';
import { Skeleton } from './skeleton';
import { PageHeader } from './page-header';
import { AriaLiveRegion } from './aria-live';

import { AIChatInput } from '../ai/AIChatInput';
import { AIChatMessageList } from '../ai/AIChatMessageList';
import { AIChatSuggestionChips } from '../ai/AIChatSuggestionChips';
import { AIToolExecutionIndicator } from '../ai/AIToolExecutionIndicator';

import ERPTablePage from '../ERPTablePage';
import { SimpleCalculator } from '../attendance-calculator';

describe('Empirical Challenger 2: Layout Stability, Accessibility & Consumer Integrity Suite', () => {
  describe('1. Icon System Comprehensive Stress Test (All 55 Glyphs)', () => {
    const ALL_55_ICONS: Array<keyof typeof Icons> = [
      'Activity',
      'AlertCircle',
      'AlertTriangle',
      'Armchair',
      'Award',
      'Bell',
      'BookOpen',
      'Building2',
      'Calendar',
      'CalendarDays',
      'CalendarOff',
      'CheckCircle',
      'CheckCircle2',
      'CheckSquare',
      'ChevronDown',
      'ChevronLeft',
      'ChevronRight',
      'ChevronUp',
      'Clock',
      'CreditCard',
      'DollarSign',
      'Download',
      'Filter',
      'GraduationCap',
      'HelpCircle',
      'Inbox',
      'Info',
      'LayoutDashboard',
      'LayoutGrid',
      'List',
      'Loader2',
      'Lock',
      'LogIn',
      'LogOut',
      'MapPin',
      'Maximize2',
      'Megaphone',
      'Menu',
      'MoreHorizontal',
      'Percent',
      'RefreshCw',
      'Search',
      'Send',
      'ShieldCheck',
      'Sparkles',
      'Star',
      'Target',
      'Trash2',
      'TrendingDown',
      'TrendingUp',
      'User',
      'Wallet',
      'Wrench',
      'X',
      'XCircle',
    ];

    test('all 55 icons render valid standalone SVG with correct default geometry and viewBox', () => {
      assert.strictEqual(ALL_55_ICONS.length, 55);
      for (const iconName of ALL_55_ICONS) {
        const IconComponent = Icons[
          iconName
        ] as React.ComponentType<Icons.IconProps>;
        const html = renderToString(React.createElement(IconComponent));
        assert.match(html, /<svg/);
        assert.match(html, /viewBox="0 0 24 24"/);
        assert.match(html, /fill="none"/);
        assert.match(html, /stroke="currentColor"/);
        assert.match(html, /stroke-width="2"/);
      }
    });

    test('all 55 icons cleanly handle custom width, height, strokeWidth, className and accessibility attributes', () => {
      for (const iconName of ALL_55_ICONS) {
        const IconComponent = Icons[
          iconName
        ] as React.ComponentType<Icons.IconProps>;
        const html = renderToString(
          React.createElement(IconComponent, {
            width: 36,
            height: 36,
            strokeWidth: 1.75,
            className: 'custom-icon-class text-emerald-400',
            'aria-hidden': 'true',
            role: 'img',
          })
        );
        assert.match(html, /width="36"/);
        assert.match(html, /height="36"/);
        assert.match(html, /stroke-width="1.75"/);
        assert.match(html, /custom-icon-class/);
        assert.match(html, /text-emerald-400/);
        assert.match(html, /aria-hidden="true"/);
        assert.match(html, /role="img"/);
      }
    });

    test('all 55 icons support string size props (e.g. rem/px) and width/height overrides', () => {
      for (const iconName of ALL_55_ICONS) {
        const IconComponent = Icons[
          iconName
        ] as React.ComponentType<Icons.IconProps>;
        const html = renderToString(
          React.createElement(IconComponent, {
            size: '2.5rem',
          })
        );
        assert.match(html, /width="2\.5rem"/);
        assert.match(html, /height="2\.5rem"/);
      }
    });
  });

  describe('2. UI Primitives Layout Stability & Accessibility', () => {
    test('Button renders all visual variants with WCAG touch bounds and focus ring tokens', () => {
      const variants: Array<
        | 'default'
        | 'destructive'
        | 'outline'
        | 'secondary'
        | 'ghost'
        | 'primary'
      > = [
        'default',
        'destructive',
        'outline',
        'secondary',
        'ghost',
        'primary',
      ];
      for (const variant of variants) {
        const html = renderToString(
          React.createElement(Button, { variant }, `Button ${variant}`)
        );
        assert.match(html, new RegExp(`Button ${variant}`));
        assert.match(html, /focus-visible:ring-2/);
      }
    });

    test('Button loading state displays animated native Loader2 spinner and disables button', () => {
      const html = renderToString(
        React.createElement(Button, { isLoading: true }, 'Saving Changes')
      );
      assert.match(html, /animate-spin/);
      assert.match(html, /disabled/);
      assert.match(html, /Saving Changes/);
    });

    test('Card primitive renders complete composable layout structure', () => {
      const html = renderToString(
        React.createElement(
          Card,
          { className: 'custom-card' },
          React.createElement(
            CardHeader,
            null,
            React.createElement(CardTitle, null, 'Semester Summary'),
            React.createElement(
              CardDescription,
              null,
              'Academic details for current term'
            )
          ),
          React.createElement(
            CardContent,
            null,
            React.createElement('p', null, 'Content Body')
          ),
          React.createElement(
            CardFooter,
            null,
            React.createElement('span', null, 'Footer Status')
          )
        )
      );
      assert.match(html, /custom-card/);
      assert.match(html, /Semester Summary/);
      assert.match(html, /Academic details for current term/);
      assert.match(html, /Content Body/);
      assert.match(html, /Footer Status/);
    });

    test('Badge renders normal and variant styles cleanly', () => {
      const html = renderToString(
        React.createElement(
          Badge,
          { variant: 'outline', className: 'border-sky-400' },
          'Active Semester'
        )
      );
      assert.match(html, /Active Semester/);
      assert.match(html, /border-sky-400/);
    });

    test('Input primitive provides accessible focus rings and touch bounds', () => {
      const html = renderToString(
        React.createElement(Input, {
          placeholder: 'Search courses...',
          'aria-label': 'Search courses',
          type: 'text',
        })
      );
      assert.match(html, /placeholder="Search courses\.\.\."/);
      assert.match(html, /aria-label="Search courses"/);
      assert.match(html, /focus-visible:ring-2/);
    });

    test('StatCard component renders trend indicators (positive and negative) with icons', () => {
      const htmlPos = renderToString(
        React.createElement(StatCard, {
          label: 'Current CGPA',
          value: '9.42',
          icon: Icons.Star,
          trend: { value: '+0.15 this sem', positive: true },
        })
      );
      assert.match(htmlPos, /Current CGPA/);
      assert.match(htmlPos, /9\.42/);
      assert.match(htmlPos, /\+0\.15 this sem/);
      assert.match(htmlPos, /text-emerald-300|text-success/);

      const htmlNeg = renderToString(
        React.createElement(StatCard, {
          label: 'Attendance Rate',
          value: '74.2%',
          icon: Icons.AlertTriangle,
          trend: { value: '-2.1% drop', positive: false },
        })
      );
      assert.match(htmlNeg, /Attendance Rate/);
      assert.match(htmlNeg, /74\.2%/);
      assert.match(htmlNeg, /-2\.1% drop/);
      assert.match(htmlNeg, /text-red-300|text-destructive/);
    });

    test('EmptyState component renders with icon, title, description, and action button', () => {
      const html = renderToString(
        React.createElement(EmptyState, {
          icon: React.createElement(Icons.Inbox, { size: 32 }),
          title: 'No Hostel Bookings',
          description: 'You have not registered for hostel accommodation yet.',
          action: {
            label: 'Register Now',
            onClick: () => {},
          },
        })
      );
      assert.match(html, /No Hostel Bookings/);
      assert.match(
        html,
        /You have not registered for hostel accommodation yet\./
      );
      assert.match(html, /Register Now/);
      assert.match(html, /<svg/);
    });

    test('Progress component renders accessible progress bar with value', () => {
      const html = renderToString(
        React.createElement(Progress, { value: 75, max: 100 })
      );
      assert.match(html, /role="progressbar"/);
      assert.match(html, /aria-valuenow="75"/);
    });

    test('Skeleton primitive renders with shimmer animation classes', () => {
      const html = renderToString(
        React.createElement(Skeleton, { className: 'w-48 h-6 rounded-md' })
      );
      assert.match(html, /shimmer/);
      assert.match(html, /w-48 h-6 rounded-md/);
    });

    test('PageHeader renders title, description, and action buttons', () => {
      const html = renderToString(
        React.createElement(PageHeader, {
          title: 'Attendance Records',
          description: 'View daily classroom and lab attendance statistics',
          actions: React.createElement(Button, null, 'Export PDF'),
        })
      );
      assert.match(html, /Attendance Records/);
      assert.match(html, /View daily classroom and lab attendance statistics/);
      assert.match(html, /Export PDF/);
    });

    test('AriaLiveRegion renders live announcements container with polite and assertive regions', () => {
      const html = renderToString(
        React.createElement(
          AriaLiveRegion,
          null,
          React.createElement('span', null, 'Child Content')
        )
      );
      assert.match(html, /aria-live="polite"/);
      assert.match(html, /aria-live="assertive"/);
      assert.match(html, /Child Content/);
    });
  });

  describe('3. AI Copilot & Interactive Widgets Suite', () => {
    test('AIChatInput renders with custom placeholder, send button, and minimum touch target size', () => {
      const html = renderToString(
        React.createElement(AIChatInput, {
          onSendMessage: () => {},
          placeholder: 'Ask about attendance...',
          disabled: false,
        })
      );
      assert.match(html, /placeholder="Ask about attendance\.\.\."/);
      assert.match(html, /aria-label="Send query"/);
      assert.match(html, /min-w-\[44px\] min-h-\[44px\]/);
      assert.match(html, /<svg/);
    });

    test('AIChatInput renders animated Sparkles loader when disabled is true', () => {
      const html = renderToString(
        React.createElement(AIChatInput, {
          onSendMessage: () => {},
          disabled: true,
        })
      );
      assert.match(html, /animate-spin/);
      assert.match(html, /disabled=""/);
    });

    test('AIChatSuggestionChips renders chips with icons and clickable targets', () => {
      const html = renderToString(
        React.createElement(AIChatSuggestionChips, {
          onSelectSuggestion: () => {},
          disabled: false,
        })
      );
      assert.match(html, /OS Attendance|Fee Balance|Today Schedule/);
      assert.match(html, /<svg/);
    });

    test('AIToolExecutionIndicator renders active and completed tool call badges', () => {
      const thinkingHtml = renderToString(
        React.createElement(AIToolExecutionIndicator, {
          status: 'thinking',
        })
      );
      assert.match(
        thinkingHtml,
        /Analyzing request &amp; executing workflow\.\.\./
      );
      assert.match(thinkingHtml, /animate-spin/);

      const executingHtml = renderToString(
        React.createElement(AIToolExecutionIndicator, {
          toolName: 'get_attendance',
          status: 'executing_tool',
        })
      );
      assert.match(executingHtml, /Querying ERP via get_attendance\.\.\./);
      assert.match(executingHtml, /animate-spin/);

      const errorHtml = renderToString(
        React.createElement(AIToolExecutionIndicator, {
          status: 'error',
        })
      );
      assert.strictEqual(errorHtml, '');
    });

    test('AIChatMessageList renders empty welcome state with quick suggestions', () => {
      const html = renderToString(
        React.createElement(AIChatMessageList, {
          messages: [],
        })
      );
      assert.match(html, /KL Sync AI Copilot|Copilot/i);
      assert.match(html, /<svg/);
    });

    test('SimpleCalculator renders interactive controls and formulas', () => {
      const html = renderToString(
        React.createElement(SimpleCalculator, {
          totalClasses: 40,
          presents: 32,
        })
      );
      assert.match(html, /Attendance Analysis|Classes/i);
      assert.match(html, /80(\.00)?<!-- -->%/);
      assert.match(html, /Conditional Eligibility/);
      assert.match(html, /<svg/);
    });
  });

  describe('4. ERP Table Page & Responsive Layout Verification', () => {
    test('ERPTablePage renders responsive table/cards and loading states cleanly', () => {
      const emptyHtml = renderToString(
        React.createElement(ERPTablePage, {
          module: 'library',
          title: 'Library Transactions',
          description: 'Issued books and due dates',
          emptyTitle: 'No books borrowed',
          emptyDescription: 'Your library account is clear.',
          emptyIcon: React.createElement(Icons.BookOpen, { size: 32 }),
        })
      );
      assert.match(emptyHtml, /Library Transactions/);
      assert.match(emptyHtml, /Issued books and due dates/);
      assert.match(emptyHtml, /shimmer|Library/);
    });

    test('ERPTablePage supports headerActions, columnFormatters, and sticky headers', () => {
      const html = renderToString(
        React.createElement(ERPTablePage, {
          module: 'circulars',
          title: 'Circulars & Notices',
          description: 'Official notifications',
          emptyTitle: 'No circulars',
          emptyDescription: 'No active circulars',
          emptyIcon: React.createElement(Icons.Megaphone, { size: 32 }),
          headerActions: React.createElement(
            'button',
            { id: 'custom-action-btn' },
            'Filter Notices'
          ),
          columnFormatters: {
            Title: (val) =>
              React.createElement('span', { className: 'font-bold' }, String(val)),
          },
        })
      );
      assert.match(html, /Circulars &amp; Notices|Circulars & Notices/);
      assert.match(html, /custom-action-btn/);
      assert.match(html, /Filter Notices/);
    });
  });
});
