import React, { useState, useRef } from 'react'
import { UploadCloud, CheckCircle2, AlertTriangle, FileText, X } from 'lucide-react'
import { uploadDocument } from '../../services/documentService'
import type { DocumentUploadResponse } from '../../api/types'
import { useToast } from '../../context/ToastContext'

interface UploadZoneProps {
  onUploadSuccess: (response: DocumentUploadResponse) => void
}

const MAX_SIZE_BYTES = 25 * 1024 * 1024 // 25 MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [lastUploadResult, setLastUploadResult] = useState<DocumentUploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const { showToast } = useToast()

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported file format '${ext}'. VERITY supports PDF, DOCX, and TXT.`
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the 25 MB limit.`
    }
    return null
  }

  const handleFile = (file: File) => {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      setSelectedFile(null)
      showToast('error', validationError)
      return
    }
    setError(null)
    setSelectedFile(file)
    setLastUploadResult(null)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    setIsUploading(true)
    setUploadProgress(20)
    setError(null)

    try {
      const timer = setInterval(() => {
        setUploadProgress((prev) => (prev < 80 ? prev + 15 : prev))
      }, 300)

      const result = await uploadDocument(selectedFile)
      clearInterval(timer)
      setUploadProgress(100)

      setLastUploadResult(result)
      setSelectedFile(null)
      showToast('success', `Document "${result.filename}" successfully parsed into ${result.chunks_count} chunks.`)
      onUploadSuccess(result)
    } catch (err: any) {
      const errMsg = err?.response?.data?.message || err.message || 'Upload failed'
      setError(errMsg)
      showToast('error', errMsg)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Secure Document Ingestion</h3>
          <p className="text-xs text-slate-500">
            Upload enterprise documents for automatic malware scanning, parsing, chunking, and FAISS vector indexing.
          </p>
        </div>
        <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md font-medium">
          PDF, DOCX, TXT up to 25 MB
        </span>
      </div>

      {/* Drag & Drop Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-blue-500 bg-blue-50/50 scale-[0.99]'
            : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50/50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFile(e.target.files[0])
            }
          }}
        />

        <div className="flex flex-col items-center justify-center gap-3">
          <div className="h-12 w-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
            <UploadCloud className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700">
              Drag and drop your file here, or{' '}
              <span className="text-blue-600 hover:underline">browse files</span>
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Supports single file uploads with automatic virus scanning and SHA-256 deduplication.
            </p>
          </div>
        </div>
      </div>

      {/* Selected file preview */}
      {selectedFile && (
        <div className="mt-4 p-4 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="h-10 w-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div className="truncate">
              <p className="text-sm font-semibold text-slate-800 truncate">{selectedFile.name}</p>
              <p className="text-xs text-slate-500">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || 'Text/Document'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              disabled={isUploading}
              onClick={(e) => {
                e.stopPropagation()
                setSelectedFile(null)
              }}
              className="text-slate-400 hover:text-slate-600 p-1"
            >
              <X className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={isUploading}
              onClick={(e) => {
                e.stopPropagation()
                handleUpload()
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <div className="h-3 w-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <span>Ingest Document</span>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {isUploading && (
        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-xs text-slate-600">
            <span>Parsing, extracting sections, and generating embeddings...</span>
            <span className="font-semibold">{uploadProgress}%</span>
          </div>
          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300 rounded-full"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Success & Malware Scan Result Details */}
      {lastUploadResult && (
        <div className="mt-4 p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs space-y-2">
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Ingestion Complete: {lastUploadResult.filename}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-emerald-900/80 pt-1 border-t border-emerald-200/60">
            <div>
              <span className="text-emerald-700 font-medium">Chunks:</span> {lastUploadResult.chunks_count}
            </div>
            <div>
              <span className="text-emerald-700 font-medium">Size:</span> {(lastUploadResult.file_size_bytes / 1024).toFixed(1)} KB
            </div>
            <div>
              <span className="text-emerald-700 font-medium">Security:</span> Clean ({lastUploadResult.malware_scan?.engine || 'Verified'})
            </div>
            <div className="truncate" title={lastUploadResult.file_hash}>
              <span className="text-emerald-700 font-medium">SHA:</span> {lastUploadResult.file_hash?.slice(0, 10)}...
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
