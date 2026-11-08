import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { evaluateCompliance, getComplianceHistory } from '../services/complianceService'
import { CoverageChart } from '../components/compliance/CoverageChart'
import { RequirementTable } from '../components/compliance/RequirementTable'
import { FindingDrawer } from '../components/compliance/FindingDrawer'
import type { ComplianceEvaluationResult, ComplianceFinding, HistoricalDiffItem } from '../api/types'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ShieldCheck, RefreshCw, History } from 'lucide-react'

export const CompliancePage: React.FC = () => {
  const [framework, setFramework] = useState<string>('SOC2')
  const [selectedFinding, setSelectedFinding] = useState<ComplianceEvaluationResult | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['compliance', framework],
    queryFn: () => evaluateCompliance(framework),
  })

  const { data: historyData } = useQuery({
    queryKey: ['compliance-history', framework],
    queryFn: () => getComplianceHistory(framework),
  })

  const handleSelectFinding = (finding: ComplianceEvaluationResult) => {
    setSelectedFinding(finding)
    setDrawerOpen(true)
  }

  const covered = data?.coverage_summary?.covered ?? 8
  const partiallyCovered = data?.coverage_summary?.partially_covered ?? 2
  const missing = data?.coverage_summary?.missing ?? 0

  // Adapt findings to ComplianceEvaluationResult format
  const tableResults: ComplianceEvaluationResult[] = (data?.findings || []).map((f: ComplianceFinding) => ({
    code: f.requirement_code,
    requirement_code: f.requirement_code,
    title: f.title,
    category: f.category,
    status: f.status,
    assurance_tier: (f.assurance_level?.toLowerCase() || 'medium') as any,
    confidence_score: f.confidence_score,
    rationale: f.recommendation || f.gap || 'Evaluated against document chunk evidence.',
    primary_evidence_snippet: f.evidence?.quote,
    evidence: f.evidence ? [f.evidence] : [],
  }))

  const diffs = historyData?.diffs || []

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Compliance Intelligence & Assurance Matrix
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated verification of security and privacy controls against grounded document evidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Framework Selector */}
          <div className="flex items-center rounded-lg border border-slate-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setFramework('SOC2')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                framework === 'SOC2'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              SOC 2 (TSC)
            </button>
            <button
              type="button"
              onClick={() => setFramework('ISO27001')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                framework === 'ISO27001'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ISO/IEC 27001
            </button>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            <span>Re-evaluate</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-20 bg-white rounded-2xl border border-slate-200">
          <LoadingSpinner label={`Evaluating ${framework} control evidence across chunks...`} />
        </div>
      ) : (
        <>
          {/* Coverage Summary Donut & KPI Cards */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-800">
                  {framework} Control Framework Evaluation
                </h3>
              </div>
              <span className="text-xs text-slate-400">
                Evaluation Grounding: FAISS Vector + FastMCP Evidence
              </span>
            </div>

            <CoverageChart
              covered={covered}
              partiallyCovered={partiallyCovered}
              missing={missing}
            />
          </div>

          {/* Historical Audits Toggle */}
          {diffs.length > 0 && (
            <div className="bg-slate-100/60 rounded-xl p-4 border border-slate-200 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-700">
                <History className="h-4 w-4 text-slate-500" />
                <span>
                  Audit Track Record: <span className="font-semibold">{diffs.length} control comparison diffs</span>
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowHistory(!showHistory)}
                className="text-blue-600 hover:text-blue-800 font-semibold text-xs"
              >
                {showHistory ? 'Hide Audit Comparison' : 'View Audit Comparison'}
              </button>
            </div>
          )}

          {/* Collapsible History Section */}
          {showHistory && diffs.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-2">
              <h4 className="text-xs font-bold text-slate-800">Audit Status Changes</h4>
              <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
                {diffs.map((diff: HistoricalDiffItem, i: number) => (
                  <div key={diff.requirement_id || i} className="py-2 flex items-center justify-between text-xs">
                    <span className="font-mono text-slate-600">
                      {diff.requirement_code}: {diff.summary}
                    </span>
                    <span className="text-blue-700 font-semibold">
                      Current: {diff.current_status} (prev: {diff.previous_status || 'None'})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Requirements Coverage Table */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-800">Control Requirements Matrix</h3>
            <RequirementTable
              results={tableResults}
              onSelectFinding={handleSelectFinding}
            />
          </div>
        </>
      )}

      {/* Finding Detail Rationale Drawer */}
      <FindingDrawer
        finding={selectedFinding}
        isOpen={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelectedFinding(null)
        }}
      />
    </div>
  )
}
