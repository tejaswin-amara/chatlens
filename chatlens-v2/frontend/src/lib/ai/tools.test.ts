import test from 'node:test';
import assert from 'node:assert/strict';
import { TOOLS_REGISTRY } from './tools';
import {
  executeTool,
  executeCalculateAttendanceTarget,
  executePredictCGPA,
  processAIChat,
} from './executor';

test('TOOLS_REGISTRY contains all 7 required ERP tools', () => {
  assert.strictEqual(TOOLS_REGISTRY.length, 7);
  const toolNames = TOOLS_REGISTRY.map((t) => t.name);

  assert.ok(toolNames.includes('getAttendance'));
  assert.ok(toolNames.includes('getTimetable'));
  assert.ok(toolNames.includes('getMarks'));
  assert.ok(toolNames.includes('getFeeDetails'));
  assert.ok(toolNames.includes('getStudentProfile'));
  assert.ok(toolNames.includes('calculateAttendanceTarget'));
  assert.ok(toolNames.includes('predictCGPA'));
});

test('executeTool: getAttendance returns structured attendance dataset', async () => {
  const result = await executeTool('getAttendance', {}, { isDemo: true });
  assert.strictEqual(result.success, true);
  assert.strictEqual(result.tool, 'getAttendance');

  const res = result.result as {
    attendance: Array<Record<string, string>>;
    summary?: { totalSubjects: number; overallPercentage: number };
  };
  assert.ok(Array.isArray(res.attendance));
  assert.ok(res.attendance.length > 0);
  assert.ok(res.summary);
  assert.ok(typeof res.summary.overallPercentage === 'number');
});

test('executeTool: getAttendance with subject filter filters correctly', async () => {
  const result = await executeTool(
    'getAttendance',
    { subject: 'OS' },
    { isDemo: true }
  );
  assert.strictEqual(result.success, true);

  const res = result.result as {
    attendance: Array<{ 'Course Title': string; 'Course Code': string }>;
  };
  assert.ok(Array.isArray(res.attendance));
  assert.ok(
    res.attendance.some((item) =>
      item['Course Title'].includes('Operating Systems')
    )
  );
});

test('executeTool: getTimetable returns normalized class sessions', async () => {
  const result = await executeTool('getTimetable', {}, { isDemo: true });
  assert.strictEqual(result.success, true);

  const res = result.result as {
    schedule: Array<{ day: string; timeSlot: string; courseCode: string }>;
  };
  assert.ok(Array.isArray(res.schedule));
  assert.ok(res.schedule.length > 0);
});

test('executeTool: getMarks returns internal evaluation marks', async () => {
  const result = await executeTool('getMarks', {}, { isDemo: true });
  assert.strictEqual(result.success, true);

  const res = result.result as {
    marks: Array<{ 'Course Code': string; 'Total Marks': string }>;
  };
  assert.ok(Array.isArray(res.marks));
  assert.ok(res.marks.length > 0);
});

test('executeTool: getFeeDetails returns total fee, total paid, and pending balance', async () => {
  const result = await executeTool('getFeeDetails', {}, { isDemo: true });
  assert.strictEqual(result.success, true);

  const res = result.result as {
    breakdown: {
      totalAmount: number;
      totalPaid: number;
      totalPending: number;
      hasPendingDue: boolean;
    };
  };
  assert.ok(res.breakdown);
  assert.ok(typeof res.breakdown.totalAmount === 'number');
  assert.ok(typeof res.breakdown.totalPending === 'number');
});

test('executeTool: getStudentProfile returns profile metadata', async () => {
  const result = await executeTool('getStudentProfile', {}, { isDemo: true });
  assert.strictEqual(result.success, true);

  const res = result.result as {
    profile: { name: string; universityId: string };
  };
  assert.ok(res.profile);
  assert.strictEqual(res.profile.name, 'Alex Student');
  assert.strictEqual(res.profile.universityId, '2100030000');
});

test('executeCalculateAttendanceTarget: calculates classes needed when below target', () => {
  const res = executeCalculateAttendanceTarget({
    currentAttended: 15,
    currentTotal: 22,
    targetPercent: 75,
  });

  assert.strictEqual(res.success, true);
  assert.strictEqual(res.status, 'below_target');
  assert.strictEqual(res.classesNeeded, 6); // (75*22 - 1500)/25 = 150/25 = 6
  assert.strictEqual(res.maxBunkable, 0);
});

test('executeCalculateAttendanceTarget: calculates max bunkable classes when target met', () => {
  const res = executeCalculateAttendanceTarget({
    currentAttended: 40,
    currentTotal: 45,
    targetPercent: 75,
  });

  assert.strictEqual(res.success, true);
  assert.strictEqual(res.status, 'target_met');
  assert.strictEqual(res.classesNeeded, 0);
  assert.strictEqual(res.maxBunkable, 8);
});

test('executePredictCGPA: computes weighted predicted CGPA correctly', () => {
  const res = executePredictCGPA({
    currentCGPA: 8.0,
    completedCredits: 40,
    newCourses: [
      { credits: 4, expectedGrade: 'O' }, // 10 * 4 = 40 pts
      { credits: 4, expectedGrade: 'A+' }, // 9 * 4 = 36 pts
    ],
  });

  // current pts = 320. new pts = 76. total pts = 396. total credits = 48.
  // 396 / 48 = 8.25. delta = +0.25
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.predictedCGPA, 8.25);
  assert.strictEqual(res.gpaDelta, 0.25);
  assert.strictEqual(res.totalCredits, 48);
});

test('processAIChat: correctly resolves tools via Vercel AI SDK for natural language queries', async () => {
  const c1 = await processAIChat([
    { role: 'user', content: 'What is my attendance in OS?' },
  ]);
  assert.ok(c1.toolCalls && c1.toolCalls.length > 0);
  assert.strictEqual(c1.toolCalls[0].tool, 'getAttendance');
  assert.strictEqual(c1.toolCalls[0].args.subject, 'OS');

  const c2 = await processAIChat([
    { role: 'user', content: 'Show fee breakdown' },
  ]);
  assert.ok(c2.toolCalls && c2.toolCalls.length > 0);
  assert.strictEqual(c2.toolCalls[0].tool, 'getFeeDetails');

  const c3 = await processAIChat([
    { role: 'user', content: 'What classes do I have today?' },
  ]);
  assert.ok(c3.toolCalls && c3.toolCalls.length > 0);
  assert.strictEqual(c3.toolCalls[0].tool, 'getTimetable');

  const c4 = await processAIChat([
    { role: 'user', content: 'How many classes can I miss in OS?' },
  ]);
  assert.ok(c4.toolCalls && c4.toolCalls.length > 0);
  assert.strictEqual(c4.toolCalls[0].tool, 'calculateAttendanceTarget');

  const c5 = await processAIChat([
    { role: 'user', content: 'Predict CGPA for next semester' },
  ]);
  assert.ok(c5.toolCalls && c5.toolCalls.length > 0);
  assert.strictEqual(c5.toolCalls[0].tool, 'predictCGPA');
});
