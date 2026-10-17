import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { parseGenericTable, isLikelyTimetableData } from './scraper';
import {
  parseTimetable,
  normalizeDay,
  parseCellContent,
  parseCellContentMultiple,
  normalizeSlotKey,
  isSameDay,
  splitCellSessions,
} from './timetable-parser';

describe('Timetable Day Normalization & DAY_MAP Coverage', () => {
  it('correctly normalizes day order variations (DAY ORDER 1 through 7)', () => {
    const do1Variations = [
      'DAY ORDER - 1',
      'DAY ORDER 1',
      'DAY ORDER 01',
      'DO 1',
      'DO-1',
      'DO 01',
      'D1',
      'DAY 1',
      'day1',
      'Mon',
      'Monday',
    ];

    do1Variations.forEach((varStr) => {
      const result = normalizeDay(varStr);
      assert.notEqual(result, null, `Failed for variation: ${varStr}`);
      assert.equal(result?.full, 'Monday');
      assert.equal(result?.short, 'Mon');
      assert.equal(result?.index, 1);
    });
  });

  it('correctly normalizes Day Order 7 to Sunday', () => {
    const do7Variations = [
      'DAY ORDER - 7',
      'DAY ORDER 07',
      'DO 7',
      'D7',
      'Sunday',
      'Sun',
    ];
    do7Variations.forEach((varStr) => {
      const result = normalizeDay(varStr);
      assert.notEqual(result, null, `Failed for variation: ${varStr}`);
      assert.equal(result?.full, 'Sunday');
      assert.equal(result?.short, 'Sun');
      assert.equal(result?.index, 0);
    });
  });

  it('rejects invalid or period-only numeric day strings', () => {
    assert.equal(normalizeDay('1'), null);
    assert.equal(normalizeDay('P1'), null);
    assert.equal(normalizeDay(''), null);
    assert.equal(normalizeDay('Unknown XYZ Day'), null);
  });

  it('isSameDay correctly matches day aliases', () => {
    assert.equal(isSameDay('DAY ORDER - 1', 'Monday'), true);
    assert.equal(isSameDay('DO 2', 'Tuesday'), true);
    assert.equal(isSameDay('DAY ORDER 5', 'Friday'), true);
    assert.equal(isSameDay('Monday', 'Tuesday'), false);
  });
});

