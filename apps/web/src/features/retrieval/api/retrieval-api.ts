import { postList } from '@/lib/api/client'
import type { SearchRequest, SearchResult } from '@/lib/api/types'

/** Search the user's processed documents by meaning; best match first. */
export function searchDocuments(request: SearchRequest): Promise<SearchResult[]> {
  return postList<SearchResult>('/retrieval/search', request)
}
