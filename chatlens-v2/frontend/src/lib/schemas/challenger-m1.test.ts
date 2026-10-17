import { test, describe } from 'node:test';
import assert from 'node:assert';
import {
  attendanceSubjectSchema,
  attendanceResponseSchema,
  feeItemSchema,
  feeResponseSchema,
  marksSubjectSchema,
  profileDataSchema,
  timetableSlotSchema,
  rawTimetableRowSchema,
  loginRequestSchema,
} from './index';

describe('Challenger M1 Schema Validation & .passthrough() Suite', () => {
  test('attendanceSubjectSchema preserves unmapped dynamic ERP columns via .passthrough()', () => {
    const rawERPPayload = {
      'Course Code': '23CS2101R',
      'Course Title': 'Data Structures',
      'Conducted Hours': '45',
      'Attended Hours': 40,
      'Attendance Percentage': '88.89%',
      'Academic Year': '2025-2026',
      Semester: '1',
      // Unmapped / Dynamic ERP columns
      'Faculty Name': 'Dr. Smith',
      'Section Code': 'S-10',
      __erp_meta_id: 998823,
    };

    const parsed = attendanceSubjectSchema.safeParse(rawERPPayload);
    assert.strictEqual(parsed.success, true);
    if (parsed.success) {
      assert.strictEqual(parsed.data['Course Code'], '23CS2101R');
      assert.strictEqual(parsed.data['Conducted Hours'], '45');
      assert.strictEqual(parsed.data['Attended Hours'], 40);
      // Verify passthrough behavior explicitly
      assert.strictEqual(parsed.data['Faculty Name'], 'Dr. Smith');
      assert.strictEqual(parsed.data['Section Code'], 'S-10');
      assert.strictEqual(parsed.data['__erp_meta_id'], 998823);
    }
  });

  test('attendanceResponseSchema correctly validates standard and alternative data keys', () => {
    const validWithAttendanceData = {
      success: true,
      attendanceData: [
        {
          'Course Code': 'CS101',
          'Attended Hours': '20',
          ExtraField: 'Value1',
        },
      ],
    };
    const parsed1 = attendanceResponseSchema.safeParse(validWithAttendanceData);
    assert.strictEqual(parsed1.success, true);
    if (parsed1.success && parsed1.data.attendanceData) {
      assert.strictEqual(
        parsed1.data.attendanceData[0]['ExtraField'],
        'Value1'
      );
    }

    const validWithData = {
      success: true,
      data: [{ 'Course Code': 'CS102', ExtraField: 'Value2' }],
    };
    const parsed2 = attendanceResponseSchema.safeParse(validWithData);
    assert.strictEqual(parsed2.success, true);

    const invalidSuccess = {
      success: 'true', // wrong type (string instead of boolean)
    };
    const parsed3 = attendanceResponseSchema.safeParse(invalidSuccess);
    assert.strictEqual(parsed3.success, false);
  });

  test('feeItemSchema preserves dynamic ERP fee columns via .passthrough()', () => {
    const rawFeePayload = {
      'Fee Type': 'Tuition Fee',
      Amount: 150000,
      'Paid Amount': '100000',
      'Balance Amount': 50000,
      Status: 'PARTIAL',
      'Receipt No': 'REC-2026-001',
      'Due Date': '2026-09-01',
    };

    const parsed = feeItemSchema.safeParse(rawFeePayload);
    assert.strictEqual(parsed.success, true);
    if (parsed.success) {
      assert.strictEqual(parsed.data['Fee Type'], 'Tuition Fee');
      assert.strictEqual(parsed.data.Amount, 150000);
      assert.strictEqual(parsed.data['Receipt No'], 'REC-2026-001');
      assert.strictEqual(parsed.data['Due Date'], '2026-09-01');
    }
  });

  test('feeResponseSchema validates response structure', () => {
    const payload = {
      success: true,
      data: [{ 'Fee Type': 'Exam Fee', Amount: 5000 }],
    };
    const parsed = feeResponseSchema.safeParse(payload);
    assert.strictEqual(parsed.success, true);
  });

  test('marksSubjectSchema preserves unmapped mark components via .passthrough()', () => {
    const rawMarksPayload = {
      'Course Code': '23CS2101R',
      'Course Name': 'Data Structures',
      'Faculty Name': 'Dr. Smith',
      'Internal 1': '22',
      'Internal 2': '24',
      Assignment: '10',
      'Total Marks': '56',
      // Unmapped components in custom ERP layouts
      'Lab Exam': '18',
      'Quiz 1': '5',
      'Grade Earned': 'A+',
    };

    const parsed = marksSubjectSchema.safeParse(rawMarksPayload);
    assert.strictEqual(parsed.success, true);
    if (parsed.success) {
      assert.strictEqual(parsed.data['Lab Exam'], '18');
      assert.strictEqual(parsed.data['Quiz 1'], '5');
      assert.strictEqual(parsed.data['Grade Earned'], 'A+');
    }
  });

  test('profileDataSchema preserves extra student metadata via .passthrough()', () => {
    const rawProfile = {
      name: 'Alex Student',
      universityId: '2100030000',
      photoUrl: '/photo.jpg',
      extendedProfile: '{"dept":"CSE"}',
      success: true,
      // Extra fields
      bloodGroup: 'O+',
      guardianPhone: '+919999999999',
    };

    const parsed = profileDataSchema.safeParse(rawProfile);
    assert.strictEqual(parsed.success, true);
    if (parsed.success) {
      assert.strictEqual(parsed.data.name, 'Alex Student');
      assert.strictEqual(parsed.data['bloodGroup'], 'O+');
      assert.strictEqual(parsed.data['guardianPhone'], '+919999999999');
    }
  });

  test('timetableSlotSchema & rawTimetableRowSchema validate arbitrary timetable rows', () => {
    const rawRow = {
      'Day / Period': 'Monday',
      '1': '23CS2101R-L - S-10 - Room 101',
      '2': '23CS2102R-P - S-10 - Lab 1',
      ArbitraryCol: 'ArbitraryVal',
    };

    const parsedRaw = rawTimetableRowSchema.safeParse(rawRow);
    assert.strictEqual(parsedRaw.success, true);
    if (parsedRaw.success) {
      assert.strictEqual(parsedRaw.data['ArbitraryCol'], 'ArbitraryVal');
    }

    const slotPayload = {
      day: 'Monday',
      timeSlot: '09:00 - 10:00',
      courseCode: '23CS2101R',
      courseTitle: 'DSA',
      room: '101',
    };
    const parsedSlot = timetableSlotSchema.safeParse(slotPayload);
    assert.strictEqual(parsedSlot.success, true);

    const invalidSlot = {
      day: 'Monday',
      // missing timeSlot and courseCode
    };
    const parsedInvalidSlot = timetableSlotSchema.safeParse(invalidSlot);
    assert.strictEqual(parsedInvalidSlot.success, false);
  });

  test('loginRequestSchema enforces required field non-emptiness', () => {
    const validLogin = {
      username: '2100030000',
      password: 'password123',
      captcha: 'ABCD',
      session: {
        cookies: [{ name: 'PHPSESSID', value: '12345' }],
        csrfToken: 'csrf123',
      },
    };
    assert.strictEqual(loginRequestSchema.safeParse(validLogin).success, true);

    const emptyUser = { ...validLogin, username: '' };
    assert.strictEqual(loginRequestSchema.safeParse(emptyUser).success, false);

    const emptyPass = { ...validLogin, password: '' };
    assert.strictEqual(loginRequestSchema.safeParse(emptyPass).success, false);

    const emptyCaptcha = { ...validLogin, captcha: '' };
    assert.strictEqual(
      loginRequestSchema.safeParse(emptyCaptcha).success,
      false
    );
  });
});
