import { AlertTriangle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { toApiError } from '@/lib/api/errors'

/** Inline error with retry; shows the request ID so bugs can be traced in server logs. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = toApiError(error)
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center" role="alert">
      <div className="mb-3 grid size-11 place-items-center rounded-2xl bg-destructive-soft text-destructive">
        <AlertTriangle className="size-5" aria-hidden />
      </div>
      <p className="text-sm font-medium">{apiError.message}</p>
      {apiError.requestId && (
        <p className="mt-1 font-mono text-[10px] text-subtle">Reference: {apiError.requestId}</p>
      )}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
