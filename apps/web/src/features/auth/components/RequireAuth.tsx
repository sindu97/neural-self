import { Navigate, Outlet, useLocation } from 'react-router'

import { FullPageLoader } from '@/components/feedback/FullPageLoader'
import { ROUTES } from '@/core/constants'

import { useAuth } from '../hooks/use-auth'

/** Renders child routes only for logged-in users; others go to /login. */
export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <FullPageLoader />
  if (status === 'anonymous') {
    return <Navigate to={ROUTES.login} replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}

/** Hides admin screens from non-admins. The backend enforces this too (403). */
export function RequireAdmin() {
  const { user } = useAuth()
  if (!user?.is_admin) return <Navigate to={ROUTES.overview} replace />
  return <Outlet />
}

/**
 * Login/signup pages: logged-in users are sent into the app, back to the page
 * that sent them to login if there was one.
 */
export function RedirectIfAuthenticated() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <FullPageLoader />
  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from ?? ROUTES.overview
    return <Navigate to={from} replace />
  }
  return <Outlet />
}
