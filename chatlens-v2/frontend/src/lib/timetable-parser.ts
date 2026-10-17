import { getSubjectTitle, isValidSubjectTitle } from './course-utils';

export interface NormalizedClassSession {
  id: string;
  day: string; // Normalized day name e.g. 'Monday'
  dayShort: string; // Normalized short day e.g. 'Mon'
  dayIndex: number; // 0=Sun, 1=Mon, ..., 6=Sat (-1 if Day Order/Unknown)
  timeSlot: string; // e.g. '09:00 AM - 10:00 AM' or 'Period 1'
  courseCode: string; // e.g. '25CS1302E'
  courseTitle: string; // e.g. 'DATABASE SYSTEMS ENGINEERING AND DISTRIBUTED BACKEND DEVELOPMENT'
  component?: string; // e.g. 'Lecture', 'Practical', 'Skill', 'Tutorial'
  section?: string; // e.g. 'S-10'
  room: string; // e.g. 'H-005'
  faculty: string; // e.g. 'khaja shareef sk'
  rawText: string; // Original cell string
}

export type TimetableLayoutType =
  'matrix_days_columns' | 'matrix_days_rows' | 'list_rows' | 'unknown';

export interface ParsedTimetable {
  layout: TimetableLayoutType;
  headers: string[];
  rawRows: Array<Record<string, unknown>>;
  sessions: NormalizedClassSession[];
  daysPresent: string[];
  timeSlotsPresent: string[];
  matrixGrid: Record<string, Record<string, NormalizedClassSession[]>>; // day -> timeSlot -> array of sessions
}

function expandTimeSlots(raw: string): string[] {
  const str = String(raw).trim().toUpperCase();

  // If it looks like a time string (e.g., 09:30-10:20), do not mangle it
  if (str.includes(':')) {
    return [str];
  }

  const periods = new Set<string>();

  const rangeRegex = /(\d+)\s*-\s*(\d+)/g;
  let match;
  let hasRange = false;
  while ((match = rangeRegex.exec(str)) !== null) {
    hasRange = true;
    const start = parseInt(match[1], 10);
    const end = parseInt(match[2], 10);
    if (start <= end && end - start < 15) {
      for (let i = start; i <= end; i++) {
        periods.add(String(i));
      }
    }
  }

  if (!hasRange) {
    const numRegex = /\d+/g;
    while ((match = numRegex.exec(str)) !== null) {
      periods.add(match[0]);
    }
  }

  if (periods.size === 0) {
    return [str];
  }
  return Array.from(periods);
}

const dayDefinitions: Array<{
  names: string[];
  full: string;
  short: string;
  index: number;
}> = [
  { names: ['monday', 'mon'], full: 'Monday', short: 'Mon', index: 1 },
  {
    names: ['tuesday', 'tue', 'tues'],
    full: 'Tuesday',
    short: 'Tue',
    index: 2,
  },
  { names: ['wednesday', 'wed'], full: 'Wednesday', short: 'Wed', index: 3 },
  {
    names: ['thursday', 'thu', 'thur', 'thurs'],
    full: 'Thursday',
    short: 'Thu',
    index: 4,
  },
  { names: ['friday', 'fri'], full: 'Friday', short: 'Fri', index: 5 },
  { names: ['saturday', 'sat'], full: 'Saturday', short: 'Sat', index: 6 },
  { names: ['sunday', 'sun'], full: 'Sunday', short: 'Sun', index: 0 },
];

const DAY_MAP: Record<string, { full: string; short: string; index: number }> =
  {};

dayDefinitions.forEach((def) => {
  def.names.forEach((name) => {
    DAY_MAP[name] = { full: def.full, short: def.short, index: def.index };
  });
});

const dayOrderMapping: Array<{ full: string; short: string; index: number }> = [
  { full: 'Monday', short: 'Mon', index: 1 },
  { full: 'Tuesday', short: 'Tue', index: 2 },
  { full: 'Wednesday', short: 'Wed', index: 3 },
  { full: 'Thursday', short: 'Thu', index: 4 },
  { full: 'Friday', short: 'Fri', index: 5 },
  { full: 'Saturday', short: 'Sat', index: 6 },
  { full: 'Sunday', short: 'Sun', index: 0 },
];

