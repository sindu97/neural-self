/**
 * Runtime configuration, validated once at startup so a missing or malformed
 * variable fails loudly instead of silently calling the wrong URL.
 */
import { z } from 'zod'

const envSchema = z.object({
  // Same-origin path by default: Vite proxies /api to the backend in
  // development, and a reverse proxy does the same in production.
  VITE_API_BASE_URL: z.string().min(1).default('/api/v1'),
  VITE_APP_NAME: z.string().min(1).default('NeuralShelf'),
})

const parsed = envSchema.safeParse(import.meta.env)

if (!parsed.success) {
  throw new Error(`Invalid environment configuration: ${parsed.error.message}`)
}

export const env = {
  apiBaseUrl: parsed.data.VITE_API_BASE_URL.replace(/\/$/, ''),
  appName: parsed.data.VITE_APP_NAME,
} as const
