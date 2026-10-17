export interface CGPAResult {
  cgpa: number;
  credits: number;
  isOfficial: boolean;
  sgpa?: number | null;
}

/**
 * Maps letter grades or string grade inputs to numerical grade points on a 10-point scale.
 * S / O -> 10
 * A+ -> 9
 * A -> 8
 * B+ -> 7
 * B -> 6
 * C -> 5
 * D -> 4
 * F / FAIL / AB / ABSENT / DT -> 0
 * P / PASS / SATISFACTORY / NC -> null (excluded from GPA calculation)
 */
export function mapGradeToPoints(gradeStr: string): number | null {
  if (gradeStr === null || gradeStr === undefined) return null;
  const g = String(gradeStr).trim().toUpperCase();
  if (!g) return null;

  switch (g) {
    case 'O':
    case 'S':
    case '10':
    case '10.0':
    case '10.00':
      return 10;
    case 'A+':
    case '9':
    case '9.0':
    case '9.00':
      return 9;
    case 'A':
    case '8':
    case '8.0':
    case '8.00':
      return 8;
    case 'B+':
    case '7':
    case '7.0':
    case '7.00':
      return 7;
    case 'B':
    case '6':
    case '6.0':
    case '6.00':
      return 6;
    case 'C':
    case '5':
    case '5.0':
    case '5.00':
      return 5;
    case 'D':
    case '4':
    case '4.0':
    case '4.00':
      return 4;
    case 'F':
    case 'FAIL':
    case 'AB':
    case 'ABSENT':
    case 'DT':
    case '0':
    case '0.0':
    case '0.00':
      return 0;
    case 'P':
    case 'PASS':
    case 'SATISFACTORY':
    case 'NC':
    case 'NON-CREDIT':
    case 'AUDIT':
    case 'W':
    case 'WITHDRAWN':
      return null;
    default: {
      const num = parseFloat(g);
      return !isNaN(num) && isFinite(num) && num >= 0 && num <= 10 ? num : null;
    }
  }
}

/**
 * Safely parses numbers from string representations (e.g. " 3.0 Cr ", "10.00 / 10").
 */
function parseNumericValue(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return isNaN(val) || !isFinite(val) ? null : val;
  if (typeof val === 'boolean') return null;
  const str = String(val).trim();
  if (!str) return null;
  const match = str.match(/[-+]?\d*\.?\d+/);
  if (!match) return null;
  const parsed = parseFloat(match[0]);
  return !isNaN(parsed) && isFinite(parsed) ? parsed : null;
}

/**
 * Helper to extract official summary values from a key-value object.
 */
function extractOfficialSummary(
  dataObj: Record<string, unknown> | null | undefined
): {
  cgpa: number | null;
  sgpa: number | null;
  credits: number | null;
} {
  if (!dataObj || typeof dataObj !== 'object') {
    return { cgpa: null, sgpa: null, credits: null };
  }
  let cgpa: number | null = null;
  let sgpa: number | null = null;
  let credits: number | null = null;

  const keys = Object.keys(dataObj);

  const cgpaKey = keys.find((k) => {
    const lk = k.toLowerCase().replace(/[^a-z0-9]/g, '');
    return (
      lk.includes('cgpa') ||
      lk === 'gpa' ||
      lk.includes('cumulativegpa') ||
      lk.includes('overallgpa') ||
      lk.includes('totalcgpa') ||
      lk.includes('academicgpa') ||
      lk.includes('cumulative')
    );
  });
  if (cgpaKey && dataObj[cgpaKey] !== undefined && dataObj[cgpaKey] !== null) {
    const val = parseNumericValue(dataObj[cgpaKey]);
    if (val !== null && val > 0 && val <= 10) {
      cgpa = val;
    }
  }

  const sgpaKey = keys.find((k) => {
    const lk = k.toLowerCase().replace(/[^a-z0-9]/g, '');
    return (
      lk.includes('sgpa') ||
      lk.includes('semgpa') ||
      lk.includes('semestergpa') ||
      lk.includes('termgpa')
    );
  });
  if (sgpaKey && dataObj[sgpaKey] !== undefined && dataObj[sgpaKey] !== null) {
    const val = parseNumericValue(dataObj[sgpaKey]);
    if (val !== null && val > 0 && val <= 10) {
      sgpa = val;
    }
  }

  const credKey = keys.find((k) => {
    const lk = k.toLowerCase();
    return (
      lk.includes('total credit') ||
      lk.includes('earned credit') ||
      lk.includes('credits earned') ||
      lk.includes('completed credit') ||
      lk === 'total_credits'
    );
  });
  if (credKey && dataObj[credKey] !== undefined && dataObj[credKey] !== null) {
    const val = parseNumericValue(dataObj[credKey]);
    if (val !== null && val > 0) {
      credits = val;
    }
  }

  return { cgpa, sgpa, credits };
}

