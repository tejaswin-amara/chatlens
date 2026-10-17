import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { Badge, BadgeProps } from '../src/components/ui/badge';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardProps,
} from '../src/components/ui/card';

describe('Challenger M2: Badge & Card Deep Edge Case Verification', () => {
  describe('Badge Component', () => {
    const ALL_VARIANTS: NonNullable<BadgeProps['variant']>[] = [
      'default',
      'secondary',
      'success',
      'warning',
      'danger',
      'destructive',
      'info',
      'outline',
      'emerald',
      'present',
      'absent',
      'pending',
      'neutral',
      'glass',
    ];

    it('renders all 14 variants without undefined classes', () => {
      for (const variant of ALL_VARIANTS) {
        const html = renderToString(
          React.createElement(Badge, { variant }, `Variant: ${variant}`)
        );
        assert.ok(
          html.startsWith('<span'),
          `${variant} should render a <span>`
        );
        assert.ok(
          !html.includes('undefined'),
          `${variant} output contains 'undefined': ${html}`
        );
        assert.ok(
          !html.includes('null'),
          `${variant} output contains 'null': ${html}`
        );
        assert.match(
          html,
          new RegExp(`Variant: ${variant}`),
          `${variant} should render children`
        );
      }
    });

    it('applies correct variant styles for each variant', () => {
      const variantExpectations: Record<
        NonNullable<BadgeProps['variant']>,
        string
      > = {
        default: 'bg-surface-2',
        secondary: 'bg-secondary',
        success: 'bg-success/15',
        warning: 'bg-warning/15',
        danger: 'bg-destructive/15',
        destructive: 'bg-destructive/15',
        info: 'bg-primary/15',
        outline: 'bg-transparent',
        emerald: 'bg-success/15',
        present: 'bg-success/15',
        absent: 'bg-error/10',
        pending: 'bg-warning/15',
        neutral: 'bg-surface-2',
        glass: 'apple-card',
      };

      for (const [variant, expectedClass] of Object.entries(
        variantExpectations
      )) {
        const html = renderToString(
          React.createElement(
            Badge,
            { variant: variant as BadgeProps['variant'] },
            variant
          )
        );
        assert.ok(
          html.includes(expectedClass),
          `Variant ${variant} missing expected class ${expectedClass}`
        );
      }
    });

    it('renders all size variants (sm, md, lg) and defaults to md', () => {
      const smHtml = renderToString(
        React.createElement(Badge, { size: 'sm' }, 'Small')
      );
      assert.ok(
        smHtml.includes('text-[10px]'),
        'sm size should have text-[10px]'
      );
      assert.ok(
        smHtml.includes('px-2 py-0.5'),
        'sm size should have px-2 py-0.5'
      );

      const mdHtml = renderToString(
        React.createElement(Badge, { size: 'md' }, 'Medium')
      );
      assert.ok(
        mdHtml.includes('text-[11px]'),
        'md size should have text-[11px]'
      );
      assert.ok(
        mdHtml.includes('px-2.5 py-1'),
        'md size should have px-2.5 py-1'
      );

      const lgHtml = renderToString(
        React.createElement(Badge, { size: 'lg' }, 'Large')
      );
      assert.ok(lgHtml.includes('text-xs'), 'lg size should have text-xs');
      assert.ok(
        lgHtml.includes('px-3 py-1.5'),
        'lg size should have px-3 py-1.5'
      );

      const defaultHtml = renderToString(
        React.createElement(Badge, null, 'Default Size')
      );
      assert.ok(
        defaultHtml.includes('text-[11px]'),
        'default size should be md (text-[11px])'
      );
    });

    it('renders dot indicator with semantic color mappings and default fallback', () => {
      const dotExpectations: Record<string, string> = {
        success: 'bg-success',
        emerald: 'bg-success',
        present: 'bg-success',
        warning: 'bg-warning',
        pending: 'bg-warning',
        danger: 'bg-destructive',
        destructive: 'bg-destructive',
        absent: 'bg-destructive',
        info: 'bg-primary',
        default: 'bg-muted-foreground',
        secondary: 'bg-muted-foreground',
        outline: 'bg-muted-foreground',
        neutral: 'bg-muted-foreground',
        glass: 'bg-muted-foreground',
      };

      for (const [variant, expectedDotColor] of Object.entries(
        dotExpectations
      )) {
        const html = renderToString(
          React.createElement(
            Badge,
            { variant: variant as BadgeProps['variant'], dot: true },
            variant
          )
        );
        assert.ok(
          html.includes('w-1.5 h-1.5 rounded-full shrink-0'),
          `${variant} dot missing base dot classes`
        );
        assert.ok(
          html.includes(expectedDotColor),
          `${variant} dot missing color ${expectedDotColor}`
        );
      }
    });

    it('handles pulse prop with and without dot', () => {
      const pulseNoDot = renderToString(
        React.createElement(Badge, { pulse: true }, 'Pulsing')
      );
      assert.ok(
        pulseNoDot.includes('animate-pulse'),
        'Badge should have animate-pulse on container'
      );
      assert.ok(
        !pulseNoDot.includes('animate-ping'),
        'Badge without dot should not have animate-ping'
      );

      const pulseWithDot = renderToString(
        React.createElement(Badge, { pulse: true, dot: true }, 'Pulsing Dot')
      );
      assert.ok(
        pulseWithDot.includes('animate-pulse'),
        'Badge should have animate-pulse'
      );
      assert.ok(
        pulseWithDot.includes('animate-ping'),
        'Dot should have animate-ping'
      );
    });

    it('renders icon slot correctly', () => {
      const mockIcon = React.createElement('svg', {
        'data-testid': 'custom-icon',
      });
      const html = renderToString(
        React.createElement(Badge, { icon: mockIcon }, 'With Icon')
      );
      assert.ok(
        html.includes('shrink-0 flex items-center'),
        'Icon container should have flex alignment classes'
      );
      assert.ok(
        html.includes('data-testid="custom-icon"'),
        'Custom icon should be rendered'
      );
    });

    it('merges custom className and passes through HTML attributes', () => {
      const html = renderToString(
        React.createElement(
          Badge,
          {
            className: 'custom-challenger-class my-3',
            id: 'badge-id-123',
            'aria-label': 'Custom Badge Label',
            ...({ 'data-testid': 'challenger-badge' } as Record<
              string,
              unknown
            >),
          } as BadgeProps,
          'Attributed'
        )
      );
      assert.ok(
        html.includes('custom-challenger-class'),
        'Custom class must be included'
      );
      assert.ok(html.includes('my-3'), 'Custom class must be included');
      assert.ok(
        html.includes('id="badge-id-123"'),
        'id must be passed through'
      );
      assert.ok(
        html.includes('aria-label="Custom Badge Label"'),
        'aria-label must be passed through'
      );
      assert.ok(
        html.includes('data-testid="challenger-badge"'),
        'data-testid must be passed through'
      );
    });

    it('forwards ref correctly on React element', () => {
      const ref = React.createRef<HTMLSpanElement>();
      const el = React.createElement(Badge, { ref }, 'Ref Test');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(Badge.displayName, 'Badge');
    });
  });

  describe('Card Component & Subcomponents', () => {
    const CARD_VARIANTS: NonNullable<CardProps['variant']>[] = [
      'default',
      'glass',
      'interactive',
      'elevated',
    ];

    it('renders all 4 Card variants without undefined classes', () => {
      const variantClassMap: Record<
        NonNullable<CardProps['variant']>,
        string
      > = {
        default: 'bg-surface-1 border border-border shadow-sm apple-card',
        glass: 'bg-surface-1/95 border border-border shadow-md apple-card',
        interactive:
          'bg-surface-1 border border-border shadow-sm cursor-pointer hover-lift hover:border-primary/25 hover:shadow-md transition-all apple-card',
        elevated: 'bg-surface-1 border border-border shadow-md apple-card',
      };

      for (const variant of CARD_VARIANTS) {
        const html = renderToString(
          React.createElement(Card, { variant }, `Card ${variant}`)
        );
        assert.ok(html.startsWith('<div'), `${variant} should render a <div>`);
        assert.ok(
          !html.includes('undefined'),
          `${variant} output contains undefined`
        );
        const expected = variantClassMap[variant];
        for (const cls of expected.split(' ')) {
          assert.ok(html.includes(cls), `Card ${variant} missing class ${cls}`);
        }
      }
    });

    it('Card defaults to default variant and forwards ref', () => {
      const html = renderToString(
        React.createElement(Card, null, 'Default Card')
      );
      assert.ok(
        html.includes('bg-surface-1'),
        'Default card should have bg-surface-1'
      );
      assert.ok(
        html.includes('border-border'),
        'Default card should have border-border'
      );

      const ref = React.createRef<HTMLDivElement>();
      const el = React.createElement(Card, { ref }, 'Ref Card');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(Card.displayName, 'Card');
    });

    it('renders CardHeader with correct classes and ref forwarding', () => {
      const html = renderToString(
        React.createElement(
          CardHeader,
          { className: 'extra-header' },
          'Header Content'
        )
      );
      assert.ok(html.startsWith('<div'), 'CardHeader must be a <div>');
      assert.ok(
        html.includes('flex flex-col gap-1.5 p-5 pb-3'),
        'CardHeader must have flex-col padding classes'
      );
      assert.ok(
        html.includes('extra-header'),
        'CardHeader must merge extra className'
      );

      const ref = React.createRef<HTMLDivElement>();
      const el = React.createElement(CardHeader, { ref }, 'Ref');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(CardHeader.displayName, 'CardHeader');
    });

    it('renders CardTitle as semantic h3 with font-heading and ref forwarding', () => {
      const html = renderToString(
        React.createElement(
          CardTitle,
          { className: 'title-custom' },
          'Title Text'
        )
      );
      assert.ok(html.startsWith('<h3'), 'CardTitle must be a semantic <h3>');
      assert.ok(
        html.includes(
          'font-heading text-base font-semibold leading-tight tracking-[-0.015em] text-foreground'
        ),
        'CardTitle classes'
      );
      assert.ok(html.includes('title-custom'), 'CardTitle custom class');
      assert.ok(
        html.includes('Title Text</h3>'),
        'CardTitle closing tag and text'
      );

      const ref = React.createRef<HTMLHeadingElement>();
      const el = React.createElement(CardTitle, { ref }, 'Ref');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(CardTitle.displayName, 'CardTitle');
    });

    it('renders CardDescription as semantic p with muted text and ref forwarding', () => {
      const html = renderToString(
        React.createElement(
          CardDescription,
          { className: 'desc-custom' },
          'Description Text'
        )
      );
      assert.ok(
        html.startsWith('<p'),
        'CardDescription must be a semantic <p>'
      );
      assert.ok(
        html.includes('text-xs'),
        'CardDescription classes'
      );
      assert.ok(
        html.includes('text-muted-foreground'),
        'CardDescription muted text'
      );
      assert.ok(
        html.includes('leading-relaxed'),
        'CardDescription leading'
      );
      assert.ok(html.includes('desc-custom'), 'CardDescription custom class');
      assert.ok(
        html.includes('Description Text</p>'),
        'CardDescription closing tag and text'
      );

      const ref = React.createRef<HTMLParagraphElement>();
      const el = React.createElement(CardDescription, { ref }, 'Ref');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(CardDescription.displayName, 'CardDescription');
    });

    it('renders CardContent with p-5 pt-0 and ref forwarding', () => {
      const html = renderToString(
        React.createElement(
          CardContent,
          { className: 'content-custom' },
          'Body Content'
        )
      );
      assert.ok(html.startsWith('<div'), 'CardContent must be a <div>');
      assert.ok(html.includes('p-5 pt-0'), 'CardContent padding classes');
      assert.ok(html.includes('content-custom'), 'CardContent custom class');

      const ref = React.createRef<HTMLDivElement>();
      const el = React.createElement(CardContent, { ref }, 'Ref');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(CardContent.displayName, 'CardContent');
    });

    it('renders CardFooter with border-t and ref forwarding', () => {
      const html = renderToString(
        React.createElement(
          CardFooter,
          { className: 'footer-custom' },
          'Footer Content'
        )
      );
      assert.ok(html.startsWith('<div'), 'CardFooter must be a <div>');
      assert.ok(
        html.includes('flex items-center') &&
          html.includes('border-t') &&
          html.includes('border-border/70'),
        'CardFooter classes'
      );
      assert.ok(html.includes('footer-custom'), 'CardFooter custom class');

      const ref = React.createRef<HTMLDivElement>();
      const el = React.createElement(CardFooter, { ref }, 'Ref');
      assert.strictEqual(el.props.ref, ref);
      assert.strictEqual(CardFooter.displayName, 'CardFooter');
    });

    it('renders full composed Card tree with nested Badge and custom props', () => {
      const tree = React.createElement(
        Card,
        {
          variant: 'interactive',
          id: 'profile-card',
          ...({ 'data-testid': 'profile-card-test' } as Record<
            string,
            unknown
          >),
        } as CardProps,
        React.createElement(
          CardHeader,
          null,
          React.createElement(CardTitle, null, 'Student Attendance Profile'),
          React.createElement(
            CardDescription,
            null,
            'Academic Year 2025-2026 Semester 1'
          )
        ),
        React.createElement(
          CardContent,
          null,
          React.createElement(
            Badge,
            { variant: 'success', dot: true, pulse: true },
            'Eligible for Exams'
          ),
          React.createElement(
            Badge,
            { variant: 'present', size: 'sm' },
            '88.5%'
          )
        ),
        React.createElement(
          CardFooter,
          null,
          React.createElement('span', null, 'Last updated: 5 mins ago')
        )
      );

      const html = renderToString(tree);
      assert.ok(html.includes('id="profile-card"'));
      assert.ok(html.includes('data-testid="profile-card-test"'));
      assert.ok(html.includes('Student Attendance Profile</h3>'));
      assert.ok(html.includes('Academic Year 2025-2026 Semester 1</p>'));
      assert.ok(html.includes('Eligible for Exams'));
      assert.ok(html.includes('88.5%'));
      assert.ok(html.includes('Last updated: 5 mins ago'));
      assert.ok(html.includes('cursor-pointer') && html.includes('hover-lift'));
      assert.ok(!html.includes('undefined'));
    });
  });
});
