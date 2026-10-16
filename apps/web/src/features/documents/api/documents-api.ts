import { getOne, getPage, postOne, remove } from '@/lib/api/client'
import type { DocumentItem, Page, PageParams } from '@/lib/api/types'

/** A page of the user's documents, newest first. */
export function listDocuments(params: PageParams = {}): Promise<Page<DocumentItem>> {
  return getPage<DocumentItem>('/documents', { params })
}

/** One document's metadata and processing status. */
export function getDocument(id: string): Promise<DocumentItem> {
  return getOne<DocumentItem>(`/documents/${id}`)
}

/** Upload a PDF and queue it for processing; `onProgress` receives 0–100. */
export function uploadDocument(file: File, onProgress?: (percent: number) => void): Promise<DocumentItem> {
  const form = new FormData()
  form.append('file', file)
  return postOne<DocumentItem>('/documents', form, {
    // Uploads can be large; don't apply the default request timeout.
    timeout: 0,
    onUploadProgress: (event) => {
      if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100))
    },
  })
}

/** Delete a document, its indexed text and its stored file. */
export function deleteDocument(id: string): Promise<void> {
  return remove(`/documents/${id}`)
}

/** Queue a failed or completed document for processing again. */
export function reprocessDocument(id: string): Promise<DocumentItem> {
  return postOne<DocumentItem>(`/documents/${id}/reprocess`)
}
