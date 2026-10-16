import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

const TONES = {
  primary: 'bg-accent text-primary',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  destructive: 'bg-destructive-soft text-destructive',
} as const

/** Metric tile from the design's stats row. */
export function StatCard({
  label,
  value,
  icon: Icon,
  tone = 'primary',
  note,
  loading,
}: {
  label: string
  value: ReactNode
  icon: LucideIcon
  tone?: keyof typeof TONES
  note?: ReactNode
  loading?: boolean
}) {
  return (
    <div className="rounded-[15px] border bg-card px-3 py-3.5 shadow-card sm:px-[19px] sm:py-[18px]">
      {/* Narrow phones: icon above the label so long labels never overflow. */}
      <div className="mb-3.5 flex flex-col-reverse items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
        <span className="min-w-0 text-[10px] leading-tight font-medium text-muted-foreground sm:text-[11px]">
          {label}
        </span>
        <span
          className={cn('grid size-[29px] shrink-0 place-items-center rounded-[10px] sm:size-8', TONES[tone])}
        >
          <Icon className="size-4" strokeWidth={1.7} aria-hidden />
        </span>
      </div>
      {loading ? (
        <Skeleton className="h-7 w-12" />
      ) : (
        <div className="text-[22px] font-bold tracking-[-0.7px] sm:text-[25px]">{value}</div>
      )}
      {note && <div className="mt-1.5 text-[9px] text-muted-foreground sm:text-[10px]">{note}</div>}
    </div>
  )
}
