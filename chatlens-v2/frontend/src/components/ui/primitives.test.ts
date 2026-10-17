import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

import { Button } from './button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './card';
import { Input } from './input';
import { Badge } from './badge';
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
  useDialog,
} from './dialog';
import { Skeleton } from './skeleton';

describe('UI Primitives - Empirical Stress Testing & Verification', () => {
  describe('Button Component', () => {
    test('renders default button with 44px min-height touch target', () => {
      const html = renderToString(
        React.createElement(Button, null, 'Click Me')
      );
      assert.match(html, /min-h-\[44px\]/);
      assert.match(html, /type="button"/);
      assert.match(html, /bg-primary/);
      assert.match(html, /focus-visible:ring-2/);
      assert.match(html, /Click Me/);
    });

    test('supports icon size with 44px x 44px minimum touch target', () => {
      const html = renderToString(
        React.createElement(Button, { size: 'icon' }, 'X')
      );
      assert.match(html, /min-h-\[44px\]/);
      assert.match(html, /min-w-\[44px\]/);
    });

    test('supports lg size with 48px min-height touch target', () => {
      const html = renderToString(
        React.createElement(Button, { size: 'lg' }, 'Large Button')
      );
      assert.match(html, /min-h-\[48px\]/);
    });

    test('handles isLoading state by disabling button and rendering spinner', () => {
      const html = renderToString(
        React.createElement(Button, { isLoading: true }, 'Save')
      );
      assert.match(html, /disabled=""/);
      assert.match(html, /animate-spin/);
      assert.match(html, /Save/);
    });

    test('merges custom className cleanly via cn()', () => {
      const html = renderToString(
        React.createElement(Button, { className: 'custom-class-test' }, 'Test')
      );
      assert.match(html, /custom-class-test/);
      assert.match(html, /min-h-\[44px\]/);
    });

    test('renders destructive, secondary, outline, and ghost variants correctly', () => {
      const variants = [
        'destructive',
        'secondary',
        'outline',
        'ghost',
      ] as const;
      for (const variant of variants) {
        const html = renderToString(
          React.createElement(Button, { variant }, 'Variant')
        );
        assert.ok(html.length > 0);
      }
    });
  });

  describe('Input Component', () => {
    test('renders input with 44px min-height touch target and focus ring', () => {
      const html = renderToString(
        React.createElement(Input, { placeholder: 'Enter text...' })
      );
      assert.match(html, /min-h-\[44px\]/);
      assert.match(html, /bg-surface-2\/70/);
      assert.match(html, /focus-visible:ring-ring/);
    });

    test('renders leftIcon and applies ps-10 logical padding offset', () => {
      const icon = React.createElement('span', { id: 'search-icon' }, '🔍');
      const html = renderToString(
        React.createElement(Input, { leftIcon: icon })
      );
      assert.match(html, /search-icon/);
      assert.match(html, /ps-10/);
      assert.match(html, /pointer-events-none/);
    });

    test('renders rightIcon and applies pe-10 logical padding offset', () => {
      const icon = React.createElement('button', { id: 'clear-icon' }, '✕');
      const html = renderToString(
        React.createElement(Input, { rightIcon: icon })
      );
      assert.match(html, /clear-icon/);
      assert.match(html, /pe-10/);
    });

    test('renders error state with destructive border and focus ring', () => {
      const html = renderToString(React.createElement(Input, { error: true }));
      assert.match(html, /border-destructive\/50/);
      assert.match(html, /focus-visible:ring-destructive/);
    });
  });

  describe('Badge Component', () => {
    test('renders default badge with font and tracking styling', () => {
      const html = renderToString(React.createElement(Badge, null, 'Active'));
      assert.match(html, /tracking-wide/);
      assert.match(html, /Active/);
    });

    test('renders indicator dot when dot=true', () => {
      const html = renderToString(
        React.createElement(Badge, { variant: 'success', dot: true }, 'Online')
      );
      assert.match(html, /w-1.5 h-1.5/);
      assert.match(html, /bg-success/);
      assert.match(html, /Online/);
    });

    test('supports all variant color themes (success, warning, error, info, etc.)', () => {
      const variants = [
        'success',
        'warning',
        'danger',
        'info',
        'outline',
        'emerald',
      ] as const;
      for (const variant of variants) {
        const html = renderToString(
          React.createElement(Badge, { variant }, variant)
        );
        assert.ok(html.length > 0);
      }
    });
  });

  describe('Card Components', () => {
    test('renders Card with modern surface styles by default', () => {
      const html = renderToString(
        React.createElement(
          Card,
          null,
          React.createElement(
            CardHeader,
            null,
            React.createElement(CardTitle, null, 'Title')
          ),
          React.createElement(CardContent, null, 'Body Content'),
          React.createElement(CardFooter, null, 'Footer')
        )
      );
      assert.match(html, /bg-surface-1/);
      assert.match(html, /Title/);
      assert.match(html, /Body Content/);
      assert.match(html, /Footer/);
    });

    test('supports interactive variant with hover-lift effect', () => {
      const html = renderToString(
        React.createElement(Card, { variant: 'interactive' }, 'Clickable Card')
      );
      assert.match(html, /hover-lift/);
      assert.match(html, /cursor-pointer/);
    });
  });

  describe('Dialog Component', () => {
    test('throws error if useDialog is invoked outside Dialog context', () => {
      function BadComponent() {
        useDialog();
        return null;
      }
      assert.throws(
        () => renderToString(React.createElement(BadComponent)),
        /useDialog must be used within a Dialog/
      );
    });

    test('renders dialog trigger and hidden content when closed', () => {
      const html = renderToString(
        React.createElement(
          Dialog,
          { open: false },
          React.createElement(DialogTrigger, null, 'Open Modal'),
          React.createElement(
            DialogContent,
            null,
            React.createElement(
              DialogHeader,
              null,
              React.createElement(DialogTitle, null, 'Modal Title')
            ),
            React.createElement(DialogDescription, null, 'Modal Description')
          )
        )
      );
      assert.match(html, /Open Modal/);
      assert.doesNotMatch(html, /Modal Title/);
    });

    test('renders modal overlay and accessible role="dialog" when open', () => {
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
              React.createElement(DialogTitle, null, 'Modal Title')
            ),
            React.createElement(DialogDescription, null, 'Modal Description'),
            React.createElement(
              DialogFooter,
              null,
              React.createElement(DialogClose, null, 'Close')
            )
          )
        )
      );
      assert.match(html, /role="dialog"/);
      assert.match(html, /aria-modal="true"/);
      assert.match(html, /aria-label="Close dialog"/);
      assert.match(html, /Modal Title/);
      assert.match(html, /Modal Description/);
      assert.match(html, /Close/);
    });
  });

  describe('Skeleton Component', () => {
    test('renders rounded card loader with shimmer effect by default', () => {
      const html = renderToString(
        React.createElement(Skeleton, { className: 'h-12 w-full' })
      );
      assert.match(html, /shimmer/);
      assert.match(html, /h-12 w-full/);
    });
  });
});
