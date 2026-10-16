import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { ErrorBoundary } from '@/components/feedback/ErrorBoundary'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/features/auth'

import { queryClient } from './query-client'

/** App-wide providers: error boundary, server-state cache, auth session, tooltips and toasts. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <TooltipProvider delayDuration={200}>
            {children}
            <Toaster position="bottom-center" richColors closeButton />
          </TooltipProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
