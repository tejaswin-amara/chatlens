import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

import * as Icons from './icons';

describe('Native SVG Icons Suite - Ponytail R2 Verification', () => {
  const iconNames: Array<keyof typeof Icons> = [
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

  test('all 55 required icons are exported and defined', () => {
    assert.strictEqual(iconNames.length, 55);
    for (const name of iconNames) {
      const Component = Icons[name];
      assert.ok(Component, `Icon ${name} should be exported`);
      assert.strictEqual(
        typeof Component,
        'object',
        `Icon ${name} should be a forwardRef component`
      );
    }
  });

  test('CalendarIcon alias is exported and matches Calendar', () => {
    assert.ok(Icons.CalendarIcon);
    assert.strictEqual(Icons.CalendarIcon, Icons.Calendar);
  });

  test('all 55 icons render valid SVG elements with standard attributes', () => {
    for (const name of iconNames) {
      const IconComponent = Icons[name] as Icons.LucideIcon;
      const html = renderToString(React.createElement(IconComponent));
      assert.match(
        html,
        /<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/,
        `${name} missing svg tag or xmlns`
      );
      assert.match(html, /viewBox="0 0 24 24"/, `${name} missing viewBox`);
      assert.match(html, /fill="none"/, `${name} missing fill="none"`);
      assert.match(
        html,
        /stroke="currentColor"/,
        `${name} missing stroke="currentColor"`
      );
      assert.match(
        html,
        /stroke-width="2"/,
        `${name} missing default stroke-width="2"`
      );
      assert.match(html, /width="24"/, `${name} missing default width="24"`);
      assert.match(html, /height="24"/, `${name} missing default height="24"`);
    }
  });

  test('supports custom size, width, height, and strokeWidth props', () => {
    const html1 = renderToString(
      React.createElement(Icons.Sparkles, { size: 32 })
    );
    assert.match(html1, /width="32"/);
    assert.match(html1, /height="32"/);

    const html2 = renderToString(
      React.createElement(Icons.Sparkles, { width: 16, height: 16 })
    );
    assert.match(html2, /width="16"/);
    assert.match(html2, /height="16"/);

    const html3 = renderToString(
      React.createElement(Icons.Activity, { strokeWidth: 1.5 })
    );
    assert.match(html3, /stroke-width="1.5"/);
  });

  test('supports custom className including Tailwind animation classes', () => {
    const html = renderToString(
      React.createElement(Icons.Loader2, {
        className: 'w-4 h-4 animate-spin text-sky-400',
      })
    );
    assert.match(html, /class="w-4 h-4 animate-spin text-sky-400"/);
  });

  test('supports aria and role attributes for accessibility', () => {
    const html = renderToString(
      React.createElement(Icons.AlertCircle, {
        'aria-hidden': 'true',
        role: 'img',
      })
    );
    assert.match(html, /aria-hidden="true"/);
    assert.match(html, /role="img"/);
  });
});
