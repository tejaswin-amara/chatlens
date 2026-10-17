import { z } from 'zod';

export const profileDataSchema = z
  .object({
    name: z.string().optional(),
    universityId: z.string().optional(),
    photoUrl: z.string().optional(),
    extendedProfile: z.string().optional(),
    success: z.boolean().optional(),
  })
  .passthrough();

export const profileResponseSchema = z.object({
  success: z.boolean(),
  data: profileDataSchema.optional(),
  error: z.string().optional(),
});

export type ProfileData = z.infer<typeof profileDataSchema>;
export type ProfileResponse = z.infer<typeof profileResponseSchema>;
