import { Loader2 } from 'lucide-react'

import type { DocumentStatus } from '@/lib/api/types'
import { cn } from '@/lib/utils'

import { STATUS_LABELS } from '../utils/document-status'

const STYLES: Record<DocumentStatus, string> = {
  uploaded: 'bg-warning-soft text-warning',
  processing: 'bg-warning-soft text-warning',
  completed: 'bg-success-soft text-success',
  failed: 'bg-destructive-soft text-destructive',
}

/** Colour-coded processing status, with a spinner while queued or processing. */
export function DocumentStatusBadge({ status, className }: { status: DocumentStatus; className?: string }) {
  const busy = status === 'uploaded' || status === 'processing'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-[7px] px-2 py-1.5 text-[10px] font-bold whitespace-nowrap',
        STYLES[status],
        className,
      )}
    >
      {busy && <Loader2 className="size-3 animate-spin" aria-hidden />}
      {STATUS_LABELS[status]}
    </span>
  )
}
