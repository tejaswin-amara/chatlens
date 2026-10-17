import { z } from 'zod';

export const attendanceSubjectSchema = z
  .object({
    'Course Code': z.string().optional(),
    'Course Title': z.string().optional(),
    'Conducted Hours': z.string().or(z.number()).optional(),
    'Attended Hours': z.string().or(z.number()).optional(),
    'Attendance Percentage': z.string().optional(),
    'Academic Year': z.string().optional(),
    Semester: z.string().optional(),
  })
  .passthrough();

export const attendanceResponseSchema = z.object({
  success: z.boolean(),
  attendanceData: z.array(attendanceSubjectSchema).optional(),
  data: z.array(attendanceSubjectSchema).optional(),
  error: z.string().optional(),
});

export type AttendanceSubject = z.infer<typeof attendanceSubjectSchema>;
export type AttendanceResponse = z.infer<typeof attendanceResponseSchema>;
