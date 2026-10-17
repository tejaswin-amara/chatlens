import { z } from 'zod';
import type { NormalizedClassSession } from '@/lib/timetable-parser';

// ============================================================================
// Agent Tool Definition Interface
// ============================================================================

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
}

// ============================================================================
// 1. getAttendance Tool Schemas & Types
// ============================================================================

export const getAttendanceArgsSchema = z.object({
  subject: z.string().optional(),
});
export type GetAttendanceArgs = z.infer<typeof getAttendanceArgsSchema>;

export interface AttendanceSubject {
  'Course Code': string;
  'Course Title': string;
  'Conducted Hours': string;
  'Attended Hours': string;
  'Attendance Percentage': string;
  'Academic Year'?: string;
  Semester?: string;
  Component?: string;
  'Course Type'?: string;
}

export interface GetAttendanceResult {
  success: boolean;
  attendance: AttendanceSubject[];
  summary?: {
    totalSubjects: number;
    overallPercentage: number;
    atRiskCount: number;
  };
  error?: string;
}

// ============================================================================
// 2. getTimetable Tool Schemas & Types
// ============================================================================

export const getTimetableArgsSchema = z.object({
  day: z.string().optional(),
});
export type GetTimetableArgs = z.infer<typeof getTimetableArgsSchema>;

export interface GetTimetableResult {
  success: boolean;
  schedule: NormalizedClassSession[];
  daysPresent?: string[];
  error?: string;
}

// ============================================================================
// 3. getMarks Tool Schemas & Types
// ============================================================================

export const getMarksArgsSchema = z.object({
  semester: z.string().optional(),
});
export type GetMarksArgs = z.infer<typeof getMarksArgsSchema>;

export interface MarksSubject {
  'Course Code': string;
  'Course Name': string;
  'Faculty Name'?: string;
  'Internal 1'?: string;
  'Internal 2'?: string;
  Assignment?: string;
  'Total Marks'?: string;
}

export interface GetMarksResult {
  success: boolean;
  marks: MarksSubject[];
  error?: string;
}

// ============================================================================
// 4. getFeeDetails Tool Schemas & Types
// ============================================================================

export const getFeeDetailsArgsSchema = z.object({});
export type GetFeeDetailsArgs = z.infer<typeof getFeeDetailsArgsSchema>;

export interface FeeItem {
  'Fee Type': string;
  Amount: string;
  'Paid Amount': string;
  'Balance Amount': string;
  Status: string;
}

export interface FeeDetailsBreakdown {
  items: FeeItem[];
  totalAmount: number;
  totalPaid: number;
  totalPending: number;
  hasPendingDue: boolean;
}

export interface GetFeeDetailsResult {
  success: boolean;
  breakdown: FeeDetailsBreakdown;
  error?: string;
}

// ============================================================================
// 5. getStudentProfile Tool Schemas & Types
// ============================================================================

export const getStudentProfileArgsSchema = z.object({});
export type GetStudentProfileArgs = z.infer<typeof getStudentProfileArgsSchema>;

export interface StudentProfileInfo {
  name: string;
  universityId: string;
  photoUrl?: string;
  program?: string;
  department?: string;
  academicYear?: string;
  semester?: string;
  extendedProfile?: Record<string, unknown>;
}

export interface GetStudentProfileResult {
  success: boolean;
  profile: StudentProfileInfo;
  error?: string;
}

// ============================================================================
// 6. calculateAttendanceTarget Tool Schemas & Types
// ============================================================================

export const calculateAttendanceTargetArgsSchema = z.object({
  currentAttended: z.number().min(0),
  currentTotal: z.number().min(1),
  targetPercent: z.number().min(1).max(100).optional().default(75),
});
export type CalculateAttendanceTargetArgs = z.infer<
  typeof calculateAttendanceTargetArgsSchema
>;

export interface CalculateAttendanceTargetResult {
  success: boolean;
  currentAttended: number;
  currentTotal: number;
  currentPercentage: number;
  targetPercent: number;
  classesNeeded: number;
  maxBunkable: number;
  status: 'below_target' | 'target_met';
  message: string;
  error?: string;
}

