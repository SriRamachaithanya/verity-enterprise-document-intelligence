import apiClient from '../api/client'
import type {
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentUploadResponse,
} from '../api/types'

export const uploadDocument = async (
  file: File,
  onProgress?: (percent: number) => void
): Promise<DocumentUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await apiClient.post<DocumentUploadResponse>(
    '/api/v1/documents/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    }
  )
  return data
}

export const getDocuments = async (
  limit = 20,
  offset = 0
): Promise<DocumentListResponse> => {
  const { data } = await apiClient.get<DocumentListResponse>('/api/v1/documents', {
    params: { limit, offset },
  })
  return data
}

export const getDocumentById = async (id: string): Promise<DocumentDetailResponse> => {
  const { data } = await apiClient.get<DocumentDetailResponse>(`/api/v1/documents/${id}`)
  return data
}

export const deleteDocument = async (
  id: string
): Promise<{ status: string; document_id: string }> => {
  const { data } = await apiClient.delete<{ status: string; document_id: string }>(
    `/api/v1/documents/${id}`
  )
  return data
}

export const documentService = {
  uploadDocument,
  getDocuments,
  getDocumentById,
  deleteDocument,
}

export default documentService
