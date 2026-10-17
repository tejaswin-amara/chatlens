/**
 * Course Code to Subject Name Resolver and Dynamic Multi-Source Registry
 * Ensures 100% accurate subject names across Attendance, Marks, Timetable, Profile, & AI.
 */

// Global runtime in-memory registry
const COURSE_TITLE_REGISTRY: Record<string, string> = {};

// Safe browser hydration
function hydrateFromStorage(): void {
  if (typeof window === 'undefined') return;
  try {
    const raw =
      sessionStorage.getItem('kl_course_registry') ||
      localStorage.getItem('kl_course_registry');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        Object.assign(COURSE_TITLE_REGISTRY, parsed);
      }
    }
  } catch {}
}

// Initial hydration attempt
hydrateFromStorage();

function persistToStorage(): void {
  if (typeof window === 'undefined') return;
  try {
    const serialized = JSON.stringify(COURSE_TITLE_REGISTRY);
    sessionStorage.setItem('kl_course_registry', serialized);
    localStorage.setItem('kl_course_registry', serialized);
  } catch {}
}

/**
 * Curated dictionary of official KL University course codes & names.
 */
export const KNOWN_COURSE_MAP: Record<string, string> = {
  // Core Department & Universal Course Codes
  CS1302: 'Data Structures & Algorithms',
  CS2101: 'Data Structures & Algorithms',
  CS1101: 'Object Oriented Programming with Java',
  CS1102: 'Object Oriented Programming',
  CS2102: 'Computer Organization & Architecture',
  CS2103: 'Database Management Systems',
  CS2205: 'Database Management Systems',
  CS2104: 'Operating Systems',
  CS3108: 'Software Engineering & Agile',
  CS3109: 'Computer Networks',
  CS3110: 'Design & Analysis of Algorithms',
  CS3211: 'Cloud Computing & DevOps',
  CS3212: 'Artificial Intelligence & Machine Learning',
  EC1201: 'Basic Electrical & Electronics Engineering',
  EC2206: 'Signal Processing & Communication Systems',
  EC2102: 'Digital Logic Design & Microprocessors',
  SC2107: 'Discrete Mathematics & Graph Theory',
  SC1101: 'Linear Algebra & Calculus',
  SC1102: 'Probability & Statistics for Engineers',
  FL2112: 'Foreign Language - Elective',
  EN1001: 'English for Professional Communication',
  HS1002: 'Universal Human Values & Professional Ethics',

  // 25 Series (Y25 Curriculum)
  '25CS1302E': 'Data Structures & Algorithms',
  '25CS1101E': 'Object Oriented Programming with Java',
  '25CS2103E': 'Database Management Systems',
  '25CS2104E': 'Operating Systems',
  '25CS2205E': 'Database Management Systems',
  '25CS3108E': 'Software Engineering & Agile',
  '25EC2206E': 'Signal Processing & Communication Systems',
  '25EC1201E': 'Basic Electrical & Electronics',
  '25SC2107E': 'Discrete Mathematics & Graph Theory',
  '25FL2112E': 'Foreign Language - Elective',

  // 24 Series (Y24 Curriculum)
  '24CS1302E': 'Data Structures & Algorithms',
  '24CS1101E': 'Object Oriented Programming with Java',
  '24CS2103E': 'Database Management Systems',
  '24CS2104E': 'Operating Systems',
  '24EC2206E': 'Signal Processing & Communication Systems',
  '24SC2107E': 'Discrete Mathematics & Graph Theory',
  '24FL2112E': 'Foreign Language - Elective',

  // 23 Series (Y23 Curriculum)
  '23CS2101R': 'Data Structures & Algorithms',
  '23CS2102R': 'Computer Organization & Architecture',
  '23CS2103R': 'Database Management Systems',
  '23CS2104R': 'Operating Systems',
  '23EC2206R': 'Signal Processing & Communication Systems',
  '23SC2107R': 'Discrete Mathematics & Graph Theory',

  // 22 Series (Y22 Curriculum)
  '22CS1101': 'Data Structures & Algorithms',
  '22CS1102': 'Object Oriented Programming',
  '22EC1201': 'Basic Electrical & Electronics',
  '22SC1101': 'Linear Algebra & Calculus',
};

/**
 * Validates whether a candidate string is a genuine Subject Title,
 * strictly rejecting faculty names, room numbers, periods, sections, and placeholders.
 */
