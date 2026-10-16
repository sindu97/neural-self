import { FileText } from 'lucide-react'

import { cn } from '@/lib/utils'

// The design alternates three soft tints for file icons; pick one per document.
const TINTS = [
  'bg-destructive-soft text-destructive',
  'bg-accent text-primary',
  'bg-success-soft text-success',
]

function tintFor(id: string): string {
  let hash = 0
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return TINTS[hash % TINTS.length] ?? TINTS[0]!
}

/** File icon in one of the design's three tints, stable per document. */
export function DocumentFileIcon({ id, className }: { id: string; className?: string }) {
  return (
    <div
      className={cn('grid h-[43px] w-10 shrink-0 place-items-center rounded-[10px]', tintFor(id), className)}
    >
      <FileText className="size-5" strokeWidth={1.7} aria-hidden />
    </div>
  )
}
