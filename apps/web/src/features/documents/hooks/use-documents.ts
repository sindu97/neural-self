import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { toast } from 'sonner'

import { DOCUMENT_POLL_INTERVAL_MS } from '@/core/constants'
import { describeError } from '@/lib/api/errors'
import type { DocumentItem, Page } from '@/lib/api/types'

import * as documentsApi from '../api/documents-api'
import { isInProgress } from '../utils/document-status'
import { validateFiles } from '../utils/validate-files'

export const documentKeys = {
  all: ['documents'] as const,
  recent: (limit: number) => ['documents', 'recent', limit] as const,
  library: ['documents', 'library'] as const,
}

const LIBRARY_PAGE_SIZE = 100

/** Keep polling while any visible document is still queued or processing. */
function pollWhileProcessing(items: DocumentItem[] | undefined) {
  return items?.some(isInProgress) ? DOCUMENT_POLL_INTERVAL_MS : false
}

/** The newest `limit` documents, polled while any of them is still processing. */
export function useRecentDocuments(limit = 5) {
  return useQuery({
    queryKey: documentKeys.recent(limit),
    queryFn: () => documentsApi.listDocuments({ limit }),
    refetchInterval: (query) => pollWhileProcessing(query.state.data?.items),
  })
}

/** The full library, loaded 100 at a time. */
export function useDocumentLibrary() {
  return useInfiniteQuery({
    queryKey: documentKeys.library,
    queryFn: ({ pageParam }) => documentsApi.listDocuments({ limit: LIBRARY_PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last: Page<DocumentItem>) => {
      const next = last.pagination.offset + last.pagination.limit
      return next < last.pagination.total ? next : undefined
    },
    refetchInterval: (query) => pollWhileProcessing(query.state.data?.pages.flatMap((page) => page.items)),
  })
}

/** Upload progress for one file. */
export interface UploadProgress {
  key: string
  name: string
  percent: number
}

/** Upload several PDFs; exposes per-file progress for the UI. */
export function useUploadDocuments() {
  const queryClient = useQueryClient()
  const [uploads, setUploads] = useState<UploadProgress[]>([])

  const mutation = useMutation({
    mutationFn: async ({ file, key }: { file: File; key: string }) =>
      documentsApi.uploadDocument(file, (percent) =>
        setUploads((current) => current.map((item) => (item.key === key ? { ...item, percent } : item))),
      ),
    onSettled: (_data, _error, { key }) =>
      setUploads((current) => current.filter((item) => item.key !== key)),
  })

  const upload = useCallback(
    async (files: Iterable<File>) => {
      const { accepted, rejected } = validateFiles(files)
      for (const { file, reason } of rejected) toast.error(`${file.name}: ${reason}`)

      const results = await Promise.allSettled(
        accepted.map((file) => {
          const key = `${file.name}-${file.size}-${crypto.randomUUID()}`
          setUploads((current) => [...current, { key, name: file.name, percent: 0 }])
          return mutation.mutateAsync({ file, key }).catch((error: unknown) => {
            toast.error(`${file.name}: ${describeError(error)}`)
            throw error
          })
        }),
      )

      const succeeded = results.filter((result) => result.status === 'fulfilled').length
      if (succeeded > 0) {
        toast.success(
          succeeded === 1 ? 'Document uploaded. Processing has started.' : `${succeeded} documents uploaded.`,
        )
        await queryClient.invalidateQueries({ queryKey: documentKeys.all })
      }
    },
    [mutation, queryClient],
  )

  return { upload, uploads, isUploading: uploads.length > 0 }
}

/** Delete a document, confirm with a toast and refresh document lists. */
export function useDeleteDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (document: DocumentItem) => documentsApi.deleteDocument(document.id),
    onSuccess: (_data, document) => {
      toast.success(`Deleted ${document.filename}.`)
      return queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
    onError: (error) => toast.error(describeError(error)),
  })
}

/** Queue a document for processing again and refresh document lists. */
export function useReprocessDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (document: DocumentItem) => documentsApi.reprocessDocument(document.id),
    onSuccess: (_data, document) => {
      toast.success(`${document.filename} queued for processing.`)
      return queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
    onError: (error) => toast.error(describeError(error)),
  })
}
