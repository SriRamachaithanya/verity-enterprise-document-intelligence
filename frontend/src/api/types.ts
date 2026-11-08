// Central TypeScript definitions for VERITY REST API

export type UserRole = 'admin' | 'auditor' | 'user'

export interface AuthenticatedUser {
  userId: string
  role: UserRole
  apiKey: string
}

export interface HealthResponse {
  status: string
  service: string
  version: string
  timestamp: string
}

export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency_ms: number
  details: Record<string, unknown>
}

export interface ReadinessResponse {
  status: 'ready' | 'degraded'
  components: Record<string, ComponentHealth>
  timestamp: string
}

export interface MalwareScanResult {
  scanned: boolean
  engine: string
  is_clean: boolean
  details: string
}

export interface DocumentUploadResponse {
  document_id: string
  filename: string
  file_hash: string
  file_size_bytes: number
  mime_type: string
  chunks_count: number
  status: 'ingested' | 'already_exists'
  message: string
  malware_scan: MalwareScanResult
}

export interface DocumentItem {
  id: string
  filename: string
  file_hash: string
  mime_type: string
  file_size_bytes: number
  page_count: number | null
  created_at: string
}

export interface DocumentListResponse {
  total_count: number
  documents: DocumentItem[]
  limit: number
  offset: number
}

export interface DocumentDetailResponse {
  id: string
  filename: string
  file_hash: string
  mime_type: string
  file_size_bytes: number
  page_count: number | null
  total_chunks: number
  sections: string[]
  created_at: string
  metadata_json: Record<string, unknown>
}

export interface SearchResultItem {
  chunk_id: string
  document_id: string
  document_name: string
  page_number: number | null
  section_heading: string
  locator: string
  content: string
  rrf_score: number
}

export interface SearchResponse {
  query: string
  total_results: number
  results: SearchResultItem[]
}

export interface CitationItem {
  chunk_id: string
  document_name: string
  page_number: number | null
  section_heading: string
  locator: string
  exact_quote: string
  verified: boolean
}

export interface ChatResponse {
  session_id: string
  query: string
  intent: string
  answer: string
  citations: CitationItem[]
  compliance_status: string | null
  confidence_score: number
  human_review_required: boolean
  execution_time_ms: number
  tools_executed: string[]
}

export interface StreamEventPayload {
  stage?: string
  message?: string
  token?: string
  chunk_id?: string
  document_name?: string
  page_number?: number | null
  section_heading?: string
  locator?: string
  exact_quote?: string
  verified?: boolean
  session_id?: string
  intent?: string
  confidence_score?: number
  compliance_status?: string | null
  human_review_required?: boolean
  tools_executed?: string[]
  code?: string
}

export interface ComplianceEvidence {
  chunk_id: string
  document_id: string
  document_name: string
  source_filename?: string
  page_number: number | null
  section_heading: string
  locator: string
  quote: string
  quote_snippet?: string
  relevance_score?: number
}

export interface ComplianceFinding {
  requirement_code: string
  title: string
  category: string
  status: 'COVERED' | 'PARTIALLY_COVERED' | 'MISSING'
  confidence_score: number
  evidence: ComplianceEvidence | null
  gap: string | null
  recommendation: string | null
  human_review_required: boolean
  assurance_level: string
}

export interface CoverageSummary {
  covered: number
  partially_covered: number
  missing: number
  total: number
  compliance_percentage: number
}

export interface ComplianceEvaluationResponse {
  framework_id: string
  framework_name: string
  total_requirements: number
  coverage_summary: CoverageSummary
  findings: ComplianceFinding[]
}

export interface GapItem {
  priority_rank: number
  requirement_code: string
  title: string
  category: string
  current_status: 'PARTIALLY_COVERED' | 'MISSING'
  severity: 'Critical' | 'High' | 'Medium' | 'Low'
  identified_gap: string
  remediation_recommendation: string
  human_review_required: boolean
  estimated_effort_days: number
}

export interface GapAnalysisResponse {
  framework_id: string
  framework_name: string
  total_gaps: number
  covered_count: number
  partially_covered_count: number
  missing_count: number
  human_review_count: number
  remediation_roadmap: GapItem[]
}

export interface HistoricalDiffItem {
  requirement_id: string
  requirement_code: string
  current_status: string
  previous_status: string | null
  status_changed: boolean
  current_confidence: number
  previous_confidence: number | null
  new_evidence_found: boolean
  summary: string
}

export interface HistoricalDiffResponse {
  framework_id: string
  total_requirements: number
  diffs: HistoricalDiffItem[]
}

export interface KnowledgeNodeItem {
  id: string
  slug: string
  title: string
  node_type: string
  content_markdown: string
}

export interface KnowledgeLinkItem {
  target_slug: string
  target_title?: string | null
  link_text?: string | null
  context_snippet?: string | null
}

export interface BacklinkItem {
  source_slug: string
  source_title: string
  source_type: string
  context_snippet?: string | null
}

export interface KnowledgeNodeDetailResponse {
  root_node: KnowledgeNodeItem
  outgoing_links: KnowledgeLinkItem[]
  backlinks: BacklinkItem[]
  related_requirements: string[]
  depth: number
}

export interface BacklinksListResponse {
  target_slug: string
  total_backlinks: number
  backlinks: BacklinkItem[]
}

export interface ApiError {
  code: string
  message: string
  field?: string | null
}

export interface ApiErrorResponse {
  error: ApiError
  request_id: string
  timestamp: string
}

// Unified Aliases for Domain Components
export type ComplianceStatus = 'COVERED' | 'PARTIALLY_COVERED' | 'MISSING'
export type AssuranceTier = 'high' | 'medium' | 'low' | 'unverified'

export interface ComplianceEvaluationResult {
  requirement_id?: string
  requirement_code?: string
  code: string
  title: string
  category?: string
  description?: string
  status: ComplianceStatus
  assurance_tier: AssuranceTier
  confidence_score: number
  rationale: string
  evidence_count?: number
  primary_evidence_snippet?: string
  evidence?: ComplianceEvidence[]
}

export interface DocumentChunk {
  id?: string
  chunk_index: number
  page_number?: number
  section_heading?: string
  token_count?: number
  content: string
}

export interface Document extends DocumentItem {
  original_filename?: string
  sha256_hash?: string
  chunk_count?: number
  updated_at?: string
}

export interface DocumentDetail extends Document {
  chunks: DocumentChunk[]
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  content: string
  score: number
  section_heading?: string
  page_number?: number
  document_name?: string
  source_filename?: string
  token_count?: number
}

export interface Citation {
  document_id: string
  chunk_id: string
  source_filename?: string
  document_name?: string
  section?: string
  page_number?: number
  locator?: string
  quote?: string
  text?: string
  confidence?: number
  is_verified?: boolean
  verification_tier?: AssuranceTier
}

export interface KnowledgeEdge {
  id: string
  source_slug: string
  target_slug: string
  target_name?: string
  relation: string
  weight?: number
  evidence_chunk_id?: string
}

export interface KnowledgeNode {
  id: string
  slug: string
  name: string
  category: string
  summary?: string
  framework?: string
  confidence?: number
  metadata?: Record<string, unknown>
  forward_links?: KnowledgeEdge[]
  backlinks?: KnowledgeEdge[]
}

export interface KnowledgeBacklinksResponse {
  node_slug: string
  total_backlinks: number
  backlinks: KnowledgeEdge[]
}

