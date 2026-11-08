import apiClient from '../api/client'
import type { SearchResponse } from '../api/types'

export interface SearchOptions {
  query: string
  limit?: number
  top_k?: number
  filters?: {
    document_id?: string
  }
}

export const search = async (
  queryOrOptions: string | SearchOptions,
  top_k = 5,
  document_ids?: string[]
): Promise<SearchResponse> => {
  let q: string
  let k: number = top_k
  let docIds: string[] | undefined = document_ids

  if (typeof queryOrOptions === 'object') {
    q = queryOrOptions.query
    k = queryOrOptions.limit || queryOrOptions.top_k || 5
    if (queryOrOptions.filters?.document_id) {
      docIds = [queryOrOptions.filters.document_id]
    }
  } else {
    q = queryOrOptions
  }

  const { data } = await apiClient.post<SearchResponse>('/api/v1/search', {
    query: q,
    top_k: k,
    document_ids: docIds,
  })
  return data
}

export const searchService = {
  search,
}

export default searchService
