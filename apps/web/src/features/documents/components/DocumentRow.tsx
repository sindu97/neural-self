import { MessageSquareText, MoreHorizontal, RotateCcw, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ROUTES } from '@/core/constants'
import type { DocumentItem } from '@/lib/api/types'
import { formatBytes, formatRelativeTime } from '@/lib/format'

import { isInProgress } from '../utils/document-status'
import { DocumentFileIcon } from './DocumentFileIcon'
import { DocumentStatusBadge } from './DocumentStatusBadge'

/** One document: name, size, age, status and an actions menu (ask, process again, delete). */
export function DocumentRow({
  document,
  onDelete,
  onReprocess,
}: {
  document: DocumentItem
  onDelete?: (document: DocumentItem) => void
  onReprocess?: (document: DocumentItem) => void
}) {
  const navigate = useNavigate()
  const ready = document.status === 'completed'

  return (
    <div className="flex items-center gap-3 border-b border-[#f0f1f5] py-[15px] last:border-b-0">
      <DocumentFileIcon id={document.id} />
      <div className="min-w-0 flex-1">
        <strong className="block truncate text-xs font-semibold" title={document.filename}>
          {document.filename}
        </strong>
        <small className="mt-1.5 block text-[10px] text-subtle">
          PDF document · {formatBytes(document.file_size_bytes)} · Added{' '}
          {formatRelativeTime(document.created_at)}
        </small>
        {document.status === 'failed' && document.error_message && (
          <small className="mt-1 block text-[10px] text-destructive">{document.error_message}</small>
        )}
      </div>
      <DocumentStatusBadge status={document.status} />
      {(onDelete || onReprocess) && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-subtle"
              aria-label={`Actions for ${document.filename}`}
            >
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuItem
              disabled={!ready}
              onSelect={() => navigate(`${ROUTES.chat}?document=${document.id}`)}
            >
              <MessageSquareText /> Ask about this document
            </DropdownMenuItem>
            {onReprocess && (
              <DropdownMenuItem disabled={isInProgress(document)} onSelect={() => onReprocess(document)}>
                <RotateCcw /> Process again
              </DropdownMenuItem>
            )}
            {onDelete && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onSelect={() => onDelete(document)}>
                  <Trash2 /> Delete
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  )
}
