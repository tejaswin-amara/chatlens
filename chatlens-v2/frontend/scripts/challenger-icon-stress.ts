import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import * as fs from 'node:fs';
import * as path from 'node:path';

import * as Icons from '../src/components/ui/icons';
import { Button } from '../src/components/ui/button';
import { StatCard } from '../src/components/ui/stat-card';
import { EmptyState } from '../src/components/ui/empty-state';
import { Toast } from '../src/components/ui/toast';
import { Select } from '../src/components/ui/select';
import { AIChatInput } from '../src/components/ai/AIChatInput';
import { AIToolExecutionIndicator } from '../src/components/ai/AIToolExecutionIndicator';
import { AIChatSuggestionChips } from '../src/components/ai/AIChatSuggestionChips';
import {
  AIChatMessageList,
  ChatMessage,
} from '../src/components/ai/AIChatMessageList';
import { SimpleCalculator } from '../src/components/attendance-calculator';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../src/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '../src/components/ui/sheet';
import { Captcha } from '../src/components/Captcha';

const ICONS = [
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

console.log(
  '================================================================================'
);
console.log(
  '            🛡️  CHALLENGER EMPIRICAL ICON & REPO STRESS TEST                   '
);
console.log(
  '================================================================================\n'
);

let passCount = 0;
let failCount = 0;

function runCheck(title: string, fn: () => void) {
  try {
    fn();
    console.log(`  ✓ ${title}`);
    passCount++;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`  ✗ ${title}: ${message}`);
    failCount++;
  }
}

// 1. Icon Count
runCheck('[ICON-01] 55 Icon Definitions & CalendarIcon Alias', () => {
  assert.strictEqual(ICONS.length, 55, 'ICONS list must have exactly 55 names');
  for (const name of ICONS) {
    const Icon = Icons[
      name as keyof typeof Icons
    ] as React.ForwardRefExoticComponent<Icons.IconProps>;
    assert.ok(Icon, `Icon ${name} is not exported`);
    assert.strictEqual(
      typeof Icon,
      'object',
      `Icon ${name} should be React forwardRef object`
    );
    assert.strictEqual(
      Icon.displayName,
      name,
      `Icon ${name} displayName is ${Icon.displayName}, expected ${name}`
    );
  }
  assert.strictEqual(
    Icons.CalendarIcon,
    Icons.Calendar,
    'CalendarIcon must strictly equal Calendar'
  );
});

