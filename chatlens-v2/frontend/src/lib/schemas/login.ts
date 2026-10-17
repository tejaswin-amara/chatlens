import { z } from 'zod';

export const semesterOptionSchema = z.object({
  value: z.string(),
  label: z.string(),
});

export const loginRequestSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
  captcha: z.string().min(1, 'Captcha is required'),
  session: z.object({
    cookies: z.array(z.object({ name: z.string(), value: z.string() })),
    csrfToken: z.string(),
    userAgent: z.string().optional(),
  }),
  deviceId: z.string().optional(),
});

export const loginResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  session: z
    .object({
      cookies: z.array(z.object({ name: z.string(), value: z.string() })),
      csrfToken: z.string(),
      userAgent: z.string().optional(),
    })
    .optional(),
  csrfToken: z.string().optional(),
  academicYears: z.array(semesterOptionSchema).optional(),
  semesters: z.array(semesterOptionSchema).optional(),
  deviceId: z.string().optional(),
  needsCaptchaRetry: z.boolean().optional(),
  error: z.string().optional(),
});

export type LoginRequest = z.infer<typeof loginRequestSchema>;
export type LoginResponse = z.infer<typeof loginResponseSchema>;