dayOrderMapping.forEach((def, idx) => {
  const i = idx + 1;
  const numStr = String(i);
  const padStr = i < 10 ? `0${i}` : String(i);

  const variations = [
    `day order ${numStr}`,
    `day order ${padStr}`,
    `dayorder${numStr}`,
    `dayorder${padStr}`,
    `do ${numStr}`,
    `do ${padStr}`,
    `do${numStr}`,
    `do${padStr}`,
    `d${numStr}`,
    `d${padStr}`,
    `day ${numStr}`,
    `day ${padStr}`,
    `day${numStr}`,
    `day${padStr}`,
  ];

  variations.forEach((v) => {
    DAY_MAP[v] = { full: def.full, short: def.short, index: def.index };
  });
});

/**
 * Normalizes a time slot or period string (e.g. '1', 'P1', 'Period 1') into a clean canonical key (e.g. '1').
 */
export function normalizeSlotKey(slotStr: string): string {
  if (!slotStr) return '';
  const str = String(slotStr).trim().toUpperCase();
  const match = str.match(/^(?:PERIOD\s*|P\s*)?(\d+)$/i);
  if (match) {
    return match[1];
  }
  return str;
}

/**
 * Normalizes day string representation (e.g. 'Mon', 'Monday', 'Day 1') into a structured object.
 * Rejects pure numbers (e.g. '1', '2', '3') to prevent period numbers from being misclassified as days.
 */
export function normalizeDay(
  dayStr: string
): { full: string; short: string; index: number } | null {
  if (!dayStr) return null;
  const clean = dayStr
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!clean || /^\d+$/.test(clean)) return null;

  // Direct lookup
  if (DAY_MAP[clean]) return DAY_MAP[clean];

  // Token / word matching
  const words = clean.split(/\s+/);
  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    if (DAY_MAP[word]) return DAY_MAP[word];
    if (i < words.length - 1) {
      const phrase = `${words[i]} ${words[i + 1]}`;
      if (DAY_MAP[phrase]) return DAY_MAP[phrase];
    }
  }

  return null;
}

/**
 * Checks if two day strings refer to the same day of the week or day order.
 */
export function isSameDay(dayA: string, dayB: string): boolean {
  if (!dayA || !dayB) return false;
  const normA = normalizeDay(dayA);
  const normB = normalizeDay(dayB);
  if (normA && normB) {
    return normA.full === normB.full;
  }
  return dayA.toLowerCase().trim() === dayB.toLowerCase().trim();
}

/**
 * Splits a timetable cell string into individual session blocks if it contains multiple class sessions
 * separated by newlines (\n), HTML break tags (<br>), double pipes (||), or triple dashes (---).
 */
export function splitCellSessions(text: string): string[] {
  if (!text || typeof text !== 'string') return [];

  const clean = text.replace(/<br\s*\/?>/gi, '\n');

  const blocks = clean
    .split(/[\r\n]+|\|{2,}|-{3,}/)
    .map((b) => b.trim())
    .filter((b) => {
      if (!b) return false;
      const lower = b.toLowerCase();
      return (
        lower !== '-' &&
        lower !== '- - -' &&
        lower !== 'free' &&
        lower !== 'n/a'
      );
    });

  return blocks;
}

/**
 * Smart Cell Parser: Robustly parses course code, course title, room/venue, and faculty from cell strings.
 * Handles multi-hyphen strings ("22-CS-1101", "C-101 - Lab", "22-CS-1101 - Data Structures - C-101 - Dr. Smith").
 */
