/**
 * The browser session.
 *
 * - The access token lives only in this module's memory: never in
 *   localStorage or sessionStorage, where injected scripts could read it.
 * - The refresh token is an httpOnly cookie that JavaScript can't access at
 *   all; the browser sends it to /auth/* automatically.
 * - After a page reload the access token is gone, so the app calls
 *   refreshSession() to get a new one from the cookie.
 */
import { CSRF_HEADER } from '@/core/constants'
import { env } from '@/core/config/env'

import { apiErrorFromResponse, toApiError } from './errors'
import type { ApiEnvelope, SessionTokens } from './types'

let accessToken: string | null = null
const expiredListeners = new Set<() => void>()

/** The current access token, held in memory only. */
export function getAccessToken(): string | null {
  return accessToken
}

/** Replace (or clear) the in-memory access token. */
export function setAccessToken(token: string | null): void {
  accessToken = token
}

/** Subscribe to "the session can no longer be refreshed" (e.g. logged out elsewhere). */
export function onSessionExpired(listener: () => void): () => void {
  expiredListeners.add(listener)
  return () => expiredListeners.delete(listener)
}

/** Clear the token and tell listeners that the user must log in again. */
export function notifySessionExpired(): void {
  accessToken = null
  expiredListeners.forEach((listener) => listener())
}

let inflightRefresh: Promise<SessionTokens> | null = null

/**
 * Exchange the refresh cookie for a new access token.
 *
 * Refresh tokens are single-use: presenting one twice looks like theft to the
 * backend, which then logs the user out everywhere. So concurrent callers in
 * this tab share one request (single flight), and tabs take turns through a
 * Web Lock. When a tab gets the lock, the cookie has already been rotated by
 * the previous holder, so it never replays a used token.
 */
export function refreshSession(): Promise<SessionTokens> {
  inflightRefresh ??= withCrossTabLock(requestRefresh).finally(() => {
    inflightRefresh = null
  })
  return inflightRefresh
}

async function requestRefresh(): Promise<SessionTokens> {
  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { [CSRF_HEADER]: '1' },
    })
  } catch (error) {
    throw toApiError(error)
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw apiErrorFromResponse(response.status, body, response.headers)

  const tokens = (body as ApiEnvelope<SessionTokens>).data[0]
  if (!tokens) throw apiErrorFromResponse(500, body, response.headers)
  accessToken = tokens.access_token
  return tokens
}

function withCrossTabLock<T>(task: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && 'locks' in navigator) {
    return navigator.locks.request('neuralshelf-session-refresh', task)
  }
  return task()
}
