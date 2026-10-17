import test from 'node:test';
import assert from 'node:assert/strict';
import {
  executeTool,
  executeCalculateAttendanceTarget,
  executePredictCGPA,
  processAIChat,
  createErpTools,
} from './executor';
import {
  calculateAttendanceTargetArgsSchema,
  predictCGPAArgsSchema,
} from './tools';

test('ADVERSARIAL: calculateAttendanceTargetArgsSchema validation boundary tests', () => {
  // Valid default targetPercent
  const res1 = calculateAttendanceTargetArgsSchema.parse({
    currentAttended: 30,
    currentTotal: 40,
  });
  assert.strictEqual(res1.targetPercent, 75);

  // Reject negative currentAttended
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: -1,
      currentTotal: 40,
    });
  });

  // Reject currentTotal <= 0
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: 10,
      currentTotal: 0,
    });
  });
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: 10,
      currentTotal: -5,
    });
  });

  // Reject targetPercent < 1 or > 100
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: 10,
      currentTotal: 20,
      targetPercent: 0,
    });
  });
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: 10,
      currentTotal: 20,
      targetPercent: 101,
    });
  });

  // Reject invalid types
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: 'thirty',
      currentTotal: 40,
    });
  });
  assert.throws(() => {
    calculateAttendanceTargetArgsSchema.parse({
      currentAttended: 30,
      currentTotal: null,
    });
  });
});

test('ADVERSARIAL: executeCalculateAttendanceTarget edge case behavior', () => {
  // 100% target when already missed a class (current 35/40 = 87.5%)
  const edge100 = executeCalculateAttendanceTarget({
    currentAttended: 35,
    currentTotal: 40,
    targetPercent: 100,
  });
  assert.strictEqual(edge100.success, true);
  assert.strictEqual(edge100.status, 'below_target');
  assert.strictEqual(edge100.classesNeeded, 0);
  assert.strictEqual(edge100.maxBunkable, 0);
  assert.ok(edge100.message.includes('impossible'));

  // Target met exactly (30/40 = 75%, target 75%)
  const exact = executeCalculateAttendanceTarget({
    currentAttended: 30,
    currentTotal: 40,
    targetPercent: 75,
  });
  assert.strictEqual(exact.status, 'target_met');
  assert.strictEqual(exact.classesNeeded, 0);
  assert.strictEqual(exact.maxBunkable, 0);

  // Target met with bunkable buffer (36/40 = 90%, target 75%)
  // formula: (100*36 - 75*40)/75 = (3600 - 3000)/75 = 600/75 = 8
  const bunkable = executeCalculateAttendanceTarget({
    currentAttended: 36,
    currentTotal: 40,
    targetPercent: 75,
  });
  assert.strictEqual(bunkable.status, 'target_met');
  assert.strictEqual(bunkable.maxBunkable, 8);

  // Zero attended out of 10 total (0/10 = 0%), target 75%
  // denominator = 25, numerator = 75*10 - 0 = 750 => 30 classes needed
  const zeroAttended = executeCalculateAttendanceTarget({
    currentAttended: 0,
    currentTotal: 10,
    targetPercent: 75,
  });
  assert.strictEqual(zeroAttended.status, 'below_target');
  assert.strictEqual(zeroAttended.classesNeeded, 30);
});

