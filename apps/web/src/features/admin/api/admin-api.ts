import { getOne, getPage, postOne } from '@/lib/api/client'
import type { BulkRetryResult, IngestionJob, JobStats, JobStatus, Page, PageParams } from '@/lib/api/types'

/** Ingestion jobs across all users, newest first; optionally only one status. Admin only. */
export function listJobs(params: PageParams & { status?: JobStatus } = {}): Promise<Page<IngestionJob>> {
  return getPage<IngestionJob>('/admin/ingestion-jobs', { params })
}

/** Queue health: jobs per status, oldest waiting job, jobs with expired leases. Admin only. */
export function getJobStats(): Promise<JobStats> {
  return getOne<JobStats>('/admin/ingestion-jobs/stats')
}

/** Queue a new attempt for a failed job's document. Admin only. */
export function retryJob(jobId: string): Promise<{ job_id: string; document_id: string }> {
  return postOne(`/admin/ingestion-jobs/${jobId}/retry`)
}

/** Requeue up to `limit` failed documents. Admin only. */
export function retryAllFailed(limit = 100): Promise<BulkRetryResult> {
  return postOne<BulkRetryResult>('/admin/ingestion-jobs/retry-failed', undefined, { params: { limit } })
}
