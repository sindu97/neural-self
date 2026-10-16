import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { describeError } from '@/lib/api/errors'
import type { JobStatus } from '@/lib/api/types'

import * as adminApi from '../api/admin-api'

const adminKeys = {
  all: ['admin', 'jobs'] as const,
  list: (status: JobStatus | undefined, offset: number) => ['admin', 'jobs', 'list', status, offset] as const,
  stats: ['admin', 'jobs', 'stats'] as const,
}

const REFRESH_MS = 5000

/** Queue statistics, refreshed every few seconds. */
export function useJobStats() {
  return useQuery({ queryKey: adminKeys.stats, queryFn: adminApi.getJobStats, refetchInterval: REFRESH_MS })
}

/** One page of ingestion jobs, refreshed every few seconds; keeps the previous page while loading. */
export function useJobs(status: JobStatus | undefined, offset: number, limit: number) {
  return useQuery({
    queryKey: adminKeys.list(status, offset),
    queryFn: () => adminApi.listJobs({ status, offset, limit }),
    placeholderData: keepPreviousData,
    refetchInterval: REFRESH_MS,
  })
}

/** Retry one failed job, with a toast, then refresh the admin views. */
export function useRetryJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: adminApi.retryJob,
    onSuccess: () => {
      toast.success('Queued for another attempt.')
      return queryClient.invalidateQueries({ queryKey: adminKeys.all })
    },
    onError: (error) => toast.error(describeError(error)),
  })
}

/** Requeue every failed document, with a toast, then refresh the admin views. */
export function useRetryAllFailed() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => adminApi.retryAllFailed(),
    onSuccess: (result) => {
      toast.success(
        result.requeued === 0
          ? 'No failed documents to retry.'
          : `${result.requeued} document(s) queued again.`,
      )
      return queryClient.invalidateQueries({ queryKey: adminKeys.all })
    },
    onError: (error) => toast.error(describeError(error)),
  })
}