export function parseCellContent(text: string): {
  courseCode: string;
  courseTitle: string;
  component?: string;
  section?: string;
  room: string;
  faculty: string;
} {
  if (
    !text ||
    text.trim() === '' ||
    text.trim() === '-' ||
    text.trim() === '- - -' ||
    text.toLowerCase().trim() === 'free' ||
    text.toLowerCase().trim() === 'n/a'
  ) {
    return { courseCode: '', courseTitle: '', room: '', faculty: '' };
  }

  const sessionBlocks = splitCellSessions(text);
  if (sessionBlocks.length > 1) {
    return parseCellContent(sessionBlocks[0]);
  }

  const raw = text.trim();

  // 1. Extract Course Code & Component Suffix (e.g. 25CS1302E-L, 25SC2107E_S)
  let courseCode = '';
  let componentLetter = '';

  const klCodeMatch = raw.match(
    /([0-9]{2}[A-Z]{2,5}[0-9]{3,4}[A-Z]?|[A-Z]{2,5}[0-9]{3,4}[A-Z]?)[-_]([LTPSS])\b/i
  );
  if (klCodeMatch) {
    courseCode = klCodeMatch[1].toUpperCase();
    componentLetter = klCodeMatch[2].toUpperCase();
  } else {
    const codeMatch = raw.match(
      /([0-9]{2}[A-Z]{2,5}[0-9]{3,4}[A-Z]?|[A-Z]{2,5}[0-9]{3,4}[A-Z]?)/i
    );
    if (codeMatch) {
      courseCode = codeMatch[1].toUpperCase();
    }
  }

  const compMap: Record<string, string> = {
    L: 'Lecture',
    P: 'Practical',
    S: 'Skill',
    T: 'Tutorial',
  };
  const component = componentLetter
    ? compMap[componentLetter] || componentLetter
    : undefined;

  // 2. Extract Section (e.g. S-10, SEC-10, SECTION 10, L-10, P-10)
  let section: string | undefined = undefined;
  const secMatch = raw.match(/\b(SEC(?:TION)?[-:\s]*\d+|S-\d+|[LPS]-\d+)\b/i);
  if (secMatch) {
    section = secMatch[1].toUpperCase().replace(/\s+/g, '-');
  }

  // 3. Extract Room / Venue (room matching is optional)
  let room = '';
  const explicitRoomMatch = raw.match(
    /(?:RoomNo|Room|Hall|Lab|Venue)[-:\s]*([A-Z0-9-]+)/i
  );
  if (explicitRoomMatch) {
    room = explicitRoomMatch[1].replace(/^RoomNo-/i, '').trim();
  } else {
    const roomCandidates = raw.match(
      /\b([A-Z]{1,4}[-_\s]?\d{3,4}|[A-Z]-\d{2,4})\b/gi
    );
    if (roomCandidates) {
      for (const cand of roomCandidates) {
        const cleanCand = cand.toUpperCase().trim();
        if (courseCode && cleanCand.includes(courseCode)) continue;
        if (section && cleanCand === section.toUpperCase()) continue;
        if (/^S-\d+$/i.test(cleanCand)) continue;
        if (/^(MON|TUE|WED|THU|FRI|SAT|SUN)$/i.test(cleanCand)) continue;
        room = cleanCand;
        break;
      }
    }
  }

  // 4. Extract Faculty Name if present
  let faculty = '';
  const facultyPrefixMatch = raw.match(
    /(?:Faculty|Instructor|Staff|Teacher)[-:\s]*([A-Za-z\s.]+)/i
  );
  if (facultyPrefixMatch) {
    faculty = facultyPrefixMatch[1].trim();
  } else {
    const parts = raw
      .split(/\n|\|\||\s+-\s+|\s+\/\s+/)
      .map((p) => p.trim())
      .filter(Boolean);
    for (const part of parts) {
      if (
        /^(Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)/i.test(part) ||
        (/^[A-Za-z\s.]{4,}$/.test(part) &&
          !/^(Lecture|Practical|Skill|Tutorial|RoomNo|Room|Hall|Lab|Venue|Free|N\/A|Period|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Day)/i.test(
            part
          ))
      ) {
        const cleanPart = part.trim();
        const upperPart = cleanPart.toUpperCase();
        if (
          upperPart !== courseCode &&
          upperPart !== section &&
          upperPart !== room &&
          !isValidSubjectTitle(cleanPart, courseCode) &&
          !/^(MON|TUE|WED|THU|FRI|SAT|SUN|DAY|PERIOD)/i.test(cleanPart)
        ) {
          faculty = cleanPart;
          break;
        }
      }
    }
  }

  // 5. Extract Course Title from raw parts if present
  let courseTitle = '';
  const parenMatch = raw.match(/\(([^)]+)\)/);
  if (parenMatch && isValidSubjectTitle(parenMatch[1], courseCode)) {
    courseTitle = parenMatch[1].trim();
  } else {
    const structuredParts = raw
      .split(/\n|\|\||\s+-\s+|\s+\/\s+/)
      .map((p) => p.trim())
      .filter(Boolean);

    for (const part of structuredParts) {
      const clean = part.trim();
      const upper = clean.toUpperCase();

      if (courseCode && upper.includes(courseCode)) continue;
      if (section && upper === section.toUpperCase()) continue;
      if (room && upper === room.toUpperCase()) continue;
      if (faculty && upper === faculty.toUpperCase()) continue;

      if (isValidSubjectTitle(clean, courseCode)) {
        courseTitle = clean;
        break;
      }
    }
  }

  const code = courseCode || raw;
  const resolvedTitle = getSubjectTitle(code, courseTitle);

  return {
    courseCode: code,
    courseTitle: resolvedTitle,
    component,
    section,
    room,
    faculty,
  };
}

