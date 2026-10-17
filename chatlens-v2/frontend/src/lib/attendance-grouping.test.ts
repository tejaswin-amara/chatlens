import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { groupAttendanceRows } from '@/app/dashboard/attendance/page';

describe('Unified Attendance Subject Grouping & Projections', () => {
  test('groups multiple component rows of the same course into a single unified subject', () => {
    const rawRows = [
      {
        'Course Code': '25CS1302E-L',
        'Course Title':
          'DATABASE SYSTEMS ENGINEERING AND DISTRIBUTED BACKEND DEVELOPMENT',
        Component: 'Lecture',
        'Conducted Hours': '5',
        'Attended Hours': '4',
        'Attendance Percentage': '80.00%',
      },
      {
        'Course Code': '25CS1302E-P',
        'Course Title':
          'DATABASE SYSTEMS ENGINEERING AND DISTRIBUTED BACKEND DEVELOPMENT',
        Component: 'Practical',
        'Conducted Hours': '2',
        'Attended Hours': '2',
        'Attendance Percentage': '100.00%',
      },
      {
        'Course Code': '25CS1302E-S',
        'Course Title':
          'DATABASE SYSTEMS ENGINEERING AND DISTRIBUTED BACKEND DEVELOPMENT',
        Component: 'Skilling',
        'Conducted Hours': '8',
        'Attended Hours': '8',
        'Attendance Percentage': '100.00%',
      },
    ];

    const grouped = groupAttendanceRows(rawRows);
    assert.strictEqual(grouped.length, 1);

    const subject = grouped[0];
    assert.strictEqual(subject.subjectCode, '25CS1302E');
    assert.strictEqual(
      subject.subjectTitle,
      'DATABASE SYSTEMS ENGINEERING AND DISTRIBUTED BACKEND DEVELOPMENT'
    );
    assert.strictEqual(subject.components.length, 3);

    // Verify component breakdown
    assert.strictEqual(subject.components[0].name, 'Lecture');
    assert.strictEqual(subject.components[0].attended, 4);
    assert.strictEqual(subject.components[0].conducted, 5);
    assert.strictEqual(subject.components[0].percentage, 80);

    assert.strictEqual(subject.components[1].name, 'Practical');
    assert.strictEqual(subject.components[1].attended, 2);
    assert.strictEqual(subject.components[1].conducted, 2);
    assert.strictEqual(subject.components[1].percentage, 100);

    assert.strictEqual(subject.components[2].name, 'Skilling');
    assert.strictEqual(subject.components[2].attended, 8);
    assert.strictEqual(subject.components[2].conducted, 8);
    assert.strictEqual(subject.components[2].percentage, 100);

    // Weighted percentage: (80*1.0 + 100*0.5 + 100*0.25) / 1.75 = 155 / 1.75 = 88.57%
    assert.strictEqual(Math.round(subject.overallPercentage), 89);
  });

  test('single raw ERP course row returns honest aggregate (no synthetic expansion)', () => {
    const rawRows = [
      {
        'Course Code': '25CS1302E',
        'Course Title':
          'DATABASE SYSTEMS ENGINEERING AND DISTRIBUTED BACKEND DEVELOPMENT',
        'Conducted Hours': '15',
        'Attended Hours': '14',
        'Attendance Percentage': '89.00%',
      },
    ];

    const grouped = groupAttendanceRows(rawRows);
    assert.strictEqual(grouped.length, 1);

    const subject = grouped[0];
    // No synthetic expansion — returns real data only
    assert.ok(subject.components.length >= 1);
    assert.strictEqual(subject.components[0].attended, 14);
    assert.strictEqual(subject.components[0].conducted, 15);
  });
});
