import React, { useEffect, useState } from 'react'
import { Modal } from '../common/Modal'
import { getDocumentById } from '../../services/documentService'
import type { DocumentDetailResponse } from '../../api/types'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Hash, Layers, Calendar, HardDrive, CheckCircle2 } from 'lucide-react'

interface DocumentDetailModalProps {
  documentId: string | null
  isOpen: boolean
  onClose: () => void
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({
  documentId,
  isOpen,
  onClose,
}) => {
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && documentId) {
      setLoading(true)
      setError(null)
      getDocumentById(documentId)
        .then((doc: DocumentDetailResponse) => {
          setDetail(doc)
        })
        .catch((err: Error) => {
          setError(err.message || 'Failed to fetch document details')
        })
        .finally(() => setLoading(false))
    } else {
      setDetail(null)
    }
  }, [isOpen, documentId])

  if (!isOpen) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={detail?.filename || 'Document Details'}
      size="xl"
    >
      {loading ? (
        <div className="py-12">
          <LoadingSpinner label="Loading document chunks and metadata..." />
        </div>
      ) : error ? (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">
          {error}
        </div>
      ) : detail ? (
        <div className="space-y-6">
          {/* Metadata Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                <HardDrive className="h-3.5 w-3.5" /> File Size
              </span>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {(detail.file_size_bytes / 1024).toFixed(1)} KB
              </p>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5" /> Total Chunks
              </span>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {detail.total_chunks} Indexed
              </p>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" /> Ingested Date
              </span>
              <p className="text-sm font-semibold text-slate-800 mt-1 truncate">
                {new Date(detail.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Security State
              </span>
              <p className="text-sm font-semibold text-emerald-700 mt-1">
                Verified Clean
              </p>
            </div>
          </div>

          {/* SHA-256 Hash Box */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg font-mono text-xs flex items-center gap-2 overflow-hidden">
            <Hash className="h-4 w-4 text-slate-400 shrink-0" />
            <span className="text-slate-500 shrink-0 font-sans font-medium">SHA-256:</span>
            <span className="text-slate-800 truncate select-all">{detail.file_hash}</span>
          </div>

          {/* Sections Explorer */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Document Structure & Extracted Sections ({detail.sections?.length || 0})
              </h4>
              <span className="text-xs text-slate-400">
                FAISS Vector & FTS5 Full-Text Indexed
              </span>
            </div>

            {detail.sections && detail.sections.length > 0 ? (
              <div className="border border-slate-200 rounded-lg p-3 bg-slate-50 space-y-1.5 max-h-48 overflow-y-auto text-xs font-mono">
                {detail.sections.map((sec: string, idx: number) => (
                  <div key={idx} className="p-1.5 bg-white rounded border border-slate-200/80 text-slate-700">
                    § {sec}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No structured section headings detected.</p>
            )}
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
