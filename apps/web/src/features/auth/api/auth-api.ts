import { CSRF_HEADER } from '@/core/constants'
import { http, postOne } from '@/lib/api/client'
import type { SessionTokens, User } from '@/lib/api/types'

import type { LoginValues, SignupValues } from '../schemas/auth-schemas'

/** Log in. The response carries the access token; the refresh token arrives as an httpOnly cookie. */
export function login(values: LoginValues): Promise<SessionTokens> {
  return postOne<SessionTokens>('/auth/login', values)
}

/** Create an account. Does not log in; call {@link login} afterwards. */
export function signup(values: Pick<SignupValues, 'name' | 'email' | 'password'>): Promise<User> {
  return postOne<User>('/auth/signup', values)
}

/** Revoke the refresh cookie on the server and clear it. */
export async function logout(): Promise<void> {
  await http.post('/auth/revoke', undefined, { headers: { [CSRF_HEADER]: '1' } })
}
