import { useState } from 'react'

import { Skeleton } from '@/components/ui/skeleton'
import type { DocumentItem } from '@/lib/api/types'

import { useDeleteDocument, useReprocessDocument } from '../hooks/use-documents'
import { DeleteDocumentDialog } from './DeleteDocumentDialog'
import { DocumentRow } from './DocumentRow'

/** Document rows with their actions (process again, delete with confirmation). */
export function DocumentList({ documents }: { documents: DocumentItem[] }) {
  const [pendingDelete, setPendingDelete] = useState<DocumentItem | null>(null)
  const deleteDocument = useDeleteDocument()
  const reprocessDocument = useReprocessDocument()

  return (
    <>
      <div className="px-[18px]">
        {documents.map((document) => (
          <DocumentRow
            key={document.id}
            document={document}
            onDelete={setPendingDelete}
            onReprocess={(item) => reprocessDocument.mutate(item)}
          />
        ))}
      </div>
      <DeleteDocumentDialog
        document={pendingDelete}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        onConfirm={(item) => {
          deleteDocument.mutate(item)
          setPendingDelete(null)
        }}
      />
    </>
  )
}

/** Loading placeholder shaped like document rows. */
export function DocumentListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="px-[18px]" aria-hidden>
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="flex items-center gap-3 border-b border-[#f0f1f5] py-[15px] last:border-b-0"
        >
          <Skeleton className="h-[43px] w-10 rounded-[10px]" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-1/2" />
            <Skeleton className="h-2.5 w-1/3" />
          </div>
          <Skeleton className="h-6 w-14 rounded-[7px]" />
        </div>
      ))}
    </div>
  )
}
