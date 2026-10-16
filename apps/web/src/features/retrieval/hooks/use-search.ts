import { keepPreviousData, useQuery } from '@tanstack/react-query'

import type { SearchRequest } from '@/lib/api/types'

import { searchDocuments } from '../api/retrieval-api'

/** Run a search when `request` has a query; keeps showing previous results while a new search runs. */
export function useSearch(request: SearchRequest | null) {
  return useQuery({
    queryKey: ['search', request],
    queryFn: () => searchDocuments(request!),
    enabled: request !== null && request.query.trim().length > 0,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  })
}
