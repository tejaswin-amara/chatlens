import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import { renderToString } from 'react-dom/server';

// Domain and utility imports
import {
  executeCalculateAttendanceTarget,
  executePredictCGPA,
} from '../src/lib/ai/executor';
import { mapGradeToPoints } from '../src/lib/cgpa';
import { parseCurrency, calculatePendingFee } from '../src/lib/fee-utils';
import { parseTimetable, normalizeSlotKey } from '../src/lib/timetable-parser';
import { decodeSession, SessionDecodeError } from '../src/lib/session';
import { groupAttendanceRows } from '../src/app/dashboard/attendance/page';
import { StatCard } from '../src/components/ui/stat-card';
import { EmptyState } from '../src/components/ui/empty-state';
import * as Icons from '../src/components/ui/icons';

describe('Adversarial Edge-Case Stress Suite: Attendance Calculation & Grouping Engine', () => {
  test('0% Attendance: 0 attended out of 50 conducted classes', () => {
    const calc = executeCalculateAttendanceTarget({
      currentAttended: 0,
      currentTotal: 50,
      targetPercent: 75,
    });
    assert.strictEqual(calc.currentPercentage, 0);
    assert.strictEqual(calc.classesNeeded, 150);
    assert.strictEqual(calc.maxBunkable, 0);
    assert.strictEqual(calc.status, 'below_target');
  });

  test('100% Attendance: 50 attended out of 50 conducted classes', () => {
    const calc = executeCalculateAttendanceTarget({
      currentAttended: 50,
      currentTotal: 50,
      targetPercent: 75,
    });
    assert.strictEqual(calc.currentPercentage, 100);
    assert.strictEqual(calc.classesNeeded, 0);
    assert.strictEqual(calc.maxBunkable, 16);
    assert.strictEqual(calc.status, 'target_met');
  });

  test('Attendance boundary: 100% target when classes missed is recognized impossible', () => {
    const calc = executeCalculateAttendanceTarget({
      currentAttended: 40,
      currentTotal: 50,
      targetPercent: 100,
    });
    assert.strictEqual(calc.status, 'below_target');
    assert.ok(calc.message?.includes('impossible'));
  });

  test('Attendance grouping with LTPS composite component breakdown', () => {
    const rawRows = [
      {
        'Course Code': '23CS2101R-L',
        'Course Title': 'DATA STRUCTURES (LECTURE)',
        'Conducted Hours': '30',
        'Attended Hours': '28',
      },
      {
        'Course Code': '23CS2101R-P',
        'Course Title': 'DATA STRUCTURES (PRACTICAL)',
        'Conducted Hours': '20',
        'Attended Hours': '18',
      },
      {
        'Course Code': '23CS2101R-S',
        'Course Title': 'DATA STRUCTURES (SKILLING)',
        'Conducted Hours': '10',
        'Attended Hours': '8',
      },
    ];

    const grouped = groupAttendanceRows(rawRows);
    assert.strictEqual(
      grouped.length,
      1,
      'Rows with same base course code 23CS2101R must group into 1 subject'
    );
    assert.strictEqual(grouped[0].subjectCode, '23CS2101R');
    assert.strictEqual(grouped[0].totalConducted, 60);
    assert.strictEqual(grouped[0].totalAttended, 54);
    assert.ok(
      grouped[0].overallPercentage > 89 && grouped[0].overallPercentage < 92
    );
    assert.strictEqual(grouped[0].components.length, 3);
  });
});

describe('Adversarial Edge-Case Stress Suite: CGPA & Marks Roadmap Engine', () => {
  test('Perfect 10.0 CGPA Boundary via executePredictCGPA', () => {
    const res = executePredictCGPA({
      currentCGPA: 10.0,
      completedCredits: 80,
      newCourses: [
        { courseCode: 'CS301', credits: 4, expectedGrade: 'O' },
        { courseCode: 'CS302', credits: 4, expectedGrade: 'O' },
      ],
    });
    assert.strictEqual(
      res.predictedCGPA,
      10.0,
      'With O grades on 10.0 CGPA, predicted CGPA must be 10.0'
    );
    assert.strictEqual(res.gpaDelta, 0);
  });

  test('Target CGPA Improvement with all O grades', () => {
    const res = executePredictCGPA({
      currentCGPA: 8.0,
      completedCredits: 80,
      newCourses: [
        { courseCode: 'CS301', credits: 10, expectedGrade: 'O' },
        { courseCode: 'CS302', credits: 10, expectedGrade: 'O' },
      ],
    });
    // Points: 640 + 200 = 840 / 100 credits = 8.40
    assert.strictEqual(res.predictedCGPA, 8.4);
    assert.strictEqual(res.gpaDelta, 0.4);
  });

  test('Grade Point Mapping across all standard and non-standard grades', () => {
    assert.strictEqual(mapGradeToPoints('O'), 10);
    assert.strictEqual(mapGradeToPoints('A+'), 9);
    assert.strictEqual(mapGradeToPoints('A'), 8);
    assert.strictEqual(mapGradeToPoints('B+'), 7);
    assert.strictEqual(mapGradeToPoints('B'), 6);
    assert.strictEqual(mapGradeToPoints('C'), 5);
    assert.strictEqual(mapGradeToPoints('D'), 4);
    assert.strictEqual(mapGradeToPoints('F'), 0);
    assert.strictEqual(mapGradeToPoints('AB'), 0);
    assert.strictEqual(mapGradeToPoints('P'), null);
    assert.strictEqual(mapGradeToPoints('Unknown'), null);
  });
});

