import { Search, SearchX, Sparkles } from 'lucide-react'
import { type FormEvent, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'

import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { LIMITS } from '@/core/constants'
import { useDocumentLibrary } from '@/features/documents'
import type { SearchRequest } from '@/lib/api/types'

import { SearchResultCard } from '../components/SearchResultCard'
import { useSearch } from '../hooks/use-search'

const ALL_DOCUMENTS = 'all'

/** Semantic search. The query, result count and document filter live in the URL, so searches can be shared and revisited. */
export default function SearchPage() {
  const [params, setParams] = useSearchParams()
  const submittedQuery = params.get('q') ?? ''
  const topK = Number(params.get('k') ?? 5)
  const documentId = params.get('document') ?? ALL_DOCUMENTS
  const [draft, setDraft] = useState(submittedQuery)

  const library = useDocumentLibrary()
  const readyDocuments = useMemo(
    () => (library.data?.pages.flatMap((page) => page.items) ?? []).filter((d) => d.status === 'completed'),
    [library.data],
  )

  const request = useMemo<SearchRequest | null>(
    () =>
      submittedQuery
        ? {
            query: submittedQuery,
            top_k: topK,
            document_ids: documentId === ALL_DOCUMENTS ? [] : [documentId],
          }
        : null,
    [submittedQuery, topK, documentId],
  )
  const search = useSearch(request)

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    setParams(next)
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    update({ q: draft.trim() })
  }

  return (
    <>
      <PageHeader
        eyebrow="Find by meaning"
        title="Semantic search"
        description="Describe what you're looking for in your own words. Matches are found by meaning, not just keywords."
      />

      <form onSubmit={onSubmit} className="mb-6 rounded-[15px] border bg-card p-4 shadow-card">
        <div className="flex flex-col gap-3 md:flex-row">
          <label className="flex flex-1 items-center gap-2.5 rounded-[10px] border bg-background px-3.5 text-subtle focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30">
            <Search className="size-4 shrink-0" aria-hidden />
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={LIMITS.maxSearchLength}
              placeholder="e.g. how do plants turn sunlight into energy?"
              aria-label="Search query"
              className="h-11 w-full bg-transparent text-sm text-foreground outline-none"
            />
          </label>
          <div className="flex gap-3">
            <Select
              value={documentId}
              onValueChange={(value) => update({ document: value === ALL_DOCUMENTS ? '' : value })}
            >
              <SelectTrigger
                className="w-full data-[size=default]:h-11 md:w-52"
                aria-label="Documents to search"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_DOCUMENTS}>All documents</SelectItem>
                {readyDocuments.map((document) => (
                  <SelectItem key={document.id} value={document.id}>
                    {document.filename}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(topK)} onValueChange={(value) => update({ k: value })}>
              <SelectTrigger className="w-32 data-[size=default]:h-11" aria-label="Number of results">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[3, 5, 10, 20].map((k) => (
                  <SelectItem key={k} value={String(k)}>
                    Top {k}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="submit" className="h-11 px-5" disabled={!draft.trim()}>
              Search
            </Button>
          </div>
        </div>
      </form>

      {!request ? (
        <EmptyState
          icon={Sparkles}
          title="Search across everything you've uploaded"
          description="Results show the exact passage, the document and the page it came from."
        />
      ) : search.isPending ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-28 rounded-[15px]" />
          ))}
        </div>
      ) : search.isError ? (
        <div className="rounded-[15px] border bg-card">
          <ErrorState error={search.error} onRetry={() => void search.refetch()} />
        </div>
      ) : search.data.length === 0 ? (
        <EmptyState
          icon={SearchX}
          title="No matches"
          description="Nothing in your processed documents is close to this query. Try other words, or upload more documents."
        />
      ) : (
        <div className="space-y-3" aria-live="polite">
          {search.data.map((result, index) => (
            <SearchResultCard key={result.chunk_id} result={result} rank={index + 1} />
          ))}
        </div>
      )}
    </>
  )
}
