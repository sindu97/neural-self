import { Progress } from '@/components/ui/progress'

import type { UploadProgress } from '../hooks/use-documents'

/** Progress bar for each upload in flight; renders nothing when idle. */
export function UploadProgressList({ uploads }: { uploads: UploadProgress[] }) {
  if (uploads.length === 0) return null
  return (
    <div className="mb-4 space-y-2.5 rounded-[15px] border bg-card p-4" aria-live="polite">
      {uploads.map((upload) => (
        <div key={upload.key}>
          <div className="mb-1.5 flex justify-between text-[11px]">
            <span className="truncate font-medium">{upload.name}</span>
            <span className="text-muted-foreground">{upload.percent}%</span>
          </div>
          <Progress value={upload.percent} className="h-1.5" />
        </div>
      ))}
    </div>
  )
}
