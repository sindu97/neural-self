import { createContext } from 'react'

import type { User } from '@/lib/api/types'

import type { LoginValues, SignupValues } from '../schemas/auth-schemas'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

/** What {@link useAuth} returns: the session state and the actions that change it. */
export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  login: (values: LoginValues) => Promise<User>
  signup: (values: SignupValues) => Promise<User>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
