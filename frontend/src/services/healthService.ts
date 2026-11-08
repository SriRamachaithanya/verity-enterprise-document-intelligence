import apiClient from '../api/client'
import type { HealthResponse, ReadinessResponse } from '../api/types'

export const getHealth = async (): Promise<HealthResponse> => {
  const { data } = await apiClient.get<HealthResponse>('/health')
  return data
}

export const getReadiness = async (): Promise<ReadinessResponse> => {
  const { data } = await apiClient.get<ReadinessResponse>('/ready')
  return data
}

export const healthService = {
  getHealth,
  getReadiness,
}

export default healthService
