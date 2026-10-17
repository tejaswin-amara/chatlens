import { z } from 'zod';

export const rawTimetableRowSchema = z.record(z.string(), z.unknown());

export const timetableSlotSchema = z.object({
  day: z.string(),
  timeSlot: z.string(),
  courseCode: z.string(),
  courseTitle: z.string().optional(),
  room: z.string().optional(),
  faculty: z.string().optional(),
  component: z.string().optional(),
  section: z.string().optional(),
});

export const timetableResponseSchema = z.object({
  success: z.boolean(),
  data: z.array(rawTimetableRowSchema).optional(),
  error: z.string().optional(),
});

export type TimetableSlot = z.infer<typeof timetableSlotSchema>;
export type TimetableResponse = z.infer<typeof timetableResponseSchema>;
