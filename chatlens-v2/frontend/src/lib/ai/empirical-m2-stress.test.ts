import test from 'node:test';
import assert from 'node:assert/strict';
import {
  executeTool,
  executeCalculateAttendanceTarget,
  executePredictCGPA,
  executeGetAttendance,
  executeGetTimetable,
  processAIChat,
} from './executor';

// ============================================================================
// EMPIRICAL STRESS SUITE: Milestone M2 - Native AI Tool Calling R2
// ============================================================================

test('EMPIRICAL M2 STRESS: calculateAttendanceTarget edge cases', () => {
  // Edge Case 1: targetPercent = 100 when currentPercentage < 100
  const res1 = executeCalculateAttendanceTarget({
    currentAttended: 9,
    currentTotal: 10,
    targetPercent: 100,
  });
  assert.strictEqual(res1.success, true);
  assert.strictEqual(res1.currentPercentage, 90);
  assert.strictEqual(res1.status, 'below_target');
  assert.strictEqual(res1.classesNeeded, 0);
  assert.strictEqual(res1.maxBunkable, 0);
  assert.ok(res1.message.includes('impossible'));

  // Edge Case 2: targetPercent = 100 when currentPercentage === 100
  const res2 = executeCalculateAttendanceTarget({
    currentAttended: 10,
    currentTotal: 10,
    targetPercent: 100,
  });
  assert.strictEqual(res2.success, true);
  assert.strictEqual(res2.currentPercentage, 100);
  assert.strictEqual(res2.status, 'target_met');
  assert.strictEqual(res2.classesNeeded, 0);
  assert.strictEqual(res2.maxBunkable, 0);
  assert.ok(res2.message.includes('meets your target of 100%'));

  // Edge Case 3: Zero attendance (0 / 10 attended), target = 75%
  const res3 = executeCalculateAttendanceTarget({
    currentAttended: 0,
    currentTotal: 10,
    targetPercent: 75,
  });
  assert.strictEqual(res3.success, true);
  assert.strictEqual(res3.currentPercentage, 0);
  assert.strictEqual(res3.status, 'below_target');
  assert.strictEqual(res3.classesNeeded, 30); // (75*10 - 0) / 25 = 30
  assert.strictEqual(res3.maxBunkable, 0);

  // Edge Case 4: Target already met with large margin
  const res4 = executeCalculateAttendanceTarget({
    currentAttended: 90,
    currentTotal: 100,
    targetPercent: 75,
  });
  assert.strictEqual(res4.success, true);
  assert.strictEqual(res4.currentPercentage, 90);
  assert.strictEqual(res4.status, 'target_met');
  assert.strictEqual(res4.classesNeeded, 0);
  assert.strictEqual(res4.maxBunkable, 20); // (100*90 - 75*100)/75 = 1500/75 = 20

  // Edge Case 5: Target exactly equal to current percentage
  const res5 = executeCalculateAttendanceTarget({
    currentAttended: 30,
    currentTotal: 40,
    targetPercent: 75,
  });
  assert.strictEqual(res5.success, true);
  assert.strictEqual(res5.currentPercentage, 75);
  assert.strictEqual(res5.status, 'target_met');
  assert.strictEqual(res5.classesNeeded, 0);
  assert.strictEqual(res5.maxBunkable, 0); // (3000 - 3000)/75 = 0
});

test('EMPIRICAL M2 STRESS: calculateAttendanceTarget invalid input handling via executeTool', async () => {
  // Negative targetPercent -> Zod validation error caught cleanly
  const res1 = await executeTool('calculateAttendanceTarget', {
    currentAttended: 10,
    currentTotal: 20,
    targetPercent: -10,
  });
  assert.strictEqual(res1.success, false);
  assert.ok(
    res1.error?.includes('Execution error in calculateAttendanceTarget')
  );

  // targetPercent > 100 -> Zod validation error
  const res2 = await executeTool('calculateAttendanceTarget', {
    currentAttended: 10,
    currentTotal: 20,
    targetPercent: 120,
  });
  assert.strictEqual(res2.success, false);

  // currentAttended negative -> Zod validation error
  const res3 = await executeTool('calculateAttendanceTarget', {
    currentAttended: -5,
    currentTotal: 20,
    targetPercent: 75,
  });
  assert.strictEqual(res3.success, false);

  // currentTotal = 0 -> Zod validation error
  const res4 = await executeTool('calculateAttendanceTarget', {
    currentAttended: 0,
    currentTotal: 0,
    targetPercent: 75,
  });
  assert.strictEqual(res4.success, false);
});

