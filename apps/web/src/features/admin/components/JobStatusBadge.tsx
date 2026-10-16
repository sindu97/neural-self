import type { JobStatus } from '@/lib/api/types'
import { cn } from '@/lib/utils'

const STYLES: Record<JobStatus, string> = {
  queued: 'bg-accent text-primary',
  running: 'bg-warning-soft text-warning',
  succeeded: 'bg-success-soft text-success',
  failed: 'bg-destructive-soft text-destructive',
}

/** Colour-coded badge for an ingestion job's status. */
export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={cn('rounded-[7px] px-2 py-1 text-[10px] font-bold capitalize', STYLES[status])}>
      {status}
    </span>
  )
}
