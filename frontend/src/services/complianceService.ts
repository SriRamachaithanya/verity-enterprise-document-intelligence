import apiClient from '../api/client'
import type {
  ComplianceEvaluationResponse,
  GapAnalysisResponse,
  HistoricalDiffResponse,
} from '../api/types'

export const evaluateCompliance = async (
  framework_id: string,
  requirement_id?: string,
  evidence_document_ids?: string[]
): Promise<ComplianceEvaluationResponse> => {
  const { data } = await apiClient.post<ComplianceEvaluationResponse>(
    '/api/v1/compliance/evaluate',
    {
      framework_id,
      requirement_id,
      evidence_document_ids,
    }
  )
  return data
}

export const getGapAnalysis = async (
  framework_id: string,
  severity_filter = 'All'
): Promise<GapAnalysisResponse> => {
  const { data } = await apiClient.post<GapAnalysisResponse>(
    '/api/v1/compliance/gap-analysis',
    {
      framework_id,
      severity_filter,
    }
  )
  return data
}

export const getComplianceHistory = async (
  framework_id = 'SOC2'
): Promise<HistoricalDiffResponse> => {
  const { data } = await apiClient.get<HistoricalDiffResponse>(
    '/api/v1/compliance/history',
    {
      params: { framework_id },
    }
  )
  return data
}

export const complianceService = {
  evaluateCompliance,
  getGapAnalysis,
  getComplianceHistory,
}

export default complianceService
