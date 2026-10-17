import { z } from 'zod';

export const feeItemSchema = z
  .object({
    'Fee Type': z.string().optional(),
    Amount: z.string().or(z.number()).optional(),
    'Paid Amount': z.string().or(z.number()).optional(),
    'Balance Amount': z.string().or(z.number()).optional(),
    Status: z.string().optional(),
  })
  .passthrough();

export const feeResponseSchema = z.object({
  success: z.boolean(),
  data: z.array(feeItemSchema).optional(),
  error: z.string().optional(),
});

export type FeeItem = z.infer<typeof feeItemSchema>;
export type FeeResponse = z.infer<typeof feeResponseSchema>;
