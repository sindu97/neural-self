import { Activity } from 'lucide-react'

import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Skeleton } from '@/components/ui/skeleton'

import { ActivityTimeline } from '../components/ActivityTimeline'
import { useActivity } from '../hooks/use-activity'

/** Activity page: the full timeline of uploads, processing results and conversations. */
export default function ActivityPage() {
  const activity = useActivity()
  return (
    <>
      <PageHeader
        eyebrow="A pulse on your workspace"
        title="Activity"
        description="Uploads, processing results and conversations, newest first."
      />
      <div className="max-w-2xl rounded-[15px] border bg-card p-5">
        {activity.isPending ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} className="h-10" />
            ))}
          </div>
        ) : activity.isError ? (
          <ErrorState error={activity.error} />
        ) : activity.items.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No activity yet"
            description="Upload a document or start a conversation."
          />
        ) : (
          <ActivityTimeline items={activity.items} />
        )}
      </div>
    </>
  )
}
