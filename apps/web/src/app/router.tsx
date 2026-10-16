import { createBrowserRouter, Navigate, type RouteObject } from 'react-router'

import { RedirectIfAuthenticated, RequireAdmin, RequireAuth } from '@/features/auth'

import { AppShell } from './layout/AppShell'
import { RouteError } from './layout/RouteError'

// Every page is lazy-loaded, so each one becomes its own small bundle and,
// for example, admin code is never downloaded by regular users.
const page = (load: () => Promise<{ default: React.ComponentType }>): Pick<RouteObject, 'lazy'> => ({
  lazy: async () => ({ Component: (await load()).default }),
})

export const routes: RouteObject[] = [
  {
    errorElement: <RouteError />,
    children: [
      {
        element: <RedirectIfAuthenticated />,
        children: [
          { path: '/login', ...page(() => import('@/features/auth/pages/LoginPage')) },
          { path: '/signup', ...page(() => import('@/features/auth/pages/SignupPage')) },
        ],
      },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <AppShell />,
            children: [
              { index: true, ...page(() => import('@/features/dashboard/pages/DashboardPage')) },
              { path: '/documents', ...page(() => import('@/features/documents/pages/DocumentsPage')) },
              // Optional id: a new chat gets its id mid-stream without remounting the page.
              { path: '/chat/:conversationId?', ...page(() => import('@/features/chat/pages/ChatPage')) },
              { path: '/search', ...page(() => import('@/features/retrieval/pages/SearchPage')) },
              { path: '/activity', ...page(() => import('@/features/activity/pages/ActivityPage')) },
              { path: '/settings', ...page(() => import('@/features/settings/pages/SettingsPage')) },
              {
                element: <RequireAdmin />,
                children: [
                  { path: '/admin/jobs', ...page(() => import('@/features/admin/pages/AdminJobsPage')) },
                ],
              },
            ],
          },
        ],
      },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