// 2. Default SVG Attributes
runCheck('[ICON-02] SVG Standard Attributes for All 55 Icons', () => {
  for (const name of ICONS) {
    const Icon = Icons[
      name as keyof typeof Icons
    ] as React.ComponentType<Icons.IconProps>;
    const html = renderToString(React.createElement(Icon));
    assert.match(html, /^<svg /, `${name} must render opening <svg`);
    assert.match(html, /<\/svg>$/, `${name} must render closing </svg>`);
    assert.match(
      html,
      /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/,
      `${name} missing xmlns`
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
    assert.match(
      html,
      /stroke-linecap="round"/,
      `${name} missing stroke-linecap="round"`
    );
    assert.match(
      html,
      /stroke-linejoin="round"/,
      `${name} missing stroke-linejoin="round"`
    );
    assert.match(html, /width="24"/, `${name} missing default width="24"`);
    assert.match(html, /height="24"/, `${name} missing default height="24"`);

    const hasGeometry = /<(path|circle|rect|line|polyline|polygon)/.test(html);
    assert.ok(hasGeometry, `${name} has no geometry children elements`);

    // Ensure no undefined or NaN values in rendered HTML
    assert.ok(
      !html.includes('undefined'),
      `${name} rendered undefined in HTML`
    );
    assert.ok(!html.includes('NaN'), `${name} rendered NaN in HTML`);
  }
});

// 3. Custom Sizes & Dimensions
runCheck(
  '[ICON-03] Size & Dimension Prop Variations (Number, String, Overrides)',
  () => {
    for (const name of ICONS) {
      const Icon = Icons[
        name as keyof typeof Icons
      ] as React.ComponentType<Icons.IconProps>;

      // Numeric size
      const numSize = renderToString(React.createElement(Icon, { size: 48 }));
      assert.match(numSize, /width="48"/, `${name} size=48 width`);
      assert.match(numSize, /height="48"/, `${name} size=48 height`);

      // String size
      const strSize = renderToString(
        React.createElement(Icon, { size: '1.75rem' })
      );
      assert.match(strSize, /width="1\.75rem"/, `${name} size='1.75rem' width`);
      assert.match(
        strSize,
        /height="1\.75rem"/,
        `${name} size='1.75rem' height`
      );

      // Width & Height overrides
      const override = renderToString(
        React.createElement(Icon, { size: 32, width: 18, height: 14 })
      );
      assert.match(override, /width="18"/, `${name} explicit width`);
      assert.match(override, /height="14"/, `${name} explicit height`);
    }
  }
);

// 4. Custom Styling & Animation Classes
runCheck('[ICON-04] ClassName Concatenation & Animation Classes', () => {
  for (const name of ICONS) {
    const Icon = Icons[
      name as keyof typeof Icons
    ] as React.ComponentType<Icons.IconProps>;
    const html = renderToString(
      React.createElement(Icon, {
        className: 'w-5 h-5 text-sky-400 animate-spin custom-class',
      })
    );
    assert.match(
      html,
      /class="w-5 h-5 text-sky-400 animate-spin custom-class"/,
      `${name} className not merged`
    );
  }
});

// 5. StrokeWidth Variations
runCheck('[ICON-05] StrokeWidth Prop Passing', () => {
  for (const name of ICONS) {
    const Icon = Icons[
      name as keyof typeof Icons
    ] as React.ComponentType<Icons.IconProps>;
    const html1 = renderToString(
      React.createElement(Icon, { strokeWidth: 1.5 })
    );
    assert.match(html1, /stroke-width="1\.5"/, `${name} strokeWidth=1.5`);

    const html3 = renderToString(React.createElement(Icon, { strokeWidth: 3 }));
    assert.match(html3, /stroke-width="3"/, `${name} strokeWidth=3`);
  }
});

// 6. SVG Attribute Passthrough & Accessibility
runCheck('[ICON-06] SVG Attribute Passthrough & Accessibility Props', () => {
  for (const name of ICONS) {
    const Icon = Icons[
      name as keyof typeof Icons
    ] as React.ComponentType<Icons.IconProps>;
    const html = renderToString(
      React.createElement(Icon, {
        'aria-label': `${name} icon`,
        'aria-hidden': 'true',
        role: 'img',
        id: `test-icon-${name}`,
        ...({ 'data-testid': `icon-${name}` } as Record<string, unknown>),
      })
    );
    assert.match(
      html,
      new RegExp(`aria-label="${name} icon"`),
      `${name} aria-label`
    );
    assert.match(html, /aria-hidden="true"/, `${name} aria-hidden`);
    assert.match(html, /role="img"/, `${name} role`);
    assert.match(html, new RegExp(`id="test-icon-${name}"`), `${name} id`);
    assert.match(
      html,
      new RegExp(`data-testid="icon-${name}"`),
      `${name} data-testid`
    );
  }
});

// 7. Lucide-React Dependency Elimination in package.json
runCheck('[REPO-01] Lucide-React Pruned from package.json', () => {
  const pkgPath = path.resolve(process.cwd(), 'package.json');
  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
  const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
  assert.ok(
    !('lucide-react' in deps),
    'lucide-react MUST NOT be present in package.json dependencies or devDependencies'
  );
});

// 8. Zero Lucide-React Imports Across ALL Source Files
runCheck('[REPO-02] Zero lucide-react imports across src/', () => {
  const srcDir = path.resolve(process.cwd(), 'src');
  function scan(dir: string): string[] {
    let results: string[] = [];
    const list = fs.readdirSync(dir);
    for (const file of list) {
      const full = path.join(dir, file);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) {
        results = results.concat(scan(full));
      } else if (/\.(tsx?|jsx?)$/.test(file) && !file.includes('test.ts')) {
        results.push(full);
      }
    }
    return results;
  }

  const files = scan(srcDir);
  const badFiles: string[] = [];
  for (const file of files) {
    const content = fs.readFileSync(file, 'utf-8');
    if (
      /from\s+['"]lucide-react['"]|require\(['"]lucide-react['"]\)/.test(
        content
      )
    ) {
      badFiles.push(file);
    }
  }
  assert.strictEqual(
    badFiles.length,
    0,
    `Found forbidden lucide-react imports in: ${badFiles.join(', ')}`
  );
});

