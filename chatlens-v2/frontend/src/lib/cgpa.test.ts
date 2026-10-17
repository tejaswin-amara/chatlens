import test from 'node:test';
import assert from 'node:assert';
import { processERPDataForCGPA } from './cgpa';

test('processERPDataForCGPA extracts official CGPA summary when present', () => {
  const rawRows = [
    {
      CGPA: '9.45',
      SGPA: '9.60',
      'Total Credits': '48',
    },
  ];
  const result = processERPDataForCGPA(rawRows);
  assert.strictEqual(result.isOfficial, true);
  assert.strictEqual(result.cgpa, 9.45);
  assert.strictEqual(result.sgpa, 9.6);
  assert.strictEqual(result.credits, 48);
});

test('processERPDataForCGPA extracts official CGPA from profile data if missing in rows', () => {
  const profileData = {
    'Cumulative GPA': '8.75',
    'Total Credits Earned': '36',
  };
  const result = processERPDataForCGPA([], profileData);
  assert.strictEqual(result.isOfficial, true);
  assert.strictEqual(result.cgpa, 8.75);
  assert.strictEqual(result.credits, 36);
});

test('processERPDataForCGPA dynamically calculates weighted GPA from grade strings and credits', () => {
  const rawRows = [
    { Grade: 'S', Credits: '4' }, // 10 * 4 = 40
    { Grade: 'A+', Credits: '4' }, // 9 * 4 = 36
    { Grade: 'A', Credits: '3' }, // 8 * 3 = 24
    { Grade: 'B+', Credits: '3' }, // 7 * 3 = 21
    { Grade: 'F', Credits: '2' }, // 0 * 2 = 0
  ];
  // Total points: 40 + 36 + 24 + 21 + 0 = 121
  // Total credits: 4 + 4 + 3 + 3 + 2 = 16
  // Expected CGPA: 121 / 16 = 7.5625 -> 7.56
  const result = processERPDataForCGPA(rawRows);
  assert.strictEqual(result.isOfficial, false);
  assert.strictEqual(result.credits, 16);
  assert.strictEqual(result.cgpa, 7.56);
});

test('processERPDataForCGPA excludes non-credit/audit courses from calculation', () => {
  const rawRows = [
    { Grade: 'O', Credits: '4' }, // 10 * 4 = 40
    { Grade: 'PASS', Credits: '0' }, // 0 credits -> ignored
    { Grade: 'NC', Credits: '2' }, // Non-credit -> ignored grade
  ];
  const result = processERPDataForCGPA(rawRows);
  assert.strictEqual(result.isOfficial, false);
  assert.strictEqual(result.credits, 4);
  assert.strictEqual(result.cgpa, 10);
});

test('processERPDataForCGPA handles empty or invalid inputs gracefully', () => {
  const result = processERPDataForCGPA([]);
  assert.strictEqual(result.isOfficial, false);
  assert.strictEqual(result.cgpa, 0);
  assert.strictEqual(result.credits, 0);
});