describe('Cell Content Parser (parseCellContent & splitCellSessions)', () => {
  it('correctly parses cells with room numbers', () => {
    const cell = '25CS1302E-L - S-10 - RoomNo-H-005';
    const parsed = parseCellContent(cell);
    assert.equal(parsed.courseCode, '25CS1302E');
    assert.equal(parsed.component, 'Lecture');
    assert.equal(parsed.section, 'S-10');
    assert.equal(parsed.room, 'H-005');
  });

  it('correctly parses cells WITHOUT room numbers without mis-parsing section S-10', () => {
    const cell = '25CS1302E-L - S-10';
    const parsed = parseCellContent(cell);
    assert.equal(parsed.courseCode, '25CS1302E');
    assert.equal(parsed.component, 'Lecture');
    assert.equal(parsed.section, 'S-10');
    assert.equal(parsed.room, '');
  });

  it('correctly parses cells with Skill component and room', () => {
    const cell = '25SC2107E-S - S-10 - RoomNo-H-005';
    const parsed = parseCellContent(cell);
    assert.equal(parsed.courseCode, '25SC2107E');
    assert.equal(parsed.component, 'Skill');
    assert.equal(parsed.section, 'S-10');
    assert.equal(parsed.room, 'H-005');
  });

  it('preserves faculty name if present in cell text', () => {
    const cell = '25CS1302E-L - S-10 - RoomNo-H-005 - Dr. Smith';
    const parsed = parseCellContent(cell);
    assert.equal(parsed.courseCode, '25CS1302E');
    assert.equal(parsed.section, 'S-10');
    assert.equal(parsed.room, 'H-005');
    assert.equal(parsed.faculty, 'Dr. Smith');
  });

  it('handles free/empty/dash cell strings gracefully', () => {
    assert.equal(parseCellContent('-').courseCode, '');
    assert.equal(parseCellContent('Free').courseCode, '');
    assert.equal(parseCellContent('N/A').courseCode, '');
    assert.equal(parseCellContent('').courseCode, '');
  });

  it('splitCellSessions correctly splits multi-session strings by \\n, <br>, ||, and ---', () => {
    const textNewline = '25CS1302E-L - S-10\n25SC2107E-S - S-10';
    assert.deepEqual(splitCellSessions(textNewline), [
      '25CS1302E-L - S-10',
      '25SC2107E-S - S-10',
    ]);

    const textBr = '25CS1302E-L - S-10<br/>25SC2107E-S - S-10';
    assert.deepEqual(splitCellSessions(textBr), [
      '25CS1302E-L - S-10',
      '25SC2107E-S - S-10',
    ]);

    const textBrSpace = '25CS1302E-L - S-10<br />25SC2107E-S - S-10';
    assert.deepEqual(splitCellSessions(textBrSpace), [
      '25CS1302E-L - S-10',
      '25SC2107E-S - S-10',
    ]);

    const textBrPlain = '25CS1302E-L - S-10<br>25SC2107E-S - S-10';
    assert.deepEqual(splitCellSessions(textBrPlain), [
      '25CS1302E-L - S-10',
      '25SC2107E-S - S-10',
    ]);

    const textPipes = '25CS1302E-L - S-10 || 25SC2107E-S - S-10';
    assert.deepEqual(splitCellSessions(textPipes), [
      '25CS1302E-L - S-10',
      '25SC2107E-S - S-10',
    ]);

    const textDashes =
      '22CS1101-P - S-05 - RoomNo-C-101 --- 25SC2107E-S - S-10';
    assert.deepEqual(splitCellSessions(textDashes), [
      '22CS1101-P - S-05 - RoomNo-C-101',
      '25SC2107E-S - S-10',
    ]);
  });
});

describe('Cell Content Multiple Parser (parseCellContentMultiple)', () => {
  it('correctly parses multiple session strings separated by \\n, <br/>, or ||', () => {
    const text =
      '25CS1302E-L - S-10 - RoomNo-H-005\n25SC2107E-S - S-10 - RoomNo-H-006';
    const parsed = parseCellContentMultiple(text);
    assert.equal(parsed.length, 2);
    assert.equal(parsed[0].courseCode, '25CS1302E');
    assert.equal(parsed[0].component, 'Lecture');
    assert.equal(parsed[0].room, 'H-005');
    assert.equal(parsed[1].courseCode, '25SC2107E');
    assert.equal(parsed[1].component, 'Skill');
    assert.equal(parsed[1].room, 'H-006');

    const pipeText = '22CS1101-P - S-05 || 25SC2107E-S - S-10';
    const pipeParsed = parseCellContentMultiple(pipeText);
    assert.equal(pipeParsed.length, 2);
    assert.equal(pipeParsed[0].courseCode, '22CS1101');
    assert.equal(pipeParsed[1].courseCode, '25SC2107E');
  });

  it('handles empty or dash text gracefully returning empty array', () => {
    assert.deepEqual(parseCellContentMultiple(''), []);
    assert.deepEqual(parseCellContentMultiple('-'), []);
    assert.deepEqual(parseCellContentMultiple('Free'), []);
  });
});

