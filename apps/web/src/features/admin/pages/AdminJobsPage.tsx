import { AlertTriangle, CheckCircle2, Clock, Loader2, RotateCcw, ServerCrash } from 'lucide-react'
import { useState } from 'react'

import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatCard } from '@/components/layout/StatCard'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { JobStatus } from '@/lib/api/types'
import { formatRelativeTime } from '@/lib/format'

import { JobStatusBadge } from '../components/JobStatusBadge'
import { useJobStats, useJobs, useRetryAllFailed, useRetryJob } from '../hooks/use-admin-jobs'

const PAGE_SIZE = 20
type Filter = JobStatus | 'all'

/** Admin page: monitor the ingestion queue and retry failed jobs. */
export default function AdminJobsPage() {
  const [filter, setFilter] = useState<Filter>('failed')
  const [offset, setOffset] = useState(0)
  const stats = useJobStats()
  const jobs = useJobs(filter === 'all' ? undefined : filter, offset, PAGE_SIZE)
  const retryJob = useRetryJob()
  const retryAll = useRetryAllFailed()

  const counts = stats.data?.counts ?? {}
  const total = jobs.data?.pagination.total ?? 0

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Ingestion jobs"
        description="Monitor document processing across all users and retry failures. Refreshes every 5 seconds."
        actions={
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button disabled={!counts.failed || retryAll.isPending}>
                {retryAll.isPending ? <Loader2 className="animate-spin" /> : <RotateCcw />} Retry all failed
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Retry all failed documents?</AlertDialogTitle>
                <AlertDialogDescription>
                  Every failed document that isn't already queued gets a new processing job. Use this after
                  fixing the cause, for example once the AI service is back up.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => retryAll.mutate()}>Retry all</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        }
      />

      <section className="mb-7 grid grid-cols-2 gap-[15px] lg:grid-cols-4">
        <StatCard
          label="Queued"
          value={counts.queued}
          icon={Clock}
          tone="primary"
          note={stats.data && `Oldest waiting ${Math.round(stats.data.oldest_due_job_age_seconds)}s`}
          loading={stats.isPending}
        />
        <StatCard
          label="Running"
          value={counts.running}
          icon={Loader2}
          tone="warning"
          note={
            stats.data &&
            (stats.data.running_with_expired_lease
              ? `${stats.data.running_with_expired_lease} with an expired lease`
              : 'No stuck jobs')
          }
          loading={stats.isPending}
        />
        <StatCard
          label="Succeeded"
          value={counts.succeeded}
          icon={CheckCircle2}
          tone="success"
          loading={stats.isPending}
        />
        <StatCard
          label="Failed"
          value={counts.failed}
          icon={AlertTriangle}
          tone="destructive"
          loading={stats.isPending}
        />
      </section>

      <div className="mb-4">
        <Tabs
          value={filter}
          onValueChange={(value) => {
            setFilter(value as Filter)
            setOffset(0)
          }}
        >
          <TabsList>
            {(['failed', 'queued', 'running', 'succeeded', 'all'] as const).map((value) => (
              <TabsTrigger key={value} value={value} className="capitalize">
                {value}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <div className="overflow-hidden rounded-[15px] border bg-card">
        {jobs.isPending ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} className="h-10" />
            ))}
          </div>
        ) : jobs.isError ? (
          <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
        ) : jobs.data.items.length === 0 ? (
          <EmptyState
            icon={ServerCrash}
            title={`No ${filter === 'all' ? '' : filter} jobs`}
            description="Nothing to show here right now."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Document</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Attempts</TableHead>
                <TableHead className="hidden md:table-cell">Last error</TableHead>
                <TableHead className="hidden sm:table-cell">Updated</TableHead>
                <TableHead className="w-0" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.data.items.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="max-w-[220px]">
                    <div className="truncate text-xs font-semibold">{job.filename}</div>
                    <div className="truncate font-mono text-[10px] text-subtle">
                      user {job.user_id.slice(0, 8)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <JobStatusBadge status={job.status} />
                  </TableCell>
                  <TableCell className="text-xs">
                    {job.attempts} / {job.max_attempts}
                  </TableCell>
                  <TableCell className="hidden max-w-[280px] md:table-cell">
                    {job.last_error ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="block truncate font-mono text-[11px] text-destructive">
                            {job.last_error}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-md font-mono text-[11px] break-all">
                          {job.last_error}
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className="text-xs text-subtle">—</span>
                    )}
                  </TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                    {formatRelativeTime(job.updated_at ?? job.created_at)}
                  </TableCell>
                  <TableCell>
                    {job.status === 'failed' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => retryJob.mutate(job.id)}
                        disabled={retryJob.isPending}
                      >
                        <RotateCcw /> Retry
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(offset - PAGE_SIZE)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </>
  )
}
