import { useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'

import { onSessionExpired, refreshSession, setAccessToken } from '@/lib/api/session'
import type { User } from '@/lib/api/types'

import * as authApi from '../api/auth-api'
import type { LoginValues, SignupValues } from '../schemas/auth-schemas'
import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context'

/**
 * Owns the session: restores it from the refresh cookie on load and exposes login, signup and logout.
 *
 * @remarks
 * Signs out locally, and clears all cached data, when the session can no longer be refreshed.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<User | null>(null)

  const signOutLocally = useCallback(() => {
    setAccessToken(null)
    setUser(null)
    setStatus('anonymous')
    queryClient.clear() // never show one user's cached data to the next
  }, [queryClient])

  // Restore the session after a page load: the access token only lives in
  // memory, but the httpOnly refresh cookie survives reloads.
  useEffect(() => {
    let active = true
    refreshSession()
      .then((tokens) => {
        if (!active) return
        setUser(tokens.user)
        setStatus('authenticated')
      })
      .catch(() => {
        if (active) setStatus('anonymous')
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => onSessionExpired(signOutLocally), [signOutLocally])

  const login = useCallback(async (values: LoginValues) => {
    const tokens = await authApi.login(values)
    setAccessToken(tokens.access_token)
    setUser(tokens.user)
    setStatus('authenticated')
    return tokens.user
  }, [])

  const signup = useCallback(
    async (values: SignupValues) => {
      await authApi.signup(values)
      return login({ email: values.email, password: values.password })
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      signOutLocally()
    }
  }, [signOutLocally])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, signup, logout }),
    [status, user, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