/**
 * Parses multiple class sessions in a single table cell text, splitting by newlines (\n) or double pipes (||).
 */
export function parseCellContentMultiple(
  text: string
): Array<ReturnType<typeof parseCellContent>> {
  if (!text || typeof text !== 'string') return [];
  const blocks = splitCellSessions(text);
  return blocks
    .map((block) => parseCellContent(block))
    .filter((parsed) => Boolean(parsed.courseCode));
}

/**
 * Universal timetable parser that auto-detects layout format:
 * - Matrix Days-as-Columns (`headers` have day names)
 * - Matrix Days-as-Rows (Row 0 has day names in col 0)
 * - List Timetables (Rows have Day, Time, Course, Room, Faculty)
 */
export function parseTimetable(
  rawRows: Array<Record<string, unknown>> | Array<Record<string, string>>
): ParsedTimetable {
  if (!rawRows || !Array.isArray(rawRows) || rawRows.length === 0) {
    return {
      layout: 'unknown',
      headers: [],
      rawRows: [],
      sessions: [],
      daysPresent: [],
      timeSlotsPresent: [],
      matrixGrid: {},
    };
  }

  const headers = Object.keys(rawRows[0] || {});
  if (headers.length === 0) {
    return {
      layout: 'unknown',
      headers: [],
      rawRows: [],
      sessions: [],
      daysPresent: [],
      timeSlotsPresent: [],
      matrixGrid: {},
    };
  }

  const dayHeaders = headers.filter((h) => normalizeDay(h) !== null);
  const dayColKey = headers.find((h) => {
    const validCount = rawRows.filter(
      (r) => normalizeDay(String(r[h] || '')) !== null
    ).length;
    return validCount >= 1;
  });

  const nonDayHeaders = headers.filter(
    (h) => h !== dayColKey && normalizeDay(h) === null
  );
  const periodHeaderMatches = nonDayHeaders.filter(
    (h) =>
      /^\d{1,2}$/.test(normalizeSlotKey(h)) ||
      /^period\s*\d{1,2}$/i.test(h) ||
      /\d{1,2}:\d{2}/.test(h)
  ).length;

  let layout: TimetableLayoutType = 'unknown';
  if (dayHeaders.length >= 2) {
    layout = 'matrix_days_columns';
  } else if (
    dayColKey &&
    (periodHeaderMatches >= 1 ||
      (nonDayHeaders.length >= 2 &&
        !nonDayHeaders.some(
          (h) =>
            h.toLowerCase().includes('course') ||
            h.toLowerCase().includes('code') ||
            h.toLowerCase().includes('section') ||
            h.toLowerCase().includes('faculty')
        )))
  ) {
    layout = 'matrix_days_rows';
  } else if (dayColKey || dayHeaders.length > 0) {
    const hasDetailCols = headers.some(
      (h) =>
        h.toLowerCase().includes('course') ||
        h.toLowerCase().includes('subject') ||
        h.toLowerCase().includes('code') ||
        h.toLowerCase().includes('room') ||
        h.toLowerCase().includes('venue')
    );
    layout = hasDetailCols ? 'list_rows' : 'matrix_days_rows';
  } else {
    layout = 'list_rows';
  }

  const sessions: NormalizedClassSession[] = [];
  const matrixGrid: Record<
    string,
    Record<string, NormalizedClassSession[]>
  > = {};
  const daysSet = new Set<string>();
  const timeSlotsSet = new Set<string>();

  if (layout === 'matrix_days_columns') {
    const timeColKey =
      headers.find((h) => normalizeDay(h) === null) || headers[0];

    rawRows.forEach((row, rIdx) => {
      const rawSlot = String(row[timeColKey] || `Period ${rIdx + 1}`).trim();
      const expandedPeriods = expandTimeSlots(rawSlot);
      expandedPeriods.forEach((timeSlot) => {
        timeSlotsSet.add(timeSlot);
      });

      dayHeaders.forEach((dayHeader) => {
        const normDay = normalizeDay(dayHeader);
        if (!normDay) return;
        daysSet.add(normDay.full);

        const rawText = String(row[dayHeader] || '').trim();
        const parsedSessions = parseCellContentMultiple(rawText);

        parsedSessions.forEach((parsedCell, blockIdx) => {
          expandedPeriods.forEach((timeSlot) => {
            const session: NormalizedClassSession = {
              id: `matrix-col-${normDay.full}-${timeSlot}-${rIdx}-${blockIdx}`,
              day: normDay.full,
              dayShort: normDay.short,
              dayIndex: normDay.index,
              timeSlot,
              ...parsedCell,
              rawText,
            };
            sessions.push(session);
            timeSlotsSet.add(timeSlot);
            if (!matrixGrid[normDay.full]) matrixGrid[normDay.full] = {};
            if (!matrixGrid[normDay.full][timeSlot])
              matrixGrid[normDay.full][timeSlot] = [];
            matrixGrid[normDay.full][timeSlot].push(session);
          });
        });
      });
    });
  } else if (layout === 'matrix_days_rows') {
    const dayKey = dayColKey || headers[0];
    const timeSlotHeaders = headers.filter((h) => h !== dayKey);

    rawRows.forEach((row, rIdx) => {
      const dayVal = String(row[dayKey] || '').trim();
      const normDay = normalizeDay(dayVal);
      if (!normDay) return;
      daysSet.add(normDay.full);

      timeSlotHeaders.forEach((tsHeader) => {
        const expandedPeriods = expandTimeSlots(tsHeader);
        const cellVal = String(row[tsHeader] || '').trim();
        const parsedSessions = parseCellContentMultiple(cellVal);

        parsedSessions.forEach((parsedCell, blockIdx) => {
          expandedPeriods.forEach((timeSlot) => {
            timeSlotsSet.add(timeSlot);
            const session: NormalizedClassSession = {
              id: `matrix-row-${normDay.full}-${timeSlot}-${rIdx}-${blockIdx}`,
              day: normDay.full,
              dayShort: normDay.short,
              dayIndex: normDay.index,
              timeSlot,
              ...parsedCell,
              rawText: cellVal,
            };
            sessions.push(session);
            if (!matrixGrid[normDay.full]) matrixGrid[normDay.full] = {};
            if (!matrixGrid[normDay.full][timeSlot])
              matrixGrid[normDay.full][timeSlot] = [];
            matrixGrid[normDay.full][timeSlot].push(session);
          });
        });
      });
    });
  } else {
    // List Timetable or fallback
    rawRows.forEach((row, rIdx) => {
      const dayKey =
        headers.find((h) => h.toLowerCase().includes('day')) || headers[0];
      const timeKey = headers.find(
        (h) =>
          h.toLowerCase().includes('time') ||
          h.toLowerCase().includes('period') ||
          h.toLowerCase().includes('slot')
      );
      const codeKey = headers.find(
        (h) =>
          h.toLowerCase().includes('code') || h.toLowerCase().includes('course')
      );
      const titleKey = headers.find(
        (h) =>
          h.toLowerCase().includes('title') ||
          h.toLowerCase().includes('name') ||
          h.toLowerCase().includes('subject')
      );
      const roomKey = headers.find(
        (h) =>
          h.toLowerCase().includes('room') ||
          h.toLowerCase().includes('venue') ||
          h.toLowerCase().includes('hall') ||
          h.toLowerCase().includes('lab')
      );
      const facultyKey = headers.find(
        (h) =>
          h.toLowerCase().includes('faculty') ||
          h.toLowerCase().includes('instructor') ||
          h.toLowerCase().includes('staff') ||
          h.toLowerCase().includes('teacher')
      );

      const rawDayVal = String(row[dayKey] || '').trim();
      const normDay = normalizeDay(rawDayVal) || {
        full: rawDayVal || 'General',
        short: rawDayVal ? rawDayVal.slice(0, 3) : 'Gen',
        index: -1,
      };
      daysSet.add(normDay.full);

      const timeSlot =
        (timeKey && String(row[timeKey]).trim()) || `Period ${rIdx + 1}`;
      timeSlotsSet.add(timeSlot);

      const rawValues = Object.values(row)
        .map((v) => String(v || '').trim())
        .filter(Boolean);

      const rawCodeVal = (codeKey && String(row[codeKey]).trim()) || '';
      const parsedCodeCell = rawCodeVal ? parseCellContent(rawCodeVal) : null;
      let courseCode = parsedCodeCell?.courseCode || rawCodeVal;
      let component = parsedCodeCell?.component || undefined;
      let courseTitle = (titleKey && String(row[titleKey]).trim()) || '';
      let room = (roomKey && String(row[roomKey]).trim()) || '';
      let faculty = (facultyKey && String(row[facultyKey]).trim()) || '';

      if (!courseCode || !courseTitle || !room) {
        for (const val of rawValues) {
          if (val === rawDayVal || val === timeSlot) continue;
          const parsed = parseCellContent(val);
          if (!courseCode && parsed.courseCode) courseCode = parsed.courseCode;
          if (!component && parsed.component) component = parsed.component;
          if (!courseTitle && parsed.courseTitle)
            courseTitle = parsed.courseTitle;
          if (!room && parsed.room) room = parsed.room;
          if (!faculty && parsed.faculty) faculty = parsed.faculty;
        }
      }

      if (!courseCode && rawValues.length > 1) {
        const parsedFallback = parseCellContent(rawValues[1]);
        courseCode = parsedFallback.courseCode || rawValues[1];
        if (!component) component = parsedFallback.component;
      }
      if (!courseTitle && rawValues.length > 2) courseTitle = rawValues[2];
      if (!room && rawValues.length > 0) room = rawValues[rawValues.length - 1];

      const session: NormalizedClassSession = {
        id: `list-session-${rIdx}`,
        day: normDay.full,
        dayShort: normDay.short,
        dayIndex: normDay.index,
        timeSlot,
        courseCode: courseCode || 'N/A',
        courseTitle: courseTitle || 'Class Session',
        component,
        room: room || 'N/A',
        faculty: faculty || '',
        rawText: rawValues.join(' | '),
      };

      sessions.push(session);
      if (!matrixGrid[normDay.full]) matrixGrid[normDay.full] = {};
      if (!matrixGrid[normDay.full][timeSlot])
        matrixGrid[normDay.full][timeSlot] = [];
      matrixGrid[normDay.full][timeSlot].push(session);
    });
  }

  const sortedDays = Array.from(daysSet).sort((a, b) => {
    const normA = normalizeDay(a);
    const normB = normalizeDay(b);
    const idxA = normA ? normA.index : 99;
    const idxB = normB ? normB.index : 99;
    return idxA - idxB;
  });

  const timeSlotsPresent = Array.from(timeSlotsSet);
  const standardDays = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];
  const allDaysToInit = Array.from(new Set([...standardDays, ...sortedDays]));

  allDaysToInit.forEach((day) => {
    if (!matrixGrid[day]) matrixGrid[day] = {};
    timeSlotsPresent.forEach((slot) => {
      if (!matrixGrid[day][slot]) {
        matrixGrid[day][slot] = [];
      }
    });
  });

  return {
    layout,
    headers,
    rawRows,
    sessions,
    daysPresent: sortedDays,
    timeSlotsPresent,
    matrixGrid,
  };
}
