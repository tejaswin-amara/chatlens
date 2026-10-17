import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import * as fs from 'node:fs';
import * as path from 'node:path';

import * as Icons from './icons';
import { AICopilot } from '@/components/ai/AICopilot';
import { AIChatSheet } from '@/components/ai/AIChatSheet';
import { AIChatInput } from '@/components/ai/AIChatInput';
import { AIChatMessageList } from '@/components/ai/AIChatMessageList';
import { AIChatSuggestionChips } from '@/components/ai/AIChatSuggestionChips';
import { AIToolExecutionIndicator } from '@/components/ai/AIToolExecutionIndicator';
import { useAttendance } from '@/hooks/useAttendance';
import { useTimetable } from '@/hooks/useTimetable';
import { useMarks } from '@/hooks/useMarks';
import { useFee } from '@/hooks/useFee';
import { useProfile } from '@/hooks/useProfile';
import { useAcademicSession } from '@/hooks/useAcademicSession';

describe('Challenger 2: Ponytail R2 Consumer & System Verification Suite', () => {
  const rootDir = path.resolve(process.cwd(), 'src');

  test('no file in src/ imports from lucide-react', () => {
    function scanDir(dir: string): string[] {
      const files: string[] = [];
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          files.push(...scanDir(fullPath));
        } else if (/\.(tsx?|jsx?)$/.test(entry.name)) {
          files.push(fullPath);
        }
      }
      return files;
    }

    const allSourceFiles = scanDir(rootDir);
    const violatingFiles: string[] = [];

    const lucideImportRegex =
      /from\s+['"]lucide-react['"]|import\s+['"]lucide-react['"]/;

    for (const file of allSourceFiles) {
      const content = fs.readFileSync(file, 'utf-8');
      if (lucideImportRegex.test(content)) {
        violatingFiles.push(file);
      }
    }

    assert.strictEqual(
      violatingFiles.length,
      0,
      `Found forbidden 'lucide-react' imports in: ${violatingFiles.join(', ')}`
    );
  });

  test('verify all 32 consumer files only import valid, exported icons from @/components/ui/icons', () => {
    const consumerFiles = [
      'app/dashboard/attendance/page.tsx',
      'app/dashboard/circulars/page.tsx',
      'app/dashboard/exam-seating/page.tsx',
      'app/dashboard/fee/page.tsx',
      'app/dashboard/hostels/page.tsx',
      'app/dashboard/library/page.tsx',
      'app/dashboard/marks/page.tsx',
      'app/dashboard/page.tsx',
      'app/dashboard/profile/page.tsx',
      'app/dashboard/timetable/page.tsx',
      'app/dashboard/tools/page.tsx',
      'app/error.tsx',
      'app/global-error.tsx',
      'app/page.tsx',
      'components/Captcha.tsx',
      'components/ERPTablePage.tsx',
      'components/Navigation.tsx',
      'components/ai/AIChatInput.tsx',
      'components/ai/AIChatMessageList.tsx',
      'components/ai/AIChatSheet.tsx',
      'components/ai/AIChatSuggestionChips.tsx',
      'components/ai/AICopilot.tsx',
      'components/ai/AIToolExecutionIndicator.tsx',
      'components/attendance-calculator.tsx',
      'components/ui/button.tsx',
      'components/ui/dialog.tsx',
      'components/ui/empty-state.tsx',
      'components/ui/select.tsx',
      'components/ui/sheet.tsx',
      'components/ui/stat-card.tsx',
      'components/ui/toast.tsx',
    ];

    const iconImportRegex =
      /import\s+{([^}]+)}\s+from\s+['"](@\/components\/ui\/icons|\.\/icons)['"]/g;
    const allImportedNames = new Set<string>();

    for (const relPath of consumerFiles) {
      const fullPath = path.join(rootDir, relPath);
      assert.ok(
        fs.existsSync(fullPath),
        `Consumer file should exist: ${relPath}`
      );
      const content = fs.readFileSync(fullPath, 'utf-8');

      let match;
      while ((match = iconImportRegex.exec(content)) !== null) {
        const rawImports = match[1];
        const names = rawImports
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s) => {
            // handle "type X" or "X as Y"
            const cleaned = s.replace(/^type\s+/, '');
            const parts = cleaned.split(/\s+as\s+/);
            return parts[0].trim();
          });

        for (const name of names) {
          allImportedNames.add(name);
          if (name === 'LucideIcon' || name === 'IconProps') {
            // These are valid TypeScript types exported in icons.tsx
            continue;
          }
          const exportedItem = (Icons as Record<string, unknown>)[name];
          assert.ok(
            exportedItem !== undefined,
            `File ${relPath} imports '${name}', but '${name}' is not exported by icons.tsx`
          );
        }
      }
    }

    assert.ok(
      allImportedNames.size > 20,
      `Expected many imported icons, got ${allImportedNames.size}`
    );
  });

  test('stress test all 55 icons across comprehensive props & forwardRef matrix', () => {
    const allIconKeys = Object.keys(Icons).filter(
      (k) =>
        k !== 'createIcon' &&
        typeof (Icons as Record<string, unknown>)[k] === 'object'
    );

    for (const key of allIconKeys) {
      const IconComp = (
        Icons as Record<string, React.ComponentType<Icons.IconProps>>
      )[key];
      assert.ok(IconComp, `Icon component ${key} must exist`);

      // 1. Render default
      const defaultHtml = renderToString(React.createElement(IconComp));
      assert.match(defaultHtml, /<svg/, `${key} must render <svg> tag`);
      assert.match(
        defaultHtml,
        /viewBox="0 0 24 24"/,
        `${key} must have viewBox`
      );

      // 2. Render with numeric size
      const numSizeHtml = renderToString(
        React.createElement(IconComp, { size: 18 })
      );
      assert.match(numSizeHtml, /width="18"/);
      assert.match(numSizeHtml, /height="18"/);

      // 3. Render with string size
      const strSizeHtml = renderToString(
        React.createElement(IconComp, { size: '1.25rem' })
      );
      assert.match(strSizeHtml, /width="1.25rem"/);
      assert.match(strSizeHtml, /height="1.25rem"/);

      // 4. Render with width/height override
      const overrideHtml = renderToString(
        React.createElement(IconComp, { width: 32, height: 48 })
      );
      assert.match(overrideHtml, /width="32"/);
      assert.match(overrideHtml, /height="48"/);

      // 5. Render with custom strokeWidth & className
      const customHtml = renderToString(
        React.createElement(IconComp, {
          strokeWidth: 1.5,
          className: 'custom-icon text-amber-500',
          'aria-hidden': 'true',
          id: `icon-${key}`,
        })
      );
      assert.match(customHtml, /stroke-width="1.5"/);
      assert.match(customHtml, /class="custom-icon text-amber-500"/);
      assert.match(customHtml, /aria-hidden="true"/);
      assert.match(customHtml, new RegExp(`id="icon-${key}"`));
    }
  });

  test('AICopilot component renders trigger button and integrated sheet cleanly', () => {
    const htmlClosed = renderToString(
      React.createElement(AICopilot, { initialOpen: false })
    );
    assert.match(htmlClosed, /AI Copilot/);
    assert.match(htmlClosed, /aria-label="AI Copilot ⌘K \(Ctrl\+Shift\+A\)"/);
    assert.match(htmlClosed, /aria-expanded="false"/);

    const htmlOpen = renderToString(
      React.createElement(AICopilot, { initialOpen: true })
    );
    assert.match(htmlOpen, /aria-expanded="true"/);
  });

  test('AIChatSheet renders all state variations without AIChatDialog wrapper', () => {
    // Idle state with no messages
    const idleHtml = renderToString(
      React.createElement(AIChatSheet, {
        open: true,
        onOpenChange: () => {},
        messages: [],
        status: 'idle',
        onSendMessage: () => {},
        onClearChat: () => {},
      })
    );
    assert.match(idleHtml, /AI Copilot/);
    assert.match(idleHtml, /Agentic v1\.0/);
    assert.match(idleHtml, /KL Sync ERP Intelligence/);

    // Thinking state with messages
    const thinkingHtml = renderToString(
      React.createElement(AIChatSheet, {
        open: true,
        onOpenChange: () => {},
        messages: [
          {
            id: 'm1',
            role: 'user',
            content: 'What is my attendance in OS?',
            timestamp: new Date('2026-08-16T12:00:00Z'),
          },
        ],
        status: 'thinking',
        onSendMessage: () => {},
        onClearChat: () => {},
      })
    );
    assert.match(thinkingHtml, /What is my attendance in OS\?/);
    assert.match(
      thinkingHtml,
      /Analyzing request &amp; executing workflow\.\.\./
    );

    // Executing tool state
    const toolHtml = renderToString(
      React.createElement(AIChatSheet, {
        open: true,
        onOpenChange: () => {},
        messages: [
          {
            id: 'm1',
            role: 'user',
            content: 'Show fee breakdown',
            timestamp: new Date('2026-08-16T12:00:00Z'),
          },
        ],
        status: 'executing_tool',
        activeTool: 'getFeeDetails',
        onSendMessage: () => {},
        onClearChat: () => {},
      })
    );
    assert.match(toolHtml, /Querying ERP via getFeeDetails\.\.\./);
  });

  test('AIChatMessageList renders user, assistant, and tool execution messages', () => {
    const messages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: 'Show my marks for Operating Systems',
        timestamp: new Date('2026-08-16T10:00:00Z'),
      },
      {
        id: 'msg-2',
        role: 'assistant' as const,
        content:
          'Here are your marks for **Operating Systems**:\n\n- Internal 1: 28/30\n- Internal 2: 29/30',
        timestamp: new Date('2026-08-16T10:00:02Z'),
        toolCalls: [
          {
            tool: 'getMarks',
            args: { subject: 'Operating Systems' },
            result: { internal1: 28, internal2: 29 },
          },
        ],
      },
    ];

    const html = renderToString(
      React.createElement(AIChatMessageList, { messages })
    );
    assert.match(html, /Show my marks for Operating Systems/);
    assert.match(
      html,
      /strong class="font-semibold">Operating Systems<\/strong>/
    );
  });

  test('AIChatSuggestionChips renders all 5 suggestion chips with icons and min-h-[44px]', () => {
    const html = renderToString(
      React.createElement(AIChatSuggestionChips, {
        onSelectSuggestion: () => {},
        disabled: false,
      })
    );
    assert.match(html, /OS Attendance/);
    assert.match(html, /Fee Balance/);
    assert.match(html, /Today Schedule/);
    assert.match(html, /Target 75%/);
    assert.match(html, /Predict CGPA/);
    assert.match(html, /min-h-\[44px\]/);
  });

  test('AIChatInput renders accessible controls with min 44x44px touch targets', () => {
    const html = renderToString(
      React.createElement(AIChatInput, {
        onSendMessage: () => {},
        disabled: false,
      })
    );
    assert.match(html, /min-w-\[44px\]/);
    assert.match(html, /min-h-\[44px\]/);
    assert.match(html, /aria-label="Send query"/);
    assert.match(html, /aria-label="Ask AI Copilot"/);
  });

  test('AIToolExecutionIndicator renders loading states and null on error', () => {
    const errorHtml = renderToString(
      React.createElement(AIToolExecutionIndicator, {
        status: 'error',
      })
    );
    assert.strictEqual(errorHtml, '');

    const thinkingHtml = renderToString(
      React.createElement(AIToolExecutionIndicator, {
        status: 'thinking',
      })
    );
    assert.match(
      thinkingHtml,
      /Analyzing request &amp; executing workflow\.\.\./
    );

    const toolHtml = renderToString(
      React.createElement(AIToolExecutionIndicator, {
        status: 'executing_tool',
        toolName: 'getAttendance',
      })
    );
    assert.match(toolHtml, /Querying ERP via getAttendance\.\.\./);
  });

  test('Hooks directory completeness and absence of useERPData', () => {
    assert.ok(typeof useAttendance === 'function');
    assert.ok(typeof useTimetable === 'function');
    assert.ok(typeof useMarks === 'function');
    assert.ok(typeof useFee === 'function');
    assert.ok(typeof useProfile === 'function');
    assert.ok(typeof useAcademicSession === 'function');

    const hookExists = fs.existsSync(
      path.resolve(rootDir, 'hooks/useERPData.ts')
    );
    assert.strictEqual(hookExists, false, 'useERPData.ts should not exist');
  });
});
