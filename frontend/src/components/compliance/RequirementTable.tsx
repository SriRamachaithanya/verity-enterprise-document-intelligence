import React, { useState } from 'react'
import type { ComplianceEvaluationResult } from '../../api/types'
import { ComplianceBadge, AssuranceBadge } from '../common/Badge'
import { Search, ChevronRight } from 'lucide-react'
import { EmptyState } from '../common/EmptyState'

interface RequirementTableProps {
  results: ComplianceEvaluationResult[]
  onSelectFinding: (finding: ComplianceEvaluationResult) => void
}

export const RequirementTable: React.FC<RequirementTableProps> = ({
  results,
  onSelectFinding,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  const filtered = results.filter((item) => {
    const matchesSearch =
      item.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.title.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus =
      statusFilter === 'ALL' || item.status.toUpperCase() === statusFilter.toUpperCase()
    return matchesSearch && matchesStatus
  })

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Table Toolbar */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search code or requirement..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="ALL">All Statuses</option>
              <option value="COVERED">Covered</option>
              <option value="PARTIALLY_COVERED">Partially Covered</option>
              <option value="MISSING">Missing Evidence</option>
            </select>
          </div>
        </div>

        <div className="text-xs text-slate-500">
          Showing <span className="font-semibold text-slate-800">{filtered.length}</span> of{' '}
          <span className="font-semibold text-slate-800">{results.length}</span> requirements
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="py-12">
          <EmptyState
            title="No matching requirements"
            description="Adjust your search criteria or status filter to see compliance requirements."
          />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Code</th>
                <th className="py-3 px-4">Title & Scope</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Assurance Tier</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((item) => (
                <tr
                  key={item.requirement_id || item.code}
                  onClick={() => onSelectFinding(item)}
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                >
                  <td className="py-3 px-4">
                    <span className="font-mono font-bold text-blue-700 bg-blue-50 border border-blue-200/80 px-2 py-0.5 rounded text-[11px]">
                      {item.code}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="max-w-md">
                      <p className="font-semibold text-slate-800 group-hover:text-blue-600 transition-colors truncate">
                        {item.title}
                      </p>
                      {item.primary_evidence_snippet && (
                        <p className="text-[11px] text-slate-500 truncate italic mt-0.5">
                          "{item.primary_evidence_snippet}"
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <ComplianceBadge status={item.status} />
                  </td>
                  <td className="py-3 px-4">
                    <AssuranceBadge tier={item.assurance_tier} />
                  </td>
                  <td className="py-3 px-4 text-slate-600 font-medium">
                    {(item.confidence_score * 100).toFixed(0)}%
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="inline-flex items-center text-slate-400 group-hover:text-blue-600 text-xs font-medium">
                      Rationale <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
