import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { UploadZone } from '../components/documents/UploadZone'
import { DocumentTable } from '../components/documents/DocumentTable'
import { DocumentDetailModal } from '../components/documents/DocumentDetailModal'
import { getDocuments } from '../services/documentService'
import { LoadingSpinner } from '../components/common/LoadingSpinner'

export const DocumentsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: () => getDocuments(100, 0),
  })

  const handleSelectDocument = (docId: string) => {
    setSelectedDocId(docId)
    setIsModalOpen(true)
  }

  const handleUploadSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
    refetch()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Document Repository & Parsing Pipeline
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Ingest enterprise compliance artifacts, policies, and audit documentation for vector and full-text indexing.
        </p>
      </div>

      {/* Upload Zone */}
      <UploadZone onUploadSuccess={handleUploadSuccess} />

      {/* Documents List */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-slate-800">
            Ingested Documents ({data?.total_count || 0})
          </h2>
        </div>

        {isLoading ? (
          <div className="py-12 bg-white rounded-xl border border-slate-200">
            <LoadingSpinner label="Loading document repository..." />
          </div>
        ) : (
          <DocumentTable
            documents={data?.documents || []}
            isLoading={isLoading}
            onRefresh={() => refetch()}
            onSelectDocument={handleSelectDocument}
          />
        )}
      </div>

      {/* Document Detail Modal */}
      <DocumentDetailModal
        documentId={selectedDocId}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedDocId(null)
        }}
      />
    </div>
  )
}

