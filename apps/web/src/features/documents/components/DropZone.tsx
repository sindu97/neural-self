import { UploadCloud } from 'lucide-react'
import { type ReactNode, useState } from 'react'

import { cn } from '@/lib/utils'

/** Accepts PDFs dropped anywhere on its area. */
export function DropZone({ onFiles, children }: { onFiles: (files: File[]) => void; children: ReactNode }) {
  const [active, setActive] = useState(false)
  return (
    <div
      className="relative"
      onDragOver={(event) => {
        if (!event.dataTransfer.types.includes('Files')) return
        event.preventDefault()
        setActive(true)
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setActive(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        setActive(false)
        const files = Array.from(event.dataTransfer.files)
        if (files.length) onFiles(files)
      }}
    >
      {children}
      <div
        className={cn(
          'pointer-events-none absolute inset-0 z-10 hidden place-items-center rounded-[15px] border-2 border-dashed border-primary bg-accent/90',
          active && 'grid',
        )}
      >
        <div className="flex flex-col items-center gap-2 text-primary">
          <UploadCloud className="size-8" aria-hidden />
          <span className="text-sm font-semibold">Drop PDFs to upload</span>
        </div>
      </div>
    </div>
  )
}
