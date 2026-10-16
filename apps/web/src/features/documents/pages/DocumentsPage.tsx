import { FileText, Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { DocumentStatus } from '@/lib/api/types'

import { DocumentList, DocumentListSkeleton } from '../components/DocumentList'
import { DropZone } from '../components/DropZone'
import { UploadButton } from '../components/UploadButton'
import { UploadProgressList } from '../components/UploadProgressList'
import { useDocumentLibrary, useUploadDocuments } from '../hooks/use-documents'

type Filter = 'all' | 'ready' | 'processing' | 'failed'

const FILTER_STATUSES: Record<Filter, DocumentStatus[] | null> = {
  all: null,
  ready: ['completed'],
  processing: ['uploaded', 'processing'],
  failed: ['failed'],
}

/** Document library: upload (button or drag and drop), filter by status or name, and manage documents. */
export default function DocumentsPage() {
  const library = useDocumentLibrary()
  const { upload, uploads, isUploading } = useUploadDocuments()
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')

  const documents = useMemo(() => library.data?.pages.flatMap((page) => page.items) ?? [], [library.data])
  const total = library.data?.pages[0]?.pagination.total ?? 0

  const counts = useMemo(
    () => ({
      all: documents.length,
      ready: documents.filter((d) => d.status === 'completed').length,
      processing: documents.filter((d) => d.status === 'uploaded' || d.status === 'processing').length,
      failed: documents.filter((d) => d.status === 'failed').length,
    }),
    [documents],
  )

  const visible = useMemo(() => {
    const statuses = FILTER_STATUSES[filter]
    const needle = query.trim().toLowerCase()
    return documents.filter(
      (document) =>
        (!statuses || statuses.includes(document.status)) &&
        (!needle || document.filename.toLowerCase().includes(needle)),
    )
  }, [documents, filter, query])

  return (
    <>
      <PageHeader
        eyebrow="Your library"
        title="Documents"
        description="Upload PDFs to make them searchable and ready for questions. Drag and drop works too."
        actions={<UploadButton onFiles={upload} disabled={isUploading} />}
      />

      <UploadProgressList uploads={uploads} />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={filter} onValueChange={(value) => setFilter(value as Filter)}>
          <TabsList>
            <TabsTrigger value="all">All ({counts.all})</TabsTrigger>
            <TabsTrigger value="ready">Ready ({counts.ready})</TabsTrigger>
            <TabsTrigger value="processing">Processing ({counts.processing})</TabsTrigger>
            <TabsTrigger value="failed">Failed ({counts.failed})</TabsTrigger>
          </TabsList>
        </Tabs>
        <label className="flex w-full items-center gap-2 rounded-[10px] border bg-card px-3 py-2.5 text-subtle sm:w-64">
          <Search className="size-4" aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter by name…"
            aria-label="Filter documents by name"
            className="w-full bg-transparent text-xs text-foreground outline-none"
          />
        </label>
      </div>

      <DropZone onFiles={upload}>
        <div className="overflow-hidden rounded-[15px] border bg-card">
          {library.isPending ? (
            <DocumentListSkeleton rows={6} />
          ) : library.isError ? (
            <ErrorState error={library.error} onRetry={() => void library.refetch()} />
          ) : documents.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No documents yet"
              description="Upload your first PDF. Once it's processed you can search it and ask questions about it."
              action={<UploadButton onFiles={upload} label="Upload a PDF" />}
            />
          ) : visible.length === 0 ? (
            <p className="px-5 py-10 text-center text-xs text-muted-foreground">
              No documents match this filter.
            </p>
          ) : (
            <DocumentList documents={visible} />
          )}
        </div>
      </DropZone>

      {library.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => void library.fetchNextPage()}
            disabled={library.isFetchingNextPage}
          >
            Load more ({documents.length} of {total})
          </Button>
        </div>
      )}
    </>
  )
}
