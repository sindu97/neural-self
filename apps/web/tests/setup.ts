import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { setAccessToken } from '@/lib/api/session'

import { server } from './msw/server'

// jsdom lacks ResizeObserver, which Radix UI (tooltips, menus) uses.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  cleanup()
  setAccessToken(null)
})
afterAll(() => server.close())