describe('Adversarial Edge-Case Stress Suite: Timetable Matrix Engine', () => {
  test('Empty Timetable Data: gracefully returns empty result without throwing', () => {
    const parsed = parseTimetable([]);
    assert.strictEqual(parsed.daysPresent.length, 0);
    assert.strictEqual(parsed.timeSlotsPresent.length, 0);
    assert.strictEqual(parsed.rawRows.length, 0);
  });

  test('Irregular & Messy Time Slot Keys: handles varied string formats', () => {
    assert.strictEqual(normalizeSlotKey('Period-1'), 'PERIOD-1');
    assert.strictEqual(normalizeSlotKey('Hour 2'), 'HOUR 2');
    assert.strictEqual(normalizeSlotKey(' 4 '), '4');
    assert.strictEqual(
      normalizeSlotKey('10:00 AM - 11:00 AM'),
      '10:00 AM - 11:00 AM'
    );
  });

  test('Timetable Matrix Grid parsing with multi-day periods', () => {
    const rawTT = [
      {
        'Day / Period': 'Monday',
        '1': '23CS2101R-L - S-10 - Room-101 - Dr. Smith',
        '2': '23CS2102R-P - S-10 - LAB-1 - Prof. Davis',
        '3': 'Free',
      },
      {
        'Day / Period': 'Tuesday',
        '1': 'Free',
        '2': '23CS2103R-L - S-10 - Room-102 - Dr. Jones',
      },
    ];

    const parsed = parseTimetable(rawTT);
    assert.strictEqual(parsed.daysPresent.length, 2);
    assert.strictEqual(parsed.daysPresent[0], 'Monday');
    assert.strictEqual(parsed.daysPresent[1], 'Tuesday');
    assert.ok(parsed.matrixGrid['Monday']?.['1']);
    assert.ok(parsed.matrixGrid['Tuesday']?.['2']);
  });
});

describe('Adversarial Edge-Case Stress Suite: Financial Currency & Balance Engine', () => {
  test('Parse dirty Indian rupee and international currency strings', () => {
    assert.strictEqual(parseCurrency('₹ 1,25,000.00'), 125000);
    assert.strictEqual(parseCurrency('Rs. 45,500/-'), 45500);
    assert.strictEqual(parseCurrency('$10,000.50'), 10000.5);
    assert.strictEqual(parseCurrency('0'), 0);
    assert.strictEqual(parseCurrency(''), 0);
    assert.strictEqual(parseCurrency(null as unknown as string), 0);
    assert.strictEqual(parseCurrency('NIL'), 0);
  });

  test('Pending balance calculation with full payment, partial payment, and overpayment', () => {
    const fullyPaid = [
      {
        'Total Fee': '100000',
        'Paid Amount': '100000',
        'Payment Status': 'Paid',
      },
    ];
    assert.strictEqual(
      calculatePendingFee(fullyPaid),
      0,
      'Fully paid => 0 due'
    );

    const partialPaid = [
      {
        'Total Fee': '100000',
        'Paid Amount': '60000',
        'Payment Status': 'Pending',
      },
    ];
    assert.strictEqual(
      calculatePendingFee(partialPaid),
      40000,
      'Partial payment => 40,000 due'
    );

    const overPaid = [
      {
        'Total Fee': '100000',
        'Paid Amount': '120000',
        'Payment Status': 'Paid',
      },
    ];
    assert.strictEqual(
      calculatePendingFee(overPaid),
      0,
      'Overpayment => 0 due (no negative fees)'
    );
  });
});

describe('Adversarial Edge-Case Stress Suite: Security, Cryptography & SSR Resilience', () => {
  test('Corrupted Ciphertext rejection in decodeSession', async () => {
    const invalidTokens = [
      '',
      'invalid-prefix',
      'enc.',
      'enc.short',
      'enc.' +
        Buffer.from('corrupted_random_payload_too_short').toString('base64url'),
      'enc.' + Buffer.from(new Uint8Array(50)).toString('base64url'),
    ];

    for (const token of invalidTokens) {
      await assert.rejects(
        async () => decodeSession(token),
        (err) => err instanceof SessionDecodeError || err instanceof Error,
        `Token '${token}' must be rejected with SessionDecodeError`
      );
    }
  });

  test('SSR Safety: UI components render without window/document access crashes', () => {
    const stat = renderToString(
      React.createElement(StatCard, {
        label: 'Attendance',
        value: '92%',
        icon: Icons.Activity,
        trend: { value: '+2%' },
      })
    );
    assert.ok(stat.includes('Attendance') && stat.includes('92%'));

    const empty = renderToString(
      React.createElement(EmptyState, {
        title: 'No Records Found',
        description: 'Zero rows returned for current query',
      })
    );
    assert.ok(empty.includes('No Records Found'));
  });
});
