import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEMO_SESSION,
  DEMO_ATTENDANCE,
  DEMO_TIMETABLE_RAW,
  DEMO_MARKS,
  DEMO_FEE_ITEMS,
  DEMO_PROFILE,
  DEMO_CGPA,
  DEMO_LOGIN_RESULT,
} from '@/lib/fixtures';
import {
  executeGetAttendance,
  executeGetTimetable,
  executeGetMarks,
  executeGetFeeDetails,
  executeGetStudentProfile,
  executeTool,
} from '@/lib/ai/executor';

test('Adversarial Mutation Stress Test for Fixtures', async () => {
  // Snapshot initial fixture state
  const snapshotSession = JSON.stringify(DEMO_SESSION);
  const snapshotAttendance = JSON.stringify(DEMO_ATTENDANCE);
  const snapshotTimetable = JSON.stringify(DEMO_TIMETABLE_RAW);
  const snapshotMarks = JSON.stringify(DEMO_MARKS);
  const snapshotFeeItems = JSON.stringify(DEMO_FEE_ITEMS);
  const snapshotProfile = JSON.stringify(DEMO_PROFILE);
  const snapshotCGPA = JSON.stringify(DEMO_CGPA);
  const snapshotLoginResult = JSON.stringify(DEMO_LOGIN_RESULT);

  // 1. Invoke executeGetAttendance with filters
  const attRes = await executeGetAttendance(
    { subject: 'OS' },
    { isDemo: true }
  );
  assert.ok(attRes.attendance.length > 0);
  assert.strictEqual(
    JSON.stringify(DEMO_ATTENDANCE),
    snapshotAttendance,
    'DEMO_ATTENDANCE was mutated during executeGetAttendance!'
  );

  // 2. Attempt mutation on returned array elements (checking if returns references vs clones)
  const attAll = await executeGetAttendance({}, { isDemo: true });
  assert.strictEqual(attAll.attendance.length, 4);

  // 3. Invoke executeGetTimetable with day filters
  const ttRes = await executeGetTimetable({ day: 'Monday' }, { isDemo: true });
  assert.ok(ttRes.schedule.length > 0);
  assert.strictEqual(
    JSON.stringify(DEMO_TIMETABLE_RAW),
    snapshotTimetable,
    'DEMO_TIMETABLE_RAW was mutated during executeGetTimetable!'
  );

  // 4. Invoke executeGetMarks
  const marksRes = await executeGetMarks({}, { isDemo: true });
  assert.strictEqual(marksRes.marks.length, 4);
  assert.strictEqual(
    JSON.stringify(DEMO_MARKS),
    snapshotMarks,
    'DEMO_MARKS was mutated during executeGetMarks!'
  );

  // 5. Invoke executeGetFeeDetails
  const feeRes = await executeGetFeeDetails({}, { isDemo: true });
  assert.ok(feeRes.breakdown.items.length > 0);
  assert.strictEqual(
    JSON.stringify(DEMO_FEE_ITEMS),
    snapshotFeeItems,
    'DEMO_FEE_ITEMS was mutated during executeGetFeeDetails!'
  );

  // 6. Invoke executeGetStudentProfile
  const profileRes = await executeGetStudentProfile({}, { isDemo: true });
  assert.strictEqual(profileRes.profile.name, 'Alex Student');
  assert.strictEqual(
    JSON.stringify(DEMO_PROFILE),
    snapshotProfile,
    'DEMO_PROFILE was mutated during executeGetStudentProfile!'
  );

  // 7. Invoke main executeTool router for all tools multiple times
  await executeTool('getAttendance', { subject: 'dsa' }, { isDemo: true });
  await executeTool('getTimetable', { day: 'Friday' }, { isDemo: true });
  await executeTool('getMarks', {}, { isDemo: true });
  await executeTool('getFeeDetails', {}, { isDemo: true });
  await executeTool('getStudentProfile', {}, { isDemo: true });

  // 8. Re-verify snapshot integrity after all executions
  assert.strictEqual(
    JSON.stringify(DEMO_SESSION),
    snapshotSession,
    'DEMO_SESSION mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_ATTENDANCE),
    snapshotAttendance,
    'DEMO_ATTENDANCE mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_TIMETABLE_RAW),
    snapshotTimetable,
    'DEMO_TIMETABLE_RAW mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_MARKS),
    snapshotMarks,
    'DEMO_MARKS mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_FEE_ITEMS),
    snapshotFeeItems,
    'DEMO_FEE_ITEMS mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_PROFILE),
    snapshotProfile,
    'DEMO_PROFILE mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_CGPA),
    snapshotCGPA,
    'DEMO_CGPA mutated'
  );
  assert.strictEqual(
    JSON.stringify(DEMO_LOGIN_RESULT),
    snapshotLoginResult,
    'DEMO_LOGIN_RESULT mutated'
  );
});