test('ADVERSARIAL: predictCGPAArgsSchema validation & execution edge cases', () => {
  // Reject currentCGPA outside [0, 10]
  assert.throws(() => {
    predictCGPAArgsSchema.parse({
      currentCGPA: 11,
      completedCredits: 50,
      newCourses: [{ credits: 4, expectedGrade: 'A' }],
    });
  });
  assert.throws(() => {
    predictCGPAArgsSchema.parse({
      currentCGPA: -1,
      completedCredits: 50,
      newCourses: [{ credits: 4, expectedGrade: 'A' }],
    });
  });

  // Reject empty newCourses array
  assert.throws(() => {
    predictCGPAArgsSchema.parse({
      currentCGPA: 8.0,
      completedCredits: 50,
      newCourses: [],
    });
  });

  // Reject non-positive credits in course
  assert.throws(() => {
    predictCGPAArgsSchema.parse({
      currentCGPA: 8.0,
      completedCredits: 50,
      newCourses: [{ credits: 0, expectedGrade: 'A' }],
    });
  });

  // Fallback behavior for unknown grade string (e.g., 'UNKNOWN_GRADE')
  const fallbackRes = executePredictCGPA({
    currentCGPA: 8.0,
    completedCredits: 40,
    newCourses: [{ credits: 4, expectedGrade: 'UNKNOWN_GRADE' }],
  });
  assert.strictEqual(fallbackRes.success, true);
  // UNKNOWN_GRADE falls back to 8.0 grade points.
  // current points = 320, new points = 32, total = 352 / 44 = 8.00
  assert.strictEqual(fallbackRes.predictedCGPA, 8.0);
  assert.strictEqual(fallbackRes.gpaDelta, 0.0);

  // 0 completed credits initial student
  const freshmanRes = executePredictCGPA({
    currentCGPA: 0.0,
    completedCredits: 0,
    newCourses: [{ credits: 4, expectedGrade: 'O' }],
  });
  assert.strictEqual(freshmanRes.success, true);
  assert.strictEqual(freshmanRes.predictedCGPA, 10.0);
});

test('ADVERSARIAL: executeTool main dispatcher invalid tool & args error handling', async () => {
  // Unknown tool name
  const unknownRes = await executeTool('nonExistentTool', {});
  assert.strictEqual(unknownRes.success, false);
  assert.strictEqual(unknownRes.tool, 'nonExistentTool');
  assert.ok(unknownRes.error?.includes('Unknown tool name'));

  // Invalid arguments passed to calculateAttendanceTarget via executeTool
  const invalidArgsRes = await executeTool('calculateAttendanceTarget', {
    currentAttended: -1,
    currentTotal: 0,
  });
  assert.strictEqual(invalidArgsRes.success, false);
  assert.strictEqual(invalidArgsRes.tool, 'calculateAttendanceTarget');
  assert.ok(invalidArgsRes.error?.includes('Execution error'));

  // Null/primitive args safety check
  const nullArgsRes = await executeTool(
    'getAttendance',
    null as unknown as Record<string, unknown>,
    { isDemo: true }
  );
  assert.strictEqual(nullArgsRes.success, true);
  assert.strictEqual(nullArgsRes.tool, 'getAttendance');
});

test('ADVERSARIAL: MockLanguageModelV4 prompt routing keyword matching', async () => {
  const queries = [
    {
      text: 'What is my attendance in Operating Systems?',
      expectedTool: 'getAttendance',
    },
    { text: 'Show my timetable for tomorrow', expectedTool: 'getTimetable' },
    { text: 'What are my internal exam marks?', expectedTool: 'getMarks' },
    { text: 'Show fee payment dues', expectedTool: 'getFeeDetails' },
    {
      text: 'Who am I? Show my student profile',
      expectedTool: 'getStudentProfile',
    },
    {
      text: 'How many classes can I bunk in DSA?',
      expectedTool: 'calculateAttendanceTarget',
    },
    { text: 'Predict my CGPA for next semester', expectedTool: 'predictCGPA' },
  ];

  for (const q of queries) {
    const res = await processAIChat([{ role: 'user', content: q.text }], {
      isDemo: true,
    });
    assert.ok(
      res.toolCalls && res.toolCalls.length > 0,
      `Expected tool call for query: "${q.text}"`
    );
    assert.strictEqual(
      res.toolCalls[0].tool,
      q.expectedTool,
      `Query "${q.text}" routed to wrong tool`
    );
  }
});

test('ADVERSARIAL: processAIChat fallback on general non-tool prompt', async () => {
  const res = await processAIChat(
    [{ role: 'user', content: 'Hello KL Sync Copilot!' }],
    { isDemo: true }
  );
  assert.strictEqual(res.toolCalls.length, 0);
  assert.ok(res.assistantResponseText.includes('I am KL Sync Copilot'));
});

test('ADVERSARIAL: createErpTools produces valid Vercel AI SDK tool objects', () => {
  const tools = createErpTools({ isDemo: true });
  const toolKeys = Object.keys(tools);
  assert.strictEqual(toolKeys.length, 7);
  assert.ok(toolKeys.includes('getAttendance'));
  assert.ok(toolKeys.includes('calculateAttendanceTarget'));
  assert.ok(toolKeys.includes('predictCGPA'));
});
