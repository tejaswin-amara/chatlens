import { z } from 'zod';

export const marksSubjectSchema = z
  .object({
    'Course Code': z.string().optional(),
    'Course Name': z.string().optional(),
    'Faculty Name': z.string().optional(),
    'Internal 1': z.string().optional(),
    'Internal 2': z.string().optional(),
    Assignment: z.string().optional(),
    'Total Marks': z.string().optional(),
  })
  .passthrough();

export const marksResponseSchema = z.object({
  success: z.boolean(),
  data: z.array(marksSubjectSchema).optional(),
  error: z.string().optional(),
});

export type MarksSubject = z.infer<typeof marksSubjectSchema>;
export type MarksResponse = z.infer<typeof marksResponseSchema>;
