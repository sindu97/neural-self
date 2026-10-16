import { z } from 'zod'

// Mirrors the backend rules (SignupRequest / LoginRequest), so users see
// problems before submitting. The backend still validates everything.
const email = z.email('Enter a valid email address.').transform((value) => value.trim().toLowerCase())

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Enter your password.').max(128),
})

export const signupSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(2, 'Name must be at least 2 characters.')
      .max(100, 'Name must be at most 100 characters.'),
    email,
    password: z.string().min(8, 'Use at least 8 characters.').max(128, 'Use at most 128 characters.'),
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Passwords do not match.',
  })

export type LoginValues = z.infer<typeof loginSchema>
export type SignupValues = z.infer<typeof signupSchema>