describe('HTML Parsing & Matrix Formats (parseGenericTable & parseTimetable)', () => {
  it('parses matrix_days_rows layout format producing complete matrix grids', () => {
    const htmlPayload = `
      <table class="table table-bordered">
        <thead>
          <tr>
            <th>Day / Period</th>
            <th>1</th>
            <th>2</th>
            <th>3</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Monday</td>
            <td>25CS1302E-L - S-10 - RoomNo-H-005</td>
            <td>25SC2107E-S - S-10</td>
            <td>Free</td>
          </tr>
          <tr>
            <td>Tuesday</td>
            <td>22CS1101-L - S-05 - RoomNo-C-101</td>
            <td>-</td>
            <td>25CS1302E-P - S-10 - RoomNo-LAB-2</td>
          </tr>
        </tbody>
      </table>
    `;

    const rawRows = parseGenericTable(htmlPayload);
    assert.equal(rawRows.length, 2);
    assert.equal(isLikelyTimetableData(rawRows), true);

    const parsedTT = parseTimetable(rawRows);
    assert.equal(parsedTT.layout, 'matrix_days_rows');
    assert.ok(parsedTT.daysPresent.includes('Monday'));
    assert.ok(parsedTT.daysPresent.includes('Tuesday'));
    assert.ok(parsedTT.timeSlotsPresent.includes('1'));
    assert.ok(parsedTT.timeSlotsPresent.includes('2'));
    assert.ok(parsedTT.timeSlotsPresent.includes('3'));

    assert.ok(Array.isArray(parsedTT.matrixGrid['Monday']['1']));
    assert.equal(parsedTT.matrixGrid['Monday']['1'][0].courseCode, '25CS1302E');
    assert.equal(parsedTT.matrixGrid['Monday']['1'][0].room, 'H-005');

    assert.ok(Array.isArray(parsedTT.matrixGrid['Tuesday']['3']));
    assert.equal(
      parsedTT.matrixGrid['Tuesday']['3'][0].courseCode,
      '25CS1302E'
    );
    assert.equal(parsedTT.matrixGrid['Tuesday']['3'][0].component, 'Practical');
    assert.equal(parsedTT.matrixGrid['Tuesday']['3'][0].room, 'LAB-2');
  });

  it('parses matrix_days_columns layout format producing complete matrix grids', () => {
    const htmlPayload = `
      <table class="table table-striped">
        <thead>
          <tr>
            <th>Period / Day</th>
            <th>Monday</th>
            <th>Tuesday</th>
            <th>Wednesday</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td>25CS1302E-L - S-10 - RoomNo-H-005</td>
            <td>22CS1101-L - S-05 - RoomNo-C-101</td>
            <td>Free</td>
          </tr>
          <tr>
            <td>2</td>
            <td>25SC2107E-S - S-10</td>
            <td>-</td>
            <td>25CS1302E-P - S-10 - RoomNo-LAB-2</td>
          </tr>
        </tbody>
      </table>
    `;

    const rawRows = parseGenericTable(htmlPayload);
    assert.equal(rawRows.length, 2);
    assert.equal(isLikelyTimetableData(rawRows), true);

    const parsedTT = parseTimetable(rawRows);
    assert.equal(parsedTT.layout, 'matrix_days_columns');
    assert.ok(parsedTT.daysPresent.includes('Monday'));
    assert.ok(parsedTT.daysPresent.includes('Tuesday'));
    assert.ok(parsedTT.daysPresent.includes('Wednesday'));

    // Check Monday Period 1
    assert.ok(Array.isArray(parsedTT.matrixGrid['Monday']['1']));
    assert.equal(parsedTT.matrixGrid['Monday']['1'][0].courseCode, '25CS1302E');
    assert.equal(parsedTT.matrixGrid['Monday']['1'][0].component, 'Lecture');
    assert.equal(parsedTT.matrixGrid['Monday']['1'][0].room, 'H-005');

    // Check Tuesday Period 1
    assert.ok(Array.isArray(parsedTT.matrixGrid['Tuesday']['1']));
    assert.equal(parsedTT.matrixGrid['Tuesday']['1'][0].courseCode, '22CS1101');
    assert.equal(parsedTT.matrixGrid['Tuesday']['1'][0].room, 'C-101');

    // Check Wednesday Period 2
    assert.ok(Array.isArray(parsedTT.matrixGrid['Wednesday']['2']));
    assert.equal(
      parsedTT.matrixGrid['Wednesday']['2'][0].courseCode,
      '25CS1302E'
    );
    assert.equal(
      parsedTT.matrixGrid['Wednesday']['2'][0].component,
      'Practical'
    );
    assert.equal(parsedTT.matrixGrid['Wednesday']['2'][0].room, 'LAB-2');
  });

  it('correctly parses multi-session cells in matrix formats without dropping sessions', () => {
    const htmlPayload = `
      <table class="table table-bordered">
        <thead>
          <tr>
            <th>Day / Period</th>
            <th>1</th>
            <th>2</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Monday</td>
            <td>25CS1302E-L - S-10 - RoomNo-H-005<br/>25SC2107E-S - S-10 - RoomNo-H-006</td>
            <td>22CS1101-P - S-05 || 25SC2107E-S - S-10</td>
          </tr>
          <tr>
            <td>Tuesday</td>
            <td>25CS1302E-P - S-10 --- 22CS1101-L - S-05</td>
            <td>Free</td>
          </tr>
        </tbody>
      </table>
    `;

    const rawRows = parseGenericTable(htmlPayload);
    assert.equal(rawRows.length, 2);

    const parsedTT = parseTimetable(rawRows);
    assert.equal(parsedTT.layout, 'matrix_days_rows');

    // Monday Period 1 should have 2 sessions (<br/> separated)
    const mon1Sessions = parsedTT.matrixGrid['Monday']['1'];
    assert.ok(Array.isArray(mon1Sessions));
    assert.equal(mon1Sessions.length, 2);
    assert.equal(mon1Sessions[0].courseCode, '25CS1302E');
    assert.equal(mon1Sessions[0].component, 'Lecture');
    assert.equal(mon1Sessions[0].room, 'H-005');
    assert.equal(mon1Sessions[1].courseCode, '25SC2107E');
    assert.equal(mon1Sessions[1].component, 'Skill');
    assert.equal(mon1Sessions[1].room, 'H-006');

    // Monday Period 2 should have 2 sessions (|| separated)
    const mon2Sessions = parsedTT.matrixGrid['Monday']['2'];
    assert.ok(Array.isArray(mon2Sessions));
    assert.equal(mon2Sessions.length, 2);
    assert.equal(mon2Sessions[0].courseCode, '22CS1101');
    assert.equal(mon2Sessions[0].component, 'Practical');
    assert.equal(mon2Sessions[1].courseCode, '25SC2107E');
    assert.equal(mon2Sessions[1].component, 'Skill');

    // Tuesday Period 1 should have 2 sessions (--- separated)
    const tue1Sessions = parsedTT.matrixGrid['Tuesday']['1'];
    assert.ok(Array.isArray(tue1Sessions));
    assert.equal(tue1Sessions.length, 2);
    assert.equal(tue1Sessions[0].courseCode, '25CS1302E');
    assert.equal(tue1Sessions[0].component, 'Practical');
    assert.equal(tue1Sessions[1].courseCode, '22CS1101');
    assert.equal(tue1Sessions[1].component, 'Lecture');

    // Verify all 6 total sessions are preserved in parsedTT.sessions
    assert.equal(parsedTT.sessions.length, 6);
  });

  it('correctly parses multi-session cells with <br/> tags in matrix_days_columns HTML layout', () => {
    const htmlPayload = `
      <table class="table table-bordered">
        <thead>
          <tr>
            <th>Period / Day</th>
            <th>Monday</th>
            <th>Tuesday</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td>25CS1302E-L - S-10 - RoomNo-H-005<br/>25SC2107E-S - S-10 - RoomNo-H-006</td>
            <td>22CS1101-L - S-05 - RoomNo-C-101<br />25SC2107E-S - S-10 - RoomNo-C-102</td>
          </tr>
          <tr>
            <td>2</td>
            <td>22CS1101-P - S-05<br>25CS1302E-P - S-10</td>
            <td>Free</td>
          </tr>
        </tbody>
      </table>
    `;

    const rawRows = parseGenericTable(htmlPayload);
    assert.equal(rawRows.length, 2);
    assert.equal(isLikelyTimetableData(rawRows), true);

    const parsedTT = parseTimetable(rawRows);
    assert.equal(parsedTT.layout, 'matrix_days_columns');

    // Monday Period 1 has 2 sessions separated by <br/>
    const mon1 = parsedTT.matrixGrid['Monday']['1'];
    assert.ok(Array.isArray(mon1));
    assert.equal(mon1.length, 2);
    assert.equal(mon1[0].courseCode, '25CS1302E');
    assert.equal(mon1[0].component, 'Lecture');
    assert.equal(mon1[0].room, 'H-005');
    assert.equal(mon1[1].courseCode, '25SC2107E');
    assert.equal(mon1[1].component, 'Skill');
    assert.equal(mon1[1].room, 'H-006');

    // Tuesday Period 1 has 2 sessions separated by <br />
    const tue1 = parsedTT.matrixGrid['Tuesday']['1'];
    assert.ok(Array.isArray(tue1));
    assert.equal(tue1.length, 2);
    assert.equal(tue1[0].courseCode, '22CS1101');
    assert.equal(tue1[0].component, 'Lecture');
    assert.equal(tue1[0].room, 'C-101');
    assert.equal(tue1[1].courseCode, '25SC2107E');
    assert.equal(tue1[1].component, 'Skill');
    assert.equal(tue1[1].room, 'C-102');

    // Monday Period 2 has 2 sessions separated by <br>
    const mon2 = parsedTT.matrixGrid['Monday']['2'];
    assert.ok(Array.isArray(mon2));
    assert.equal(mon2.length, 2);
    assert.equal(mon2[0].courseCode, '22CS1101');
    assert.equal(mon2[0].component, 'Practical');
    assert.equal(mon2[1].courseCode, '25CS1302E');
    assert.equal(mon2[1].component, 'Practical');

    assert.equal(parsedTT.sessions.length, 6);
  });

  it('parses list format timetable HTML payload cleanly', () => {
    const htmlPayload = `
      <table class="table">
        <thead>
          <tr>
            <th>Day</th>
            <th>Time Slot</th>
            <th>Course Code</th>
            <th>Course Title</th>
            <th>Section</th>
            <th>Venue</th>
            <th>Faculty</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Day Order 2</td>
            <td>09:00 AM - 09:50 AM</td>
            <td>25CS1302E-L</td>
            <td>Database Systems</td>
            <td>S-10</td>
            <td>H-005</td>
            <td>Dr. John Doe</td>
          </tr>
        </tbody>
      </table>
    `;

    const rawRows = parseGenericTable(htmlPayload);
    assert.equal(rawRows.length, 1);
    assert.equal(isLikelyTimetableData(rawRows), true);

    const parsedTT = parseTimetable(rawRows);
    assert.equal(parsedTT.sessions.length, 1);
    const session = parsedTT.sessions[0];
    assert.equal(session.day, 'Tuesday');
    assert.equal(session.timeSlot, '09:00 AM - 09:50 AM');
    assert.equal(session.courseCode, '25CS1302E');
    assert.equal(session.courseTitle, 'Database Systems');
    assert.equal(session.room, 'H-005');
    assert.equal(session.faculty, 'Dr. John Doe');
  });
});

describe('Slot Key Normalization', () => {
  it('normalizes P1, Period 1, and numeric strings', () => {
    assert.equal(normalizeSlotKey('1'), '1');
    assert.equal(normalizeSlotKey('P1'), '1');
    assert.equal(normalizeSlotKey('Period 2'), '2');
    assert.equal(
      normalizeSlotKey('09:00 AM - 09:50 AM'),
      '09:00 AM - 09:50 AM'
    );
  });
});
