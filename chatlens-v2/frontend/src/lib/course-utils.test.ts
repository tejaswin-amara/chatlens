import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  getSubjectTitle,
  getSubjectCode,
  registerCourseTitles,
  cleanTitleString,
  extractCoreCode,
  isValidSubjectTitle,
} from './course-utils';

describe('Course Utils & Title Resolution', () => {
  test('resolves explicit distinct course titles', () => {
    const title = getSubjectTitle('25CS1302E', 'Object Oriented Programming');
    assert.equal(title, 'Object Oriented Programming');
  });

  test('strips embedded course code from raw title strings', () => {
    assert.equal(
      getSubjectTitle('25CS1302E', '25CS1302E - Data Structures & Algorithms'),
      'Data Structures & Algorithms'
    );
    assert.equal(
      cleanTitleString('25CS1302E-L: Operating Systems', '25CS1302E-L'),
      'Operating Systems'
    );
  });

  test('falls back to KNOWN_COURSE_MAP when title is equal to code', () => {
    const title = getSubjectTitle('25CS1302E', '25CS1302E');
    assert.equal(title, 'Data Structures & Algorithms');
  });

  test('handles suffix codes e.g. 25CS1302E-L and 25CS1302E_LAB', () => {
    assert.equal(
      getSubjectTitle('25CS1302E-L'),
      'Data Structures & Algorithms'
    );
    assert.equal(
      getSubjectTitle('25CS1302E_LAB'),
      'Data Structures & Algorithms'
    );
  });

  test('resolves core department code for new/unknown academic year prefixes', () => {
    assert.equal(getSubjectTitle('26CS2104E'), 'Operating Systems');
    assert.equal(
      getSubjectTitle('26CS1302E-LAB'),
      'Data Structures & Algorithms'
    );
    assert.equal(extractCoreCode('26CS2104E-L1'), 'CS2104');
  });

  test('registers and resolves dynamic course titles from ERP datasets', () => {
    const mockErpAttendance = [
      {
        'Course Code': '25CS9999E',
        'Course Title': '25CS9999E - Advanced Quantum Computing Systems',
        'Attendance Percentage': '95%',
      },
    ];

    registerCourseTitles(mockErpAttendance);

    const resolvedTitle = getSubjectTitle('25CS9999E');
    assert.equal(resolvedTitle, 'Advanced Quantum Computing Systems');
  });

  test('extracts clean course codes via getSubjectCode', () => {
    assert.equal(getSubjectCode('25CS1302E-L'), '25CS1302E-L');
    assert.equal(
      getSubjectCode('', '25CS1302E-L - S-10 - RoomNo-H-005'),
      '25CS1302E'
    );
  });

  test('isValidSubjectTitle rejects non-subject strings (rooms, faculty, periods, status, sections)', () => {
    assert.equal(isValidSubjectTitle('Dr. Ramesh Kumar', '25CS1302E'), false);
    assert.equal(
      isValidSubjectTitle('Prof. Sarah Jenkins', '25CS1302E'),
      false
    );
    assert.equal(isValidSubjectTitle('RoomNo-101', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('H-005', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('Period 1', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('Period 2', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('Free', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('N/A', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('Section 10', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('S-10', '25CS1302E'), false);
    assert.equal(isValidSubjectTitle('25CS1302E', '25CS1302E'), false);

    assert.equal(
      isValidSubjectTitle('Data Structures & Algorithms', '25CS1302E'),
      true
    );
    assert.equal(
      isValidSubjectTitle('Object-Oriented Programming', '25CS1101E'),
      true
    );
    assert.equal(
      isValidSubjectTitle('Database Management Systems', '25CS2103E'),
      true
    );
  });

  test('getSubjectTitle ignores invalid faculty/room titles and falls back to genuine subject name', () => {
    assert.equal(
      getSubjectTitle('25CS1302E', 'Dr. Smith'),
      'Data Structures & Algorithms'
    );
    assert.equal(
      getSubjectTitle('25CS1302E', 'RoomNo-101'),
      'Data Structures & Algorithms'
    );
    assert.equal(
      getSubjectTitle('25CS1302E', 'Period 1'),
      'Data Structures & Algorithms'
    );
    assert.equal(getSubjectTitle('25CS2104E', 'Free'), 'Operating Systems');
  });
});
