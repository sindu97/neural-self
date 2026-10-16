import { useContext } from 'react'

import { AuthContext, type AuthContextValue } from '../components/auth-context'

/** The current session and the login, signup and logout actions. Use inside {@link AuthProvider}. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>.')
  return context
}

/** The logged-in user; only use inside routes wrapped by <RequireAuth>. */
export function useCurrentUser() {
  const { user } = useAuth()
  if (!user) throw new Error('useCurrentUser requires an authenticated route.')
  return user
}
