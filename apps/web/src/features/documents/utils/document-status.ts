import type { DocumentItem, DocumentStatus } from '@/lib/api/types'

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: 'Queued',
  processing: 'Processing',
  completed: 'Ready',
  failed: 'Failed',
}

/** Whether the document is still queued or processing. */
export function isInProgress(document: Pick<DocumentItem, 'status'>): boolean {
  return document.status === 'uploaded' || document.status === 'processing'
}
