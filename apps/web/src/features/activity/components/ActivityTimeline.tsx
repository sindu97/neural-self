import { AlertTriangle, Check, MessageSquare, Plus } from 'lucide-react'
import { Link } from 'react-router'

import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

import type { ActivityItem, ActivityKind } from '../hooks/use-activity'

const ICONS: Record<ActivityKind, { icon: typeof Check; className: string }> = {
  indexed: { icon: Check, className: 'bg-success-soft text-success' },
  conversation: { icon: MessageSquare, className: 'bg-accent text-primary' },
  uploaded: { icon: Plus, className: 'bg-warning-soft text-warning' },
  failed: { icon: AlertTriangle, className: 'bg-destructive-soft text-destructive' },
}

/** Vertical timeline of activity items, newest first, each linking to its source. */
export function ActivityTimeline({ items }: { items: ActivityItem[] }) {
  return (
    <ol>
      {items.map((item, index) => {
        const { icon: Icon, className } = ICONS[item.kind]
        return (
          <li key={item.id} className="relative flex gap-[11px] pb-[21px] last:pb-0">
            {index < items.length - 1 && (
              <span
                className="absolute top-[31px] bottom-0 left-[14px] border-l border-[#e9ebf3]"
                aria-hidden
              />
            )}
            <span
              className={cn('z-[1] grid size-[29px] shrink-0 place-items-center rounded-[9px]', className)}
            >
              <Icon className="size-[15px]" strokeWidth={1.8} aria-hidden />
            </span>
            <div className="min-w-0 text-[11px] leading-[1.55] text-muted-foreground">
              <strong className="font-semibold text-foreground/85">{item.title}</strong>
              <Link to={item.href} className="block truncate hover:text-primary">
                {item.subject}
              </Link>
              <small className="mt-1 block text-[10px] text-subtle">{formatRelativeTime(item.at)}</small>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