// ============================================================================
// 7. predictCGPA Tool Schemas & Types
// ============================================================================

export const newCourseItemSchema = z.object({
  credits: z.number().positive(),
  expectedGrade: z.string(),
});

export const predictCGPAArgsSchema = z.object({
  currentCGPA: z.number().min(0).max(10),
  completedCredits: z.number().min(0),
  newCourses: z.array(newCourseItemSchema).min(1),
});
export type PredictCGPAArgs = z.infer<typeof predictCGPAArgsSchema>;

export interface PredictCGPAResult {
  success: boolean;
  currentCGPA: number;
  completedCredits: number;
  newCredits: number;
  totalCredits: number;
  predictedCGPA: number;
  gpaDelta: number;
  error?: string;
}

// ============================================================================
// Global Tools Registry Export
// ============================================================================

export const TOOLS_REGISTRY: ToolDefinition[] = [
  {
    name: 'getAttendance',
    description:
      'Fetch attendance records for the student. Optionally filter by course code or subject title.',
    parameters: {
      type: 'object',
      properties: {
        subject: {
          type: 'string',
          description:
            "Optional course code or subject title to filter attendance (e.g. '23CS2101R' or 'Data Structures').",
        },
      },
    },
  },
  {
    name: 'getTimetable',
    description:
      "Fetch class timetable and schedule. Optionally filter by day of the week (e.g., 'Monday', 'Mon', 'Today', 'Tomorrow').",
    parameters: {
      type: 'object',
      properties: {
        day: {
          type: 'string',
          description:
            "Optional day name or order (e.g. 'Monday', 'Tue', 'Today', 'Tomorrow', 'Day 1').",
        },
      },
    },
  },
  {
    name: 'getMarks',
    description:
      'Fetch internal examination and assignment marks for student courses, optionally filtered by semester.',
    parameters: {
      type: 'object',
      properties: {
        semester: {
          type: 'string',
          description:
            "Optional semester ID or name to filter marks (e.g. '1', '2').",
        },
      },
    },
  },
  {
    name: 'getFeeDetails',
    description:
      'Fetch fee payment details, fee heads, total fee, paid amount, and pending balance.',
    parameters: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'getStudentProfile',
    description:
      'Fetch student profile details including name, university ID, program, department, and photo URL.',
    parameters: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'calculateAttendanceTarget',
    description:
      'Calculate number of additional classes needed to reach a target attendance percentage (e.g. 75% or 85%) or how many classes can be safely skipped.',
    parameters: {
      type: 'object',
      properties: {
        currentAttended: {
          type: 'number',
          description: 'Number of classes currently attended by the student.',
        },
        currentTotal: {
          type: 'number',
          description: 'Total number of classes conducted so far.',
        },
        targetPercent: {
          type: 'number',
          description: 'Desired target attendance percentage (defaults to 75).',
        },
      },
      required: ['currentAttended', 'currentTotal'],
    },
  },
  {
    name: 'predictCGPA',
    description:
      'Predict future cumulative GPA (CGPA) based on current CGPA, total completed credits, and expected grades in upcoming or new courses.',
    parameters: {
      type: 'object',
      properties: {
        currentCGPA: {
          type: 'number',
          description: "Student's current cumulative GPA (0.0 to 10.0).",
        },
        completedCredits: {
          type: 'number',
          description: 'Total credits completed so far.',
        },
        newCourses: {
          type: 'array',
          description:
            "Array of new courses with credit weight and anticipated letter grade (e.g. 'O', 'S', 'A+', 'A', 'B+', 'B').",
          items: {
            type: 'object',
            properties: {
              credits: {
                type: 'number',
                description: 'Credits for this course (e.g. 3 or 4).',
              },
              expectedGrade: {
                type: 'string',
                description:
                  "Expected letter grade (e.g. 'O', 'S', 'A+', 'A', 'B+', 'B', 'C', 'D', 'F').",
              },
            },
            required: ['credits', 'expectedGrade'],
          },
        },
      },
      required: ['currentCGPA', 'completedCredits', 'newCourses'],
    },
  },
];
