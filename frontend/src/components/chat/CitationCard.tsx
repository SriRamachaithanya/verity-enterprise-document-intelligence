import React, { useState } from 'react'
import type { Citation } from '../../api/types'
import { ShieldCheck, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'
import { AssuranceBadge } from '../common/Badge'

interface CitationCardProps {
  citation: Citation
  index: number
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, index }) => {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const docName = citation.source_filename || citation.document_name || citation.document_id
  const quoteText = citation.quote || citation.text || ''
  const locator = citation.locator || (citation.page_number ? `p. ${citation.page_number}` : citation.section || `Chunk ${citation.chunk_id}`)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (quoteText) {
      navigator.clipboard.writeText(quoteText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="bg-slate-50/90 border border-slate-200 rounded-lg p-3 text-xs space-y-2 hover:border-slate-300 transition-colors">
      {/* Top Header: Badge, Source, and Verification Tier */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 truncate">
          <span className="h-4.5 w-4.5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px] shrink-0">
            [{index + 1}]
          </span>
          <span className="font-semibold text-slate-800 truncate" title={docName}>
            {docName}
          </span>
          <span className="text-[11px] text-slate-500 bg-white border border-slate-200 px-1.5 py-0.5 rounded shrink-0">
            {locator}
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {citation.is_verified && (
            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
              <ShieldCheck className="h-3 w-3 text-emerald-600" />
              Ground Truth
            </span>
          )}
          {citation.verification_tier && (
            <AssuranceBadge tier={citation.verification_tier} />
          )}
        </div>
      </div>

      {/* Quote Preview */}
      {quoteText && (
        <div className="relative">
          <p
            className={`font-mono text-[11px] text-slate-600 bg-white p-2 rounded border border-slate-200/80 leading-relaxed italic ${
              expanded ? '' : 'line-clamp-2'
            }`}
          >
            "{quoteText}"
          </p>

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="text-[10px] text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
            >
              {expanded ? (
                <>
                  <span>Show less</span>
                  <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  <span>Show full quote</span>
                  <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleCopy}
              className="text-[10px] text-slate-400 hover:text-slate-600 flex items-center gap-1"
              title="Copy quote to clipboard"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-600" />
                  <span className="text-emerald-600">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