/**
 * Process raw ERP rows and optional profile data to extract or calculate CGPA & Credits.
 * Phase 1: Checks for direct official CGPA/SGPA summary values.
 * Phase 2: Dynamic fallback computes weighted GPA, supporting letter grades & preserving failed course credits.
 */
export function processERPDataForCGPA(
  rawRows: Record<string, unknown>[],
  profileData?: Record<string, unknown>
): CGPAResult {
  const hasRows = Array.isArray(rawRows) && rawRows.length > 0;

  // --- Phase 1: Direct Official Summary Lookup ---
  let officialCgpa: number | null = null;
  let officialSgpa: number | null = null;
  let officialCredits: number | null = null;

  if (hasRows) {
    for (const row of rawRows) {
      if (!row || typeof row !== 'object') continue;

      const summary = extractOfficialSummary(row);
      if (officialCgpa === null && summary.cgpa !== null) {
        officialCgpa = summary.cgpa;
      }
      if (officialSgpa === null && summary.sgpa !== null) {
        officialSgpa = summary.sgpa;
      }
      if (officialCredits === null && summary.credits !== null) {
        officialCredits = summary.credits;
      }
    }
  }

  if (officialCgpa === null && profileData) {
    const profileSummary = extractOfficialSummary(profileData);
    if (profileSummary.cgpa !== null) {
      officialCgpa = profileSummary.cgpa;
    }
    if (officialSgpa === null && profileSummary.sgpa !== null) {
      officialSgpa = profileSummary.sgpa;
    }
    if (officialCredits === null && profileSummary.credits !== null) {
      officialCredits = profileSummary.credits;
    }
  }

  // --- Phase 2: Dynamic Fallback Calculation ---
  let totalPoints = 0;
  let totalCredits = 0;

  if (hasRows) {
    for (const row of rawRows) {
      if (!row || typeof row !== 'object') continue;
      const keys = Object.keys(row);

      // 1. Flexible Column Identification
      const gradeKey =
        keys.find((k) => {
          const lk = k.toLowerCase().trim();
          const cleaned = lk.replace(/[^a-z0-9]/g, '');
          return (
            (lk.includes('grade') &&
              !lk.includes('point') &&
              !lk.includes('gp')) ||
            cleaned === 'grd' ||
            lk.includes('letter')
          );
        }) || keys.find((k) => k.toLowerCase().includes('grade'));

      const credKey = keys.find((k) => {
        const lk = k.toLowerCase().trim();
        const cleaned = lk.replace(/[^a-z0-9]/g, '');
        return (
          lk.includes('credit') ||
          lk.includes('cred') ||
          cleaned === 'cr' ||
          cleaned === 'creds'
        );
      });

      const pointKey = keys.find((k) => {
        const lk = k.toLowerCase().trim();
        const cleaned = lk.replace(/[^a-z0-9]/g, '');
        return (
          lk.includes('point') ||
          lk.includes('gp') ||
          cleaned === 'pts' ||
          cleaned === 'gradepoint'
        );
      });

      // 2. Value Extraction
      const credits = credKey ? parseNumericValue(row[credKey]) || 0 : 0;
      if (credits <= 0) continue; // Exclude 0-credit non-academic courses

      const gradeStr = gradeKey ? String(row[gradeKey] || '') : '';
      let gradePoint: number | null = pointKey
        ? parseNumericValue(row[pointKey])
        : null;

      // Fallback to letter grade mapping if grade points column is absent or invalid
      if (gradePoint === null || isNaN(gradePoint)) {
        gradePoint = mapGradeToPoints(gradeStr);
      }

      if (gradePoint !== null) {
        totalCredits += credits;
        totalPoints += gradePoint * credits;
      }
    }
  }

  // If Phase 1 detected official CGPA, return official result immediately
  if (officialCgpa !== null) {
    return {
      cgpa: Number(officialCgpa.toFixed(2)),
      credits: officialCredits !== null ? officialCredits : totalCredits,
      isOfficial: true,
      sgpa: officialSgpa,
    };
  }

  if (!hasRows) {
    return { cgpa: 0, credits: 0, isOfficial: false, sgpa: null };
  }

  const finalCredits =
    officialCredits !== null ? officialCredits : totalCredits;
  const calculatedCgpa =
    totalCredits > 0 ? Number((totalPoints / totalCredits).toFixed(2)) : 0;

  return {
    cgpa: calculatedCgpa,
    credits: finalCredits,
    isOfficial: false,
    sgpa: officialSgpa,
  };
}
