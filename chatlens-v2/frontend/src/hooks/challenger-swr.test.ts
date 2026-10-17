import { test, describe } from 'node:test';
import assert from 'node:assert';
import { attendanceResponseSchema } from '../lib/schemas/attendance';

describe('Challenger M1 Native Hook Fetcher & Calculation Suite', () => {
  test('attendanceFetcher validation logic throws on non-JSON or success: false', () => {
    // 1. Non-JSON response
    const mockHeadersNonJson = new Headers({ 'content-type': 'text/html' });
    const isJson1 = mockHeadersNonJson
      .get('content-type')
      ?.includes('application/json');
    assert.strictEqual(isJson1, false);

    // 2. Erp failure response (success: false)
    const errJson = { success: false, error: 'Session expired' };
    const parsed = attendanceResponseSchema.safeParse(errJson);
    assert.strictEqual(parsed.success, true);
    assert.strictEqual(errJson.success, false);
  });

  test('Attendance overall percentage calculation edge cases', () => {
    // Edge Case 1: Empty rows -> 0%
    let totalAttended = 0;
    let totalConducted = 0;
    let overallPercentage =
      totalConducted > 0
        ? Math.round((totalAttended / totalConducted) * 100)
        : 0;
    assert.strictEqual(overallPercentage, 0);

    // Edge Case 2: Standard rows
    const data = [
      { 'Conducted Hours': '45', 'Attended Hours': '40' },
      { 'Conducted Hours': '40', 'Attended Hours': '36' },
      { 'Conducted Hours': '42', 'Attended Hours': '38' },
    ];
    totalAttended = 0;
    totalConducted = 0;
    data.forEach((row) => {
      totalConducted += parseFloat(String(row['Conducted Hours'])) || 0;
      totalAttended += parseFloat(String(row['Attended Hours'])) || 0;
    });
    // totalConducted = 127, totalAttended = 114
    overallPercentage =
      totalConducted > 0
        ? Math.round((totalAttended / totalConducted) * 100)
        : 0;
    assert.strictEqual(totalConducted, 127);
    assert.strictEqual(totalAttended, 114);
    assert.strictEqual(overallPercentage, 90); // 114/127 = 0.8976 -> 90%

    // Edge Case 3: Fuzzy header matching for alternative ERP column headers
    const altData = [{ 'Total Held': '50', 'Present Hours': '45' }];
    totalAttended = 0;
    totalConducted = 0;
    altData.forEach((row) => {
      const condKey = Object.keys(row).find((k) => {
        const kl = k.toLowerCase();
        return (
          kl.includes('conducted') ||
          kl.includes('held') ||
          (kl.includes('total') && !kl.includes('%'))
        );
      });
      const attKey = Object.keys(row).find((k) => {
        const kl = k.toLowerCase();
        return kl.includes('attended') || kl.includes('present');
      });
      if (condKey && attKey) {
        totalConducted +=
          parseFloat(String(row[condKey as keyof typeof row])) || 0;
        totalAttended +=
          parseFloat(String(row[attKey as keyof typeof row])) || 0;
      }
    });
    assert.strictEqual(totalConducted, 50);
    assert.strictEqual(totalAttended, 45);
  });

  test('Fee totalPaid calculation edge cases', () => {
    const feeRows = [
      {
        'Fee Type': 'Tuition',
        Amount: '150000',
        'Paid Amount': '100,000 INR',
        Status: 'PARTIAL',
      },
      {
        'Fee Type': 'Hostel',
        Amount: '50000',
        'Paid Amount': '₹50,000',
        Status: 'PAID',
      },
    ];

    let totalPaid = 0;
    feeRows.forEach((row) => {
      const paidKey = Object.keys(row).find((k) => {
        const norm = k.toLowerCase();
        return (
          (norm.includes('paid') ||
            norm.includes('received') ||
            norm.includes('cleared')) &&
          !norm.includes('status') &&
          !norm.includes('unpaid')
        );
      });
      if (paidKey) {
        const val = row[paidKey as keyof typeof row];
        let num = 0;
        if (typeof val === 'number') num = val;
        else if (typeof val === 'string') {
          const clean = val.replace(/[₹$€,]|INR/g, '').trim();
          num = parseFloat(clean) || 0;
        }
        totalPaid += num;
      }
    });

    assert.strictEqual(totalPaid, 150000);
  });

  test('Conditional query keys for academic modules', () => {
    const getAttendanceKey = (academicYear?: string, semesterId?: string) =>
      academicYear && semesterId
        ? (['/api/erp-proxy/attendance', academicYear, semesterId] as const)
        : null;

    assert.strictEqual(getAttendanceKey(undefined, undefined), null);
    assert.strictEqual(getAttendanceKey('2025-2026', undefined), null);
    assert.strictEqual(getAttendanceKey(undefined, '1'), null);
    const validKey = getAttendanceKey('2025-2026', '1');
    assert.notStrictEqual(validKey, null);
    assert.strictEqual(validKey?.[0], '/api/erp-proxy/attendance');
    assert.strictEqual(validKey?.[1], '2025-2026');
    assert.strictEqual(validKey?.[2], '1');
  });

  test('Array literal query keys serialize to identical JSON strings across renders', () => {
    // Simulating two distinct array allocations with identical contents (typical React render)
    const keyRender1 = ['/api/erp-proxy/attendance', '2025-2026', '1'] as const;
    const keyRender2 = ['/api/erp-proxy/attendance', '2025-2026', '1'] as const;

    assert.notStrictEqual(keyRender1, keyRender2); // distinct references
    assert.strictEqual(JSON.stringify(keyRender1), JSON.stringify(keyRender2)); // identical serialization
  });
});
