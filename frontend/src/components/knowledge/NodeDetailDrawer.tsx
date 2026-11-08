import React from 'react'
import type { KnowledgeNode } from '../../api/types'
import { X, ArrowRight, ArrowLeft, ExternalLink } from 'lucide-react'

interface NodeDetailDrawerProps {
  node: KnowledgeNode | null
  isOpen: boolean
  onClose: () => void
  onSelectNode: (slug: string) => void
}

export const NodeDetailDrawer: React.FC<NodeDetailDrawerProps> = ({
  node,
  isOpen,
  onClose,
  onSelectNode,
}) => {
  if (!isOpen || !node) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 pl-10 max-w-full flex">
        <div className="w-screen max-w-lg bg-white shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50/50">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                  {node.category || 'Entity'}
                </span>
                {node.framework && (
                  <span className="text-[11px] font-semibold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded">
                    {node.framework}
                  </span>
                )}
              </div>
              <h3 className="text-base font-bold text-slate-800">{node.name}</h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">slug: {node.slug}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Summary */}
            {node.summary && (
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Entity Overview
                </h4>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed">
                  {node.summary}
                </div>
              </div>
            )}

            {/* Outgoing Forward Links */}
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <ArrowRight className="h-3.5 w-3.5 text-blue-600" />
                Outgoing Relationships ({node.forward_links?.length || 0})
              </h4>

              {node.forward_links && node.forward_links.length > 0 ? (
                <div className="space-y-2">
                  {node.forward_links.map((edge) => (
                    <div
                      key={edge.id}
                      onClick={() => onSelectNode(edge.target_slug)}
                      className="p-3 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 cursor-pointer transition-all flex items-center justify-between text-xs group"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] uppercase font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                          {edge.relation}
                        </span>
                        <span className="font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">
                          {edge.target_name || edge.target_slug}
                        </span>
                      </div>
                      <ExternalLink className="h-3.5 w-3.5 text-slate-400 group-hover:text-blue-600" />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No outgoing connections.</p>
              )}
            </div>

            {/* Backlinks */}
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <ArrowLeft className="h-3.5 w-3.5 text-purple-600" />
                Inbound Backlinks ({node.backlinks?.length || 0})
              </h4>

              {node.backlinks && node.backlinks.length > 0 ? (
                <div className="space-y-2">
                  {node.backlinks.map((edge) => (
                    <div
                      key={edge.id}
                      onClick={() => onSelectNode(edge.source_slug)}
                      className="p-3 rounded-lg border border-slate-200 hover:border-purple-300 hover:bg-purple-50/40 cursor-pointer transition-all flex items-center justify-between text-xs group"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-800 group-hover:text-purple-600 transition-colors">
                          {edge.source_slug}
                        </span>
                        <span className="font-mono text-[10px] uppercase font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                          {edge.relation}
                        </span>
                      </div>
                      <ExternalLink className="h-3.5 w-3.5 text-slate-400 group-hover:text-purple-600" />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No inbound backlinks.</p>
              )}
            </div>

            {/* Entity Metadata */}
            {node.metadata && Object.keys(node.metadata).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Raw Attributes
                </h4>
                <pre className="bg-slate-900 text-slate-200 p-3 rounded-lg text-[11px] font-mono overflow-x-auto">
                  {JSON.stringify(node.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