// 9. Dead Wrapper AIChatDialog.tsx Deleted
runCheck('[REPO-03] AIChatDialog.tsx and references eliminated', () => {
  const dialogPath = path.resolve(
    process.cwd(),
    'src/components/ai/AIChatDialog.tsx'
  );
  assert.ok(
    !fs.existsSync(dialogPath),
    'src/components/ai/AIChatDialog.tsx should have been deleted'
  );

  const copilotPath = path.resolve(
    process.cwd(),
    'src/components/ai/AICopilot.tsx'
  );
  const copilotContent = fs.readFileSync(copilotPath, 'utf-8');
  assert.ok(
    !copilotContent.includes('AIChatDialog'),
    'AICopilot.tsx should not reference AIChatDialog'
  );
});

// 10. Dead Hook useERPData.ts Deleted
runCheck('[REPO-03B] useERPData.ts eliminated', () => {
  const erpHook = path.resolve(process.cwd(), 'src/hooks/useERPData.ts');
  assert.ok(
    !fs.existsSync(erpHook),
    'src/hooks/useERPData.ts should have been deleted'
  );
});

// 11. Scraper Dual Binding & Ponytail Debt
runCheck(
  '[REPO-04] Marks Scraper Parameter Dual-Binding & Zero Debt Comments',
  () => {
    const marksPath = path.resolve(process.cwd(), 'src/lib/scrapers/marks.ts');
    const marksContent = fs.readFileSync(marksPath, 'utf-8');
    assert.ok(
      !marksContent.includes('// ponytail:'),
      'marks.ts should contain 0 ponytail: debt comments'
    );
    assert.ok(
      marksContent.includes(
        "params.append('DynamicModel[semester]', semesterId)"
      ),
      'marks.ts missing DynamicModel[semester]'
    );
    assert.ok(
      marksContent.includes(
        "params.append('DynamicModel[semesterid]', semesterId)"
      ),
      'marks.ts missing DynamicModel[semesterid]'
    );
  }
);

