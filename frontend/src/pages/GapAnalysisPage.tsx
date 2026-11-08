import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getGapAnalysis } from '../services/complianceService'
import { SeverityBadge } from '../components/common/Badge'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { EmptyState } from '../components/common/EmptyState'
import type { GapItem } from '../api/types'
import { ArrowRight } from 'lucide-react'

export const GapAnalysisPage: React.FC = () => {
  const [framework, setFramework] = useState<string>('SOC2')

  const { data, isLoading } = useQuery({
    queryKey: ['gap-analysis', framework],
    queryFn: () => getGapAnalysis(framework),
  })

  const gaps = data?.remediation_roadmap || []

  const criticalCount = gaps.filter((g: GapItem) => g.severity.toLowerCase() === 'critical').length
  const highCount = gaps.filter((g: GapItem) => g.severity.toLowerCase() === 'high').length
  const mediumCount = gaps.filter((g: GapItem) => g.severity.toLowerCase() === 'medium').length
  const lowCount = gaps.filter((g: GapItem) => g.severity.toLowerCase() === 'low').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Audit Gap Analysis & Risk Exposure
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Prioritized identification of missing controls, ungrounded policies, and audit non-compliance risks.
          </p>
        </div>

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
            SOC 2
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
            ISO 27001
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-20 bg-white rounded-2xl border border-slate-200">
          <LoadingSpinner label={`Conducting gap analysis for ${framework}...`} />
        </div>
      ) : (
        <>
          {/* Severity Counters Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-rose-200 bg-rose-50/20 shadow-xs space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-rose-600">
                Critical Severity
              </span>
              <p className="text-2xl font-black text-rose-700">{criticalCount}</p>
              <p className="text-[11px] text-slate-500">Requires immediate attention</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/20 shadow-xs space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600">
                High Severity
              </span>
              <p className="text-2xl font-black text-amber-700">{highCount}</p>
              <p className="text-[11px] text-slate-500">Key controls missing</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-blue-200 bg-blue-50/20 shadow-xs space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600">
                Medium Severity
              </span>
              <p className="text-2xl font-black text-blue-700">{mediumCount}</p>
              <p className="text-[11px] text-slate-500">Partial evidence found</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                Low Severity
              </span>
              <p className="text-2xl font-black text-slate-700">{lowCount}</p>
              <p className="text-[11px] text-slate-500">Minor policy updates</p>
            </div>
          </div>

          {/* Gaps List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800">
                Identified Compliance Gaps ({gaps.length})
              </h3>
              <Link
                to="/remediation"
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                View Remediation Roadmap <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {gaps.length > 0 ? (
              <div className="space-y-3">
                {gaps.map((gap: GapItem) => (
                  <div
                    key={gap.requirement_code}
                    className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-colors space-y-3"
                  >
                    {/* Top Row: Code, Severity, Title */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                          {gap.requirement_code}
                        </span>
                        <h4 className="font-bold text-slate-800 text-sm">{gap.title}</h4>
                      </div>
                      <SeverityBadge severity={gap.severity} />
                    </div>

                    {/* Gap Description */}
                    <p className="text-xs text-slate-600 leading-relaxed">{gap.identified_gap}</p>

                    {/* Remediation Summary Box */}
                    {gap.remediation_recommendation && (
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-700 space-y-1">
                        <span className="font-semibold text-slate-800">Remediation Guidance:</span>
                        <p>{gap.remediation_recommendation}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-16 bg-white rounded-2xl border border-slate-200">
                <EmptyState
                  title="No compliance gaps detected"
                  description={`All requirements under ${framework} have verified supporting evidence in the repository.`}
                />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
