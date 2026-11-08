import apiClient from '../api/client'
import type { BacklinksListResponse, KnowledgeNodeDetailResponse } from '../api/types'

export const getKnowledgeNode = async (
  slug: string,
  depth = 1
): Promise<KnowledgeNodeDetailResponse> => {
  const { data } = await apiClient.get<KnowledgeNodeDetailResponse>(
    `/api/v1/knowledge/${slug}`,
    {
      params: { depth },
    }
  )
  return data
}

export const getBacklinks = async (slug: string): Promise<BacklinksListResponse> => {
  const { data } = await apiClient.get<BacklinksListResponse>(
    `/api/v1/knowledge/${slug}/backlinks`
  )
  return data
}

export const knowledgeService = {
  getKnowledgeNode,
  getBacklinks,
}

export default knowledgeService