export function isValidSubjectTitle(title: string, code?: string): boolean {
  if (!title) return false;
  const str = title.trim();
  if (str.length < 3) return false;

  const upper = str.toUpperCase();
  const cleanCode = (code || '').trim().toUpperCase();

  // Rejects exact or partial course code match
  if (
    cleanCode &&
    (upper === cleanCode || upper === cleanCode.replace(/[-_][LTPSS]$/, ''))
  ) {
    return false;
  }

  // Reject pure course code format (e.g. "25CS1302E", "CS2103")
  if (/^(?:[0-9]{2})?[A-Z]{2,5}[0-9]{3,4}[A-Z]?(?:[-_][LTPSS])?$/.test(upper)) {
    return false;
  }

  // Reject Faculty prefixes and personal honorifics
  if (
    /^(?:DR\.|PROF\.|MR\.|MRS\.|MS\.|FACULTY[-:\s]|INSTRUCTOR[-:\s]|STAFF[-:\s]|TEACHER[-:\s])/i.test(
      str
    )
  ) {
    return false;
  }

  // Reject Room / Venue / Block markers
  if (
    /^(?:ROOMNO|ROOM|HALL|LAB|VENUE|BLOCK|FLOOR|FED-LAB|NEW CSE|MECHANICAL LAB)[-:\s]/i.test(
      upper
    ) ||
    /^(?:ROOMNO[-:\s]*\d+|[A-Z]-\d{2,4}|[A-Z]{1,4}[-_\s]?\d{3,4})$/i.test(upper)
  ) {
    return false;
  }

  // Reject Timetable period / slot / day markers
  if (
    /^(?:PERIOD\s*\d+|SLOT\s*\d+|DAY\s*ORDER|TIME\s*SLOT|MON(?:DAY)?|TUE(?:SDAY)?|WED(?:NESDAY)?|THU(?:RSDAY)?|FRI(?:DAY)?|SAT(?:URDAY)?|SUN(?:DAY)?)$/i.test(
      upper
    )
  ) {
    return false;
  }

  // Reject Section & Component markers only
  if (
    /^(?:SECTION|SEC)(?:\s*[-:\s]*\d+)?$/i.test(upper) ||
    /^[SLP]-\d+$/i.test(upper) ||
    /^(?:LECTURE|PRACTICAL|SKILL|TUTORIAL)$/i.test(upper)
  ) {
    return false;
  }

  // Reject Status / Placeholder words
  if (
    /^(?:FREE|N\/A|NIL|NONE|NO CLASS|LUNCH|BREAK|COUNSELING|LIBRARY|SELF STUDY|SPORTS|GUEST LECTURE|HOLIDAY)$/i.test(
      upper
    )
  ) {
    return false;
  }

  // Must contain actual alphabetical letters and meaningful words
  if (!/[a-zA-Z]{3,}/.test(str)) {
    return false;
  }

  return true;
}

/**
 * Extracts core department code (e.g. "CS1302" from "25CS1302E-L" or "23CS2101R")
 */
export function extractCoreCode(code: string): string {
  if (!code) return '';
  const clean = code.trim().toUpperCase();
  const base = clean.replace(/[-_]([LTPSS]|LAB|PRAC|THEORY|\d+)$/i, '');
  const coreMatch = base.match(/(?:[0-9]{2})?([A-Z]{2,5}[0-9]{3,4})[A-Z]?/i);
  return coreMatch ? coreMatch[1].toUpperCase() : base;
}

/**
 * Strips embedded course code prefixes/suffixes from raw title strings
 */
export function cleanTitleString(title: string, code?: string): string {
  let str = (title || '').trim();
  if (!str) return '';

  if (code) {
    const cleanCode = code.trim();
    if (cleanCode) {
      const escaped = cleanCode.replace(/[\\^$*+?.()|[\]{}]/g, '\\$&');
      str = str.replace(new RegExp(`^${escaped}\\s*[-:_\\/\\s]*`, 'i'), '');
      str = str.replace(new RegExp(`\\s*[-:_\\/\\s]*${escaped}$`, 'i'), '');
    }
  }

  // Strip leading code patterns e.g. "25CS1302E - ", "CS1302: ", "23CS2101R / "
  str = str.replace(
    /^(?:[0-9]{2})?[A-Z]{2,5}[0-9]{3,4}[A-Z]?(?:[-_][LTPSS])?\s*[-:_\\/]\s*/i,
    ''
  );

  return str.trim();
}

/**
 * Registers course code -> title pairs dynamically from ERP datasets (Attendance, Marks, Profile, Timetable)
 */
