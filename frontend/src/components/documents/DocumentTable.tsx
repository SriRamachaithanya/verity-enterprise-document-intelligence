import React, { useState } from 'react'
import type { DocumentItem } from '../../api/types'
import { FileText, Trash2, Eye, Search } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { deleteDocument } from '../../services/documentService'
import { EmptyState } from '../common/EmptyState'

interface DocumentTableProps {
  documents: DocumentItem[]
  isLoading?: boolean
  onRefresh: () => void
  onSelectDocument: (docId: string) => void
}

export const DocumentTable: React.FC<DocumentTableProps> = ({
  documents,
  onRefresh,
  onSelectDocument,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const { hasRole } = useAuth()
  const { showToast } = useToast()

  const canDelete = hasRole(['admin'])

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleDelete = async (doc: DocumentItem) => {
    if (!window.confirm(`Are you sure you want to permanently delete "${doc.filename}" and its vector indices?`)) {
      return
    }

    try {
      setDeletingId(doc.id)
      await deleteDocument(doc.id)
      showToast('success', `Document "${doc.filename}" deleted successfully.`)
      onRefresh()
    } catch (err: any) {
      showToast('error', err?.response?.data?.message || err.message || 'Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Table Toolbar */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Filter ingested documents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>

        <div className="text-xs text-slate-500">
          Showing <span className="font-semibold text-slate-800">{filteredDocs.length}</span> of{' '}
          <span className="font-semibold text-slate-800">{documents.length}</span> documents
        </div>
      </div>

      {/* Table or Empty State */}
      {filteredDocs.length === 0 ? (
        <div className="py-12">
          <EmptyState
            title={searchTerm ? 'No matching documents' : 'No documents in repository'}
            description={
              searchTerm
                ? `No documents matched "${searchTerm}". Try a different search term.`
                : 'Upload policy standards, architecture specifications, or compliance reports above.'
            }
          />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Document</th>
                <th className="py-3 px-4">Format</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Pages</th>
                <th className="py-3 px-4">Ingested Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredDocs.map((doc) => {
                const displayName = doc.filename
                const isDeleting = deletingId === doc.id
                const ext = displayName.split('.').pop()?.toUpperCase() || 'DOC'

                return (
                  <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                          <FileText className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-800 truncate max-w-xs md:max-w-md">
                            {displayName}
                          </p>
                          <p className="text-[10px] text-slate-400 font-mono truncate">
                            ID: {doc.id}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                        {ext}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-700">
                      {doc.page_count ?? 'N/A'}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => onSelectDocument(doc.id)}
                          className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                          title="View Document Details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {canDelete && (
                          <button
                            type="button"
                            disabled={isDeleting}
                            onClick={() => handleDelete(doc)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors disabled:opacity-50"
                            title="Delete Document (Admin only)"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
