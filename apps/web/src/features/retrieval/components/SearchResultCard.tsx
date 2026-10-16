import { FileText } from 'lucide-react'

import type { SearchResult } from '@/lib/api/types'

/** One matching passage; the bar shows how close it is in meaning to the query. */
export function SearchResultCard({ result, rank }: { result: SearchResult; rank: number }) {
  const relevance = Math.max(0, Math.min(1, result.score))
  return (
    <article className="rounded-[15px] border bg-card p-5 shadow-card">
      <header className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className="grid size-6 place-items-center rounded-lg bg-accent text-[11px] font-bold text-primary">
          {rank}
        </span>
        <span className="flex min-w-0 items-center gap-1.5 text-xs font-semibold">
          <FileText className="size-3.5 shrink-0 text-subtle" aria-hidden />
          <span className="truncate">{result.filename}</span>
        </span>
        {result.page_number !== null && (
          <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            Page {result.page_number}
          </span>
        )}
        <span className="ml-auto flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="h-1.5 w-16 overflow-hidden rounded-full bg-muted" aria-hidden>
            <span className="block h-full rounded-full bg-primary" style={{ width: `${relevance * 100}%` }} />
          </span>
          {Math.round(relevance * 100)}% match
        </span>
      </header>
      <p className="text-[13px] leading-relaxed text-foreground/85">{result.content}</p>
    </article>
  )
}
