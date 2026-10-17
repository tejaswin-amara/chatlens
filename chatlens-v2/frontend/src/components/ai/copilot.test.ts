import test from 'node:test';
import assert from 'node:assert/strict';
import { TOOLS_REGISTRY } from '@/lib/ai/tools';
import { processAIChat } from '@/lib/ai/executor';

test('AI Copilot component data contracts & registry integration', () => {
  assert.ok(Array.isArray(TOOLS_REGISTRY));
  assert.strictEqual(TOOLS_REGISTRY.length, 7);

  // Verify that all tools required by the UI are defined
  const toolMap = new Map(TOOLS_REGISTRY.map((t) => [t.name, t]));
  assert.ok(toolMap.has('getAttendance'));
  assert.ok(toolMap.has('getTimetable'));
  assert.ok(toolMap.has('getMarks'));
  assert.ok(toolMap.has('getFeeDetails'));
  assert.ok(toolMap.has('getStudentProfile'));
  assert.ok(toolMap.has('calculateAttendanceTarget'));
  assert.ok(toolMap.has('predictCGPA'));
});

test('Copilot suggestion chip queries map directly to valid ERP tools', async () => {
  const suggestions = [
    'What is my attendance in OS?',
    'Show fee breakdown',
    'What classes do I have today?',
    'How many classes can I miss in OS?',
    'Predict CGPA for next semester',
  ];

  for (const query of suggestions) {
    const res = await processAIChat([{ role: 'user', content: query }]);
    assert.ok(
      res.toolCalls && res.toolCalls.length > 0,
      `Expected tool call for query: ${query}`
    );
    assert.ok(
      res.toolCalls[0].tool,
      `Matched tool name should exist for: ${query}`
    );
  }
});
