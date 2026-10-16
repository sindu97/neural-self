import { FileText } from 'lucide-react'

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { Citation } from '@/lib/api/types'

/** Sources under an answer; numbers match the [n] markers in the text. */
export function Citations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null
  return (
    <div className="mt-3 border-t border-[#f0f1f5] pt-3">
      <div className="mb-2 text-[10px] font-bold tracking-[0.12em] text-subtle uppercase">Sources</div>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((citation) => (
          <Tooltip key={`${citation.document_id}-${citation.chunk_index}`}>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="flex max-w-[260px] items-center gap-1.5 rounded-lg border bg-background px-2 py-1 text-[11px] text-foreground/80 hover:border-primary/40 hover:bg-accent"
              >
                <span className="grid size-4 shrink-0 place-items-center rounded bg-accent text-[9px] font-bold text-primary">
                  {citation.number}
                </span>
                <FileText className="size-3 shrink-0 text-subtle" aria-hidden />
                <span className="truncate">{citation.filename}</span>
                {citation.page_number !== null && (
                  <span className="shrink-0 text-subtle">p. {citation.page_number}</span>
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs text-xs leading-relaxed">
              {citation.excerpt}
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
    </div>
  )
}
