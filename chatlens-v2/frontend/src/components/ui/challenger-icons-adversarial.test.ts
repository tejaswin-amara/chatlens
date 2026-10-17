import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

import * as Icons from './icons';
import { Button } from './button';
import { EmptyState } from './empty-state';
import { StatCard } from './stat-card';
import { Toast } from './toast';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './sheet';
import { Select } from './select';
import { AIChatInput } from '../ai/AIChatInput';
import { AIToolExecutionIndicator } from '../ai/AIToolExecutionIndicator';
import { AIChatSuggestionChips } from '../ai/AIChatSuggestionChips';
import { SimpleCalculator } from '../attendance-calculator';

describe('Empirical Challenger Suite: Native SVG Icons & Component Migrations', () => {
  const REQUIRED_55_ICONS: Array<keyof typeof Icons> = [
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

  describe('Suite 1: Icon Inventory, Names & Export Integrity', () => {
    test('all 55 required icons are exported, defined, and have valid forwardRef and displayName', () => {
      assert.strictEqual(
        REQUIRED_55_ICONS.length,
        55,
        'Should have exactly 55 required icons in list'
      );

      for (const name of REQUIRED_55_ICONS) {
        const IconComponent = Icons[
          name
        ] as React.ForwardRefExoticComponent<Icons.IconProps>;
        assert.ok(IconComponent, `Icon ${name} must be exported`);
        assert.strictEqual(
          typeof IconComponent,
          'object',
          `Icon ${name} must be a forwardRef object`
        );
        assert.strictEqual(
          IconComponent.displayName,
          name,
          `Icon ${name} displayName must match`
        );
        assert.ok(
          React.isValidElement(React.createElement(IconComponent)),
          `React.createElement(${name}) must be valid element`
        );
      }
    });

    test('CalendarIcon alias is exported and identically matches Calendar', () => {
      assert.ok(Icons.CalendarIcon, 'CalendarIcon must be exported');
      assert.strictEqual(
        Icons.CalendarIcon,
        Icons.Calendar,
        'CalendarIcon must be exact alias of Calendar'
      );
    });
  });

  describe('Suite 2: SVG Element Syntax & Attribute Compliance Across All 55 Icons', () => {
    test('every icon renders valid SVG with correct standard XML attributes, viewBox, and stroke styling', () => {
      for (const name of REQUIRED_55_ICONS) {
        const IconComponent = Icons[name] as Icons.LucideIcon;
        const html = renderToString(React.createElement(IconComponent));

        // SVG wrapper check
        assert.ok(
          html.startsWith('<svg'),
          `${name}: output must start with <svg`
        );
        assert.ok(
          html.endsWith('</svg>'),
          `${name}: output must end with </svg>`
        );

        // Standard attributes check
        assert.match(
          html,
          /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/,
          `${name}: missing xmlns`
        );
        assert.match(html, /viewBox="0 0 24 24"/, `${name}: invalid viewBox`);
        assert.match(html, /fill="none"/, `${name}: missing fill="none"`);
        assert.match(
          html,
          /stroke="currentColor"/,
          `${name}: missing stroke="currentColor"`
        );
        assert.match(
          html,
          /stroke-width="2"/,
          `${name}: missing default stroke-width="2"`
        );
        assert.match(
          html,
          /stroke-linecap="round"/,
          `${name}: missing stroke-linecap="round"`
        );
        assert.match(
          html,
          /stroke-linejoin="round"/,
          `${name}: missing stroke-linejoin="round"`
        );
        assert.match(html, /width="24"/, `${name}: missing default width="24"`);
        assert.match(
          html,
          /height="24"/,
          `${name}: missing default height="24"`
        );

        // Ensure child elements exist (not an empty SVG)
        const innerContent = html
          .replace(/<svg[^>]*>/, '')
          .replace(/<\/svg>/, '')
          .trim();
        assert.ok(
          innerContent.length > 0,
          `${name}: SVG inner content must not be empty`
        );
        assert.match(
          innerContent,
          /<(path|circle|polyline|line|polygon|rect)\b/,
          `${name}: must contain valid SVG child shapes`
        );
      }
    });
  });

  describe('Suite 3: Adversarial Props, Sizing & Stroke Dimensions', () => {
    test('handles numeric size prop across various scales', () => {
      const sizes = [0, 8, 12, 16, 20, 24, 32, 48, 64, 128];
      for (const s of sizes) {
        const html = renderToString(
          React.createElement(Icons.Sparkles, { size: s })
        );
        assert.match(
          html,
          new RegExp(`width="${s}"`),
          `Numeric size ${s} must set width`
        );
        assert.match(
          html,
          new RegExp(`height="${s}"`),
          `Numeric size ${s} must set height`
        );
      }
    });

    test('handles string size prop (units: rem, em, px, %)', () => {
      const stringSizes = [
        '1.5rem',
        '2em',
        '36px',
        '100%',
        'calc(100% - 10px)',
      ];
      for (const s of stringSizes) {
        const html = renderToString(
          React.createElement(Icons.Activity, { size: s })
        );
        assert.ok(
          html.includes(`width="${s}"`),
          `String size ${s} must be reflected in width`
        );
        assert.ok(
          html.includes(`height="${s}"`),
          `String size ${s} must be reflected in height`
        );
      }
    });

    test('explicit width and height props override size prop with highest precedence', () => {
      // 1. Both width and height override size
      const html1 = renderToString(
        React.createElement(Icons.Award, { size: 24, width: 40, height: 60 })
      );
      assert.match(html1, /width="40"/);
      assert.match(html1, /height="60"/);

      // 2. Only width specified -> height falls back to size (or default)
      const html2 = renderToString(
        React.createElement(Icons.Award, { size: 16, width: 32 })
      );
      assert.match(html2, /width="32"/);
      assert.match(html2, /height="16"/);

      // 3. Only height specified -> width falls back to default 24
      const html3 = renderToString(
        React.createElement(Icons.Award, { height: 48 })
      );
      assert.match(html3, /width="24"/);
      assert.match(html3, /height="48"/);
    });

    test('supports custom strokeWidth values as numbers and strings', () => {
      const html1 = renderToString(
        React.createElement(Icons.Search, { strokeWidth: 1.5 })
      );
      assert.match(html1, /stroke-width="1.5"/);

      const html2 = renderToString(
        React.createElement(Icons.Search, { strokeWidth: 3 })
      );
      assert.match(html2, /stroke-width="3"/);

      const html3 = renderToString(
        React.createElement(Icons.Search, { strokeWidth: '2.25' })
      );
      assert.match(html3, /stroke-width="2.25"/);
    });
  });

  describe('Suite 4: Class Names, Tailwind Animations, Loader2 Spinner & Accessibility', () => {
    test('className handles complex Tailwind classes, empty string, and omitted className', () => {
      // 1. Complex classes
      const html1 = renderToString(
        React.createElement(Icons.ChevronRight, {
          className:
            'w-4 h-4 text-emerald-400 group-hover:translate-x-1 transition-transform',
        })
      );
      assert.match(
        html1,
        /class="w-4 h-4 text-emerald-400 group-hover:translate-x-1 transition-transform"/
      );

      // 2. Empty className
      const html2 = renderToString(
        React.createElement(Icons.ChevronRight, { className: '' })
      );
      assert.doesNotMatch(html2, /class="undefined"/);

      // 3. Omitted className -> defaults to empty string, no class="undefined"
      const html3 = renderToString(React.createElement(Icons.ChevronRight));
      assert.doesNotMatch(html3, /class="undefined"/);
    });

    test('Loader2 spinner renders Lucide-compatible arc and supports animate-spin', () => {
      const html = renderToString(
        React.createElement(Icons.Loader2, {
          className: 'w-5 h-5 animate-spin text-primary',
        })
      );
      assert.match(html, /class="w-5 h-5 animate-spin text-primary"/);
      // Verify the arc path d="M21 12a9 9 0 1 1-6.219-8.56"
      assert.match(html, /d="M21 12a9 9 0 1 1-6\.219-8\.56"/);
    });

    test('passes through accessibility attributes, data-* attributes, IDs and styles', () => {
      const html = renderToString(
        React.createElement(Icons.Lock, {
          'aria-hidden': 'true',
          'aria-label': 'Security Lock',
          role: 'img',
          id: 'auth-lock-svg',
          style: { opacity: 0.8, color: '#38bdf8' },
          ...({
            'data-testid': 'custom-lock-icon',
            'data-state': 'locked',
          } as Record<string, unknown>),
        })
      );
      assert.match(html, /aria-hidden="true"/);
      assert.match(html, /aria-label="Security Lock"/);
      assert.match(html, /role="img"/);
      assert.match(html, /data-testid="custom-lock-icon"/);
      assert.match(html, /data-state="locked"/);
      assert.match(html, /id="auth-lock-svg"/);
      assert.match(html, /style="opacity:0\.8;color:#38bdf8"/);
    });
  });

  describe('Suite 5: Ref Forwarding Capability', () => {
    test('component supports React ref forwarding without console warnings or runtime exceptions', () => {
      const TestWrapper = () => {
        const iconRef = React.useRef<SVGSVGElement>(null);
        return React.createElement(Icons.ShieldCheck, {
          ref: iconRef,
          id: 'ref-test-icon',
        });
      };

      const html = renderToString(React.createElement(TestWrapper));
      assert.match(html, /id="ref-test-icon"/);
    });
  });

  describe('Suite 6: Consumer UI Primitives Integration', () => {
    test('Button component renders Loader2 icon cleanly when isLoading is true', () => {
      const html = renderToString(
        React.createElement(Button, { isLoading: true }, 'Submitting...')
      );
      assert.match(html, /animate-spin/);
      assert.match(html, /Submitting\.\.\./);
      assert.match(html, /disabled/);
    });

    test('StatCard component renders passed native icon cleanly', () => {
      const html = renderToString(
        React.createElement(StatCard, {
          label: 'Total Attendance',
          value: '87.5%',
          icon: Icons.Award,
          trend: { value: 'Above target threshold' },
        })
      );
      assert.match(html, /Total Attendance/);
      assert.match(html, /87\.5%/);
      assert.match(html, /<svg/);
    });

    test('EmptyState component renders passed native icon cleanly', () => {
      const html = renderToString(
        React.createElement(EmptyState, {
          title: 'No Circulars Found',
          description: 'You are all caught up for this semester.',
          icon: React.createElement(Icons.Inbox, {
            className: 'w-10 h-10 text-muted-foreground',
          }),
        })
      );
      assert.match(html, /No Circulars Found/);
      assert.match(html, /You are all caught up for this semester\./);
      assert.match(html, /<svg/);
    });

    test('Toast component renders success and destructive native icons cleanly', () => {
      const successHtml = renderToString(
        React.createElement(Toast, {
          toast: {
            id: 'toast-1',
            title: 'Session Refreshed',
            description: 'ERP token successfully synchronized.',
            variant: 'success',
          },
          onDismiss: () => {},
        })
      );
      assert.match(successHtml, /Session Refreshed/);
      assert.match(successHtml, /<svg/);

      const errorHtml = renderToString(
        React.createElement(Toast, {
          toast: {
            id: 'toast-2',
            title: 'Sync Failed',
            description: 'Invalid credentials.',
            variant: 'destructive',
          },
          onDismiss: () => {},
        })
      );
      assert.match(errorHtml, /Sync Failed/);
      assert.match(errorHtml, /<svg/);
    });

    test('Dialog component renders X close icon', () => {
      const html = renderToString(
        React.createElement(
          Dialog,
          { open: true },
          React.createElement(
            DialogContent,
            null,
            React.createElement(
              DialogHeader,
              null,
              React.createElement(DialogTitle, null, 'Test Dialog')
            )
          )
        )
      );
      assert.match(html, /Test Dialog/);
      assert.match(html, /<svg/);
    });

    test('Sheet component renders X close icon', () => {
      const html = renderToString(
        React.createElement(
          Sheet,
          { open: true },
          React.createElement(
            SheetContent,
            null,
            React.createElement(
              SheetHeader,
              null,
              React.createElement(SheetTitle, null, 'Test Sheet')
            )
          )
        )
      );
      assert.match(html, /Test Sheet/);
      assert.match(html, /<svg/);
    });

    test('Select component renders ChevronDown icon', () => {
      const html = renderToString(
        React.createElement(Select, {
          options: [
            { value: '1', label: 'Semester 1' },
            { value: '2', label: 'Semester 2' },
          ],
          placeholder: 'Select Semester',
        })
      );
      assert.match(html, /Select Semester/);
      assert.match(html, /Semester 1/);
      assert.match(html, /<svg/);
    });

    test('Search icon renders cleanly as standalone SVG component', () => {
      const html = renderToString(
        React.createElement(Icons.Search, { className: 'w-4 h-4' })
      );
      assert.match(html, /<svg/);
      assert.match(html, /viewBox="0 0 24 24"/);
    });
  });

  describe('Suite 7: Advanced Feature Widgets & ERP Integrations', () => {
    test('AIChatInput renders Send icon in default state and Sparkles when disabled', () => {
      const normalHtml = renderToString(
        React.createElement(AIChatInput, {
          onSendMessage: () => {},
          disabled: false,
        })
      );
      assert.match(normalHtml, /<svg/);
      assert.match(normalHtml, /Send query/);

      const disabledHtml = renderToString(
        React.createElement(AIChatInput, {
          onSendMessage: () => {},
          disabled: true,
        })
      );
      assert.match(disabledHtml, /animate-spin/);
    });

    test('AIToolExecutionIndicator renders Loader2 icon with animation', () => {
      const executingHtml = renderToString(
        React.createElement(AIToolExecutionIndicator, {
          status: 'executing_tool',
          toolName: 'getAttendance',
        })
      );
      assert.match(executingHtml, /Querying ERP via getAttendance\.\.\./);
      assert.match(executingHtml, /animate-spin/);

      const thinkingHtml = renderToString(
        React.createElement(AIToolExecutionIndicator, { status: 'thinking' })
      );
      assert.match(
        thinkingHtml,
        /Analyzing request &amp; executing workflow\.\.\./
      );
    });

    test('AIChatSuggestionChips renders all 5 suggestion icons (BookOpen, DollarSign, Calendar, Target, Award)', () => {
      const html = renderToString(
        React.createElement(AIChatSuggestionChips, {
          onSelectSuggestion: () => {},
        })
      );
      assert.match(html, /OS Attendance/);
      assert.match(html, /Fee Balance/);
      assert.match(html, /Today Schedule/);
      assert.match(html, /Target 75%/);
      assert.match(html, /Predict CGPA/);
      // Ensure 5 SVGs rendered
      const svgMatches = html.match(/<svg/g);
      assert.strictEqual(svgMatches?.length, 5, 'Should render 5 SVG chips');
    });

    test('SimpleCalculator renders status icons for eligible, warning, and detention states', () => {
      // 1. Eligible (>= 85%) -> CheckCircle2
      const eligibleHtml = renderToString(
        React.createElement(SimpleCalculator, {
          totalClasses: 100,
          presents: 90,
        })
      );
      assert.match(eligibleHtml, /Eligible/);
      assert.match(eligibleHtml, /<svg/);

      // 2. Warning (75-85%) -> AlertCircle
      const warningHtml = renderToString(
        React.createElement(SimpleCalculator, {
          totalClasses: 100,
          presents: 78,
        })
      );
      assert.match(warningHtml, /Conditional Eligibility/);
      assert.match(warningHtml, /<svg/);

      // 3. Danger (< 75%) -> XCircle
      const dangerHtml = renderToString(
        React.createElement(SimpleCalculator, {
          totalClasses: 100,
          presents: 60,
        })
      );
      assert.match(dangerHtml, /Not Eligible/);
      assert.match(dangerHtml, /<svg/);
    });
  });

  describe('Suite 8: SVG Geometric Integrity & Shape Sanity', () => {
    test('none of the 55 icons contain corrupted attributes, NaN values, or undefined strings', () => {
      for (const name of REQUIRED_55_ICONS) {
        const IconComponent = Icons[name] as Icons.LucideIcon;
        const html = renderToString(React.createElement(IconComponent));

        assert.doesNotMatch(html, /NaN/, `${name} rendered NaN`);
        assert.doesNotMatch(html, /undefined/, `${name} rendered undefined`);
        assert.doesNotMatch(
          html,
          /\[object Object\]/,
          `${name} rendered [object Object]`
        );
        assert.doesNotMatch(html, /null/, `${name} rendered null attribute`);
      }
    });
  });
});
