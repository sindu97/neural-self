import { http, HttpResponse } from 'msw'

export const API = 'http://localhost:3000/api/v1'

export const user = { id: 'u-1', name: 'Asha Verma', email: 'asha@example.com', is_admin: false }

export function envelope<T>(data: T[], message = 'OK') {
  return { success: true, code: 'SUCCESS', message, data }
}

export function errorEnvelope(code: string, message: string, data: unknown[] = []) {
  return { success: false, code, message, data }
}

export function sessionTokens(accessToken = 'access-1') {
  return {
    access_token: accessToken,
    token_type: 'bearer',
    expires_in: 1800,
    refresh_expires_at: '2026-10-22T00:00:00Z',
    user,
  }
}

/** Default: nobody is signed in. Tests override handlers as needed. */
export const handlers = [
  http.post(`${API}/auth/refresh`, () =>
    HttpResponse.json(errorEnvelope('INVALID_REFRESH_TOKEN', 'Refresh token is invalid.'), { status: 401 }),
  ),
]