export function registerCourseTitles(data: unknown): void {
  if (!data) return;

  hydrateFromStorage();
  let updated = false;

  const items = Array.isArray(data) ? data : [data];

  items.forEach((item) => {
    if (!item || typeof item !== 'object') return;

    const row = item as Record<string, unknown>;
    let code = '';
    let title = '';

    for (const [k, v] of Object.entries(row)) {
      const key = k.toLowerCase().replace(/[^a-z0-9]/g, '');
      const val = String(v ?? '').trim();
      if (!val) continue;

      if (key === 'coursecode' || key === 'subjectcode' || key === 'code') {
        if (!code) code = val.toUpperCase();
      } else if (
        key === 'coursetitle' ||
        key === 'subjecttitle' ||
        key === 'coursename' ||
        key === 'subjectname' ||
        key === 'title' ||
        key === 'subject'
      ) {
        if (!title) title = val;
      }
    }

    if (code && title) {
      const cleanedTitle = cleanTitleString(title, code);
      if (isValidSubjectTitle(cleanedTitle, code)) {
        const baseCode = code.replace(
          /[-_]([LTPSS]|LAB|PRAC|THEORY|\d+)$/i,
          ''
        );
        const coreCode = extractCoreCode(code);

        COURSE_TITLE_REGISTRY[code] = cleanedTitle;
        if (baseCode) COURSE_TITLE_REGISTRY[baseCode] = cleanedTitle;
        if (coreCode && !COURSE_TITLE_REGISTRY[coreCode])
          COURSE_TITLE_REGISTRY[coreCode] = cleanedTitle;
        updated = true;
      }
    }
  });

  if (updated) {
    persistToStorage();
  }
}

/**
 * Resolves a course code (e.g. "25CS1302E") or raw string to an authoritative, friendly Subject Name.
 * Priority:
 * 1. Dynamic COURSE_TITLE_REGISTRY (from attendance/marks/profile/timetable) exact full code
 * 2. Dynamic COURSE_TITLE_REGISTRY base code (e.g. "25CS1302E" for "25CS1302E-L")
 * 3. Explicit provided title if valid and genuine
 * 4. KNOWN_COURSE_MAP static dictionary exact full code
 * 5. KNOWN_COURSE_MAP static dictionary base code
 * 6. Dynamic COURSE_TITLE_REGISTRY core department code
 * 7. KNOWN_COURSE_MAP core department code
 * 8. Cleaned explicit title fallback
 * 9. Formatted clean code fallback
 */
export function getSubjectTitle(code: string, title?: string): string {
  hydrateFromStorage();

  const cleanCode = (code || '').trim().toUpperCase();
  const rawTitle = (title || '').trim();
  const cleanedTitle = cleanTitleString(rawTitle, cleanCode);
  const isTitleValid = isValidSubjectTitle(cleanedTitle, cleanCode);

  const baseCode = cleanCode.replace(/[-_]([LTPSS]|LAB|PRAC|THEORY|\d+)$/i, '');
  const coreCode = extractCoreCode(cleanCode);

  // 1. Dynamic registry from live ERP data (full code or base code) - highest authority
  if (cleanCode && COURSE_TITLE_REGISTRY[cleanCode])
    return COURSE_TITLE_REGISTRY[cleanCode];
  if (baseCode && COURSE_TITLE_REGISTRY[baseCode])
    return COURSE_TITLE_REGISTRY[baseCode];

  // 2. Explicit title if verified as genuine subject name
  if (isTitleValid) {
    return cleanedTitle;
  }

  // 3. Known static dictionary exact full or base code
  if (cleanCode && KNOWN_COURSE_MAP[cleanCode])
    return KNOWN_COURSE_MAP[cleanCode];
  if (baseCode && KNOWN_COURSE_MAP[baseCode]) return KNOWN_COURSE_MAP[baseCode];

  // 4. Dynamic registry core code
  if (coreCode && COURSE_TITLE_REGISTRY[coreCode])
    return COURSE_TITLE_REGISTRY[coreCode];

  // 5. Static map core code
  if (coreCode && KNOWN_COURSE_MAP[coreCode]) return KNOWN_COURSE_MAP[coreCode];

  // 6. Valid cleaned title fallback
  if (isTitleValid) {
    return cleanedTitle;
  }

  // 7. Final fallback to clean Code or default label
  return cleanCode || 'Subject Course';
}

/**
 * Gets formatted subject code (e.g. "25CS1302E")
 */
export function getSubjectCode(code: string, rawText?: string): string {
  if (code && code.trim()) {
    return code.trim().toUpperCase();
  }
  if (rawText) {
    const match = rawText.match(
      /([0-9]{2}[A-Z]{2,5}[0-9]{3,4}[A-Z]?|[A-Z]{2,5}[0-9]{3,4}[A-Z]?)/i
    );
    if (match) return match[1].toUpperCase();
  }
  return '';
}