// 12. Consumer Components Rendering
runCheck('[CONSUMER-01] UI Component Rendering with Native Icons', () => {
  // Button loading state
  const btnHtml = renderToString(
    React.createElement(Button, { isLoading: true }, 'Loading Button')
  );
  assert.match(
    btnHtml,
    /<svg/,
    'Button loading state should render Loader2 SVG'
  );
  assert.match(
    btnHtml,
    /animate-spin/,
    'Button loading state should have animate-spin'
  );

  // StatCard with Icon
  const statHtml = renderToString(
    React.createElement(StatCard, {
      label: 'CGPA',
      value: '9.42',
      icon: Icons.Award,
      trend: { value: '+0.15' },
    })
  );
  assert.match(statHtml, /CGPA/, 'StatCard renders label');
  assert.match(statHtml, /9\.42/, 'StatCard renders value');
  assert.match(statHtml, /<svg/, 'StatCard renders icon SVG');

  // EmptyState with Icon
  const emptyHtml = renderToString(
    React.createElement(EmptyState, {
      title: 'No Data',
      description: 'Nothing to see here',
      icon: React.createElement(Icons.Inbox, { className: 'w-10 h-10' }),
    })
  );
  assert.match(emptyHtml, /No Data/, 'EmptyState renders title');
  assert.match(emptyHtml, /<svg/, 'EmptyState renders icon SVG');

  // Toast
  const toastHtml = renderToString(
    React.createElement(Toast, {
      toast: {
        id: '1',
        title: 'Success',
        description: 'Action completed',
        variant: 'success',
      },
      onDismiss: () => {},
    })
  );
  assert.match(toastHtml, /Success/, 'Toast renders title');
  assert.match(toastHtml, /<svg/, 'Toast renders icon SVG');

  // Select
  const selectHtml = renderToString(
    React.createElement(Select, {
      options: [{ value: '1', label: 'Option 1' }],
      placeholder: 'Pick one',
    })
  );
  assert.match(selectHtml, /Pick one/, 'Select renders placeholder');
  assert.match(selectHtml, /<svg/, 'Select renders ChevronDown SVG');

  // Search Icon Component
  const searchHtml = renderToString(
    React.createElement(Icons.Search, {
      className: 'w-4 h-4 text-muted-foreground',
    })
  );
  assert.match(searchHtml, /<svg/, 'Search renders SVG');

  // AIChatInput
  const chatInputHtml = renderToString(
    React.createElement(AIChatInput, {
      onSendMessage: () => {},
      disabled: false,
    })
  );
  assert.match(chatInputHtml, /<svg/, 'AIChatInput renders Send SVG');

  // AIToolExecutionIndicator
  const toolExecHtml = renderToString(
    React.createElement(AIToolExecutionIndicator, {
      toolName: 'get_marks',
      status: 'executing_tool',
    })
  );
  assert.match(toolExecHtml, /get_marks/, 'Tool indicator renders tool name');
  assert.match(toolExecHtml, /<svg/, 'Tool indicator renders Loader2 SVG');

  // AIChatSuggestionChips
  const chipsHtml = renderToString(
    React.createElement(AIChatSuggestionChips, {
      onSelectSuggestion: () => {},
    })
  );
  assert.match(chipsHtml, /OS Attendance/, 'Suggestion chips render label');
  assert.match(chipsHtml, /<svg/, 'Suggestion chips render icon');

  // AIChatMessageList
  const sampleMessages: ChatMessage[] = [
    { id: '1', role: 'user', content: 'Hello', timestamp: new Date() },
    { id: '2', role: 'assistant', content: 'Hi there!', timestamp: new Date() },
  ];
  const msgListHtml = renderToString(
    React.createElement(AIChatMessageList, {
      messages: sampleMessages,
    })
  );
  assert.match(msgListHtml, /Hello/, 'AIChatMessageList renders user message');
  assert.match(
    msgListHtml,
    /Hi there!/,
    'AIChatMessageList renders assistant message'
  );
  assert.match(msgListHtml, /<svg/, 'AIChatMessageList renders icons');

  // SimpleCalculator
  const calcHtml = renderToString(
    React.createElement(SimpleCalculator, {
      totalClasses: 50,
      presents: 42,
    })
  );
  assert.match(calcHtml, /84\.00/, 'SimpleCalculator renders percentage');
  assert.match(calcHtml, /<svg/, 'SimpleCalculator renders icons');

  // Dialog
  const dialogHtml = renderToString(
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
  assert.match(dialogHtml, /Test Dialog/, 'Dialog renders title');
  assert.match(dialogHtml, /<svg/, 'Dialog renders close icon (X)');

  // Sheet
  const sheetHtml = renderToString(
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
  assert.match(sheetHtml, /Test Sheet/, 'Sheet renders title');
  assert.match(sheetHtml, /<svg/, 'Sheet renders close icon (X)');

  // Captcha (SSR returns null because isMounted is false on server)
  const captchaHtml = renderToString(
    React.createElement(Captcha, { onVerify: () => {} })
  );
  assert.strictEqual(captchaHtml, '', 'Captcha returns empty on SSR');
});

// 13. React 19 Ref Forwarding Verification
runCheck('[ICON-08] Ref Forwarding on SVG Element', () => {
  for (const name of ICONS) {
    const Icon = Icons[
      name as keyof typeof Icons
    ] as React.ForwardRefExoticComponent<Icons.IconProps>;
    const ref = React.createRef<SVGSVGElement>();
    const el = React.createElement(Icon, { ref });
    assert.strictEqual(el.props.ref, ref, `${name} must forward ref`);
  }
});

console.log(
  '\n--------------------------------------------------------------------------------'
);
console.log(
  `SUMMARY: ${passCount + failCount} Total Checks | ${passCount} Passed | ${failCount} Failed`
);
console.log(
  '--------------------------------------------------------------------------------\n'
);

if (failCount > 0) {
  process.exit(1);
}