test('EMPIRICAL M2 STRESS: predictCGPA edge cases and robust grade handling', () => {
  // Edge Case 1: Unrecognized letter grade fallback
  const res1 = executePredictCGPA({
    currentCGPA: 8.5,
    completedCredits: 50,
    newCourses: [{ credits: 3, expectedGrade: 'UNKNOWN_GRADE' }],
  });
  assert.strictEqual(res1.success, true);
  // Fallback maps UNKNOWN_GRADE to 8.0
  // Total points: 8.5 * 50 + 8.0 * 3 = 425 + 24 = 449
  // Total credits: 53. 449 / 53 = 8.47169... -> 8.47
  assert.strictEqual(res1.predictedCGPA, 8.47);
  assert.strictEqual(res1.gpaDelta, -0.03);

  // Edge Case 2: Zero completed credits
  const res2 = executePredictCGPA({
    currentCGPA: 0,
    completedCredits: 0,
    newCourses: [
      { credits: 4, expectedGrade: 'O' }, // 10 * 4 = 40
      { credits: 4, expectedGrade: 'S' }, // 10 * 4 = 40
    ],
  });
  assert.strictEqual(res2.success, true);
  assert.strictEqual(res2.predictedCGPA, 10.0);
  assert.strictEqual(res2.gpaDelta, 10.0);
  assert.strictEqual(res2.totalCredits, 8);

  // Edge Case 3: Failed course grade 'F' (0 points)
  const res3 = executePredictCGPA({
    currentCGPA: 9.0,
    completedCredits: 20,
    newCourses: [
      { credits: 4, expectedGrade: 'F' }, // 0 pts
    ],
  });
  assert.strictEqual(res3.success, true);
  // 9.0 * 20 + 0 = 180 / 24 = 7.50
  assert.strictEqual(res3.predictedCGPA, 7.5);
  assert.strictEqual(res3.gpaDelta, -1.5);
});

test('EMPIRICAL M2 STRESS: predictCGPA invalid input validation', async () => {
  // Invalid currentCGPA (> 10)
  const res1 = await executeTool('predictCGPA', {
    currentCGPA: 11.5,
    completedCredits: 30,
    newCourses: [{ credits: 3, expectedGrade: 'A' }],
  });
  assert.strictEqual(res1.success, false);

  // Empty newCourses array
  const res2 = await executeTool('predictCGPA', {
    currentCGPA: 8.0,
    completedCredits: 30,
    newCourses: [],
  });
  assert.strictEqual(res2.success, false);
});

test('EMPIRICAL M2 STRESS: getAttendance subject searching & unmatched subject', async () => {
  // Unmatched subject query
  const res = await executeGetAttendance(
    { subject: 'NonExistentSubject123' },
    { isDemo: true }
  );
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.attendance.length, 0);
  assert.strictEqual(res.summary?.totalSubjects, 0);
  assert.strictEqual(res.summary?.overallPercentage, 0);
  assert.strictEqual(res.summary?.atRiskCount, 0);
});

test('EMPIRICAL M2 STRESS: getTimetable day filtering & invalid day', async () => {
  // Invalid day string
  const res = await executeGetTimetable(
    { day: 'InvalidDay' },
    { isDemo: true }
  );
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.schedule.length, 0);
});

test('EMPIRICAL M2 STRESS: executeTool unknown tool name handling', async () => {
  const res = await executeTool('nonExistentTool', {});
  assert.strictEqual(res.success, false);
  assert.ok(res.error?.includes('Unknown tool name: nonExistentTool'));
});

test('EMPIRICAL M2 STRESS: processAIChat natural language responses & formatting', async () => {
  // Test 1: getAttendance response formatting
  const chat1 = await processAIChat([
    { role: 'user', content: 'Show my attendance' },
  ]);
  assert.ok(
    chat1.assistantResponseText.includes('Here is your attendance record')
  );
  assert.ok(chat1.toolCalls.length === 1);
  assert.strictEqual(chat1.toolCalls[0].tool, 'getAttendance');

  // Test 2: calculateAttendanceTarget when target met vs target impossible
  const chat2 = await processAIChat([
    { role: 'user', content: 'How many classes do I need to attend?' },
  ]);
  assert.ok(chat2.assistantResponseText.length > 0);
  assert.ok(chat2.toolCalls.length === 1);
  assert.strictEqual(chat2.toolCalls[0].tool, 'calculateAttendanceTarget');

  // Test 3: getFeeDetails formatting
  const chat3 = await processAIChat([
    { role: 'user', content: 'How much tuition fee is pending?' },
  ]);
  assert.ok(
    chat3.assistantResponseText.includes('fee breakdown') ||
      chat3.assistantResponseText.includes('fee')
  );
  assert.strictEqual(chat3.toolCalls[0].tool, 'getFeeDetails');

  // Test 4: getStudentProfile formatting
  const chat4 = await processAIChat([
    { role: 'user', content: 'Show my student profile details' },
  ]);
  assert.ok(chat4.assistantResponseText.includes('Student Profile'));
  assert.strictEqual(chat4.toolCalls[0].tool, 'getStudentProfile');

  // Test 5: getMarks formatting
  const chat5 = await processAIChat([
    { role: 'user', content: 'Show internal exam marks' },
  ]);
  assert.ok(chat5.assistantResponseText.includes('internal marks'));
  assert.strictEqual(chat5.toolCalls[0].tool, 'getMarks');

  // Test 6: predictCGPA formatting
  const chat6 = await processAIChat([
    { role: 'user', content: 'Predict my CGPA' },
  ]);
  assert.ok(chat6.assistantResponseText.includes('CGPA Forecast'));
  assert.strictEqual(chat6.toolCalls[0].tool, 'predictCGPA');
});
