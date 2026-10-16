/// <reference types="vitest/config" />
import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const CROSS_ORIGIN_ISOLATION = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp',
}

const API_PROXY = {
  '/api': { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: false },
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    port: 5173,
    // Cross-origin isolation lets the voice model use multi-threaded WASM
    // (several times faster synthesis). Production must send the same headers.
    headers: CROSS_ORIGIN_ISOLATION,
    // Same-origin in development: the browser talks to Vite, Vite forwards
    // /api to the backend. Cookies and CORS then behave like production
    // behind a single domain.
    proxy: API_PROXY,
    // Fallback for file systems that don't deliver change events into
    // containers: VITE_USE_POLLING=true.
    watch: process.env.VITE_USE_POLLING === 'true' ? { usePolling: true, interval: 300 } : undefined,
  },
  preview: { headers: CROSS_ORIGIN_ISOLATION, proxy: API_PROXY },
  worker: { format: 'es' },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}', 'tests/**/*.test.{ts,tsx}'],
    css: false,
    // Absolute URL so Node's fetch accepts it; MSW intercepts these requests.
    env: { VITE_API_BASE_URL: 'http://localhost:3000/api/v1' },
  },
})
