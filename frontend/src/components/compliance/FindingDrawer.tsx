import React from 'react'
import type { ComplianceEvaluationResult, ComplianceEvidence } from '../../api/types'
import { X, ShieldCheck, FileText, CheckCircle2, AlertTriangle } from 'lucide-react'
import { ComplianceBadge, AssuranceBadge } from '../common/Badge'

interface FindingDrawerProps {
  finding: ComplianceEvaluationResult | null
  isOpen: boolean
  onClose: () => void
}

export const FindingDrawer: React.FC<FindingDrawerProps> = ({ finding, isOpen, onClose }) => {
  if (!isOpen || !finding) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 pl-10 max-w-full flex">
        <div className="w-screen max-w-xl bg-white shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50/50">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-bold text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                  {finding.code}
                </span>
                <ComplianceBadge status={finding.status} />
                <AssuranceBadge tier={finding.assurance_tier} />
              </div>
              <h3 className="text-base font-bold text-slate-800 leading-snug">{finding.title}</h3>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Requirement Description if available */}
            {finding.description && (
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Requirement Scope
                </h4>
                <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 text-xs text-slate-700 leading-relaxed">
                  {finding.description}
                </div>
              </div>
            )}

            {/* AI Evaluator Rationale */}
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Evaluation Rationale & Assurance Logic
              </h4>
              <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100 text-xs text-slate-800 leading-relaxed space-y-2">
                <p className="whitespace-pre-wrap">{finding.rationale}</p>
                <div className="pt-2 border-t border-blue-200/50 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Grounding Confidence Score</span>
                  <span className="font-bold text-blue-700">
                    {(finding.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Primary Evidence Snippet */}
            {finding.primary_evidence_snippet && (
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  Primary Verbatim Evidence
                </h4>
                <div className="bg-slate-900 text-slate-100 p-4 rounded-xl font-mono text-xs leading-relaxed border border-slate-800 italic select-all">
                  "{finding.primary_evidence_snippet}"
                </div>
              </div>
            )}

            {/* Mapped Evidence Items */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Mapped Document Evidence ({finding.evidence?.length || 0})
                </h4>
              </div>

              {finding.evidence && finding.evidence.length > 0 ? (
                <div className="space-y-3">
                  {finding.evidence.map((ev: ComplianceEvidence, i: number) => (
                    <div
                      key={ev.chunk_id || i}
                      className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 truncate">
                          <FileText className="h-4 w-4 text-blue-600 shrink-0" />
                          <span className="font-semibold text-slate-800 truncate">
                            {ev.source_filename || ev.document_name || ev.document_id}
                          </span>
                        </div>
                        <span className="text-[10px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                          {ev.section_heading || (ev.page_number ? `p. ${ev.page_number}` : 'Section')}
                        </span>
                      </div>

                      <p className="font-mono text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100 leading-relaxed italic">
                        "{ev.quote_snippet || ev.quote}"
                      </p>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                        <span className="flex items-center gap-1 text-emerald-600">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          FAISS Vector Similarity: {((ev.relevance_score || 0.95) * 100).toFixed(0)}%
                        </span>
                        <span className="text-slate-400 font-mono text-[10px]">
                          Chunk ID: {ev.chunk_id}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center bg-slate-50 border border-slate-200 rounded-xl text-slate-500 text-xs">
                  <AlertTriangle className="h-6 w-6 text-amber-500 mx-auto mb-2" />
                  No direct document chunks mapped to this requirement yet.
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              Close Drawer
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
