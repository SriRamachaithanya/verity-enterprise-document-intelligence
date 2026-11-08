import React, { useState } from 'react'
import { Search, FileText, AlertCircle, Copy, Check } from 'lucide-react'
import { search } from '../services/searchService'
import type { SearchResultItem } from '../api/types'
import { EmptyState } from '../components/common/EmptyState'
import { LoadingSpinner } from '../components/common/LoadingSpinner'

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(10)
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!query.trim()) return

    setIsLoading(true)
    setError(null)
    setHasSearched(true)

    try {
      const resp = await search({ query: query.trim(), limit })
      setResults(resp.results || [])
    } catch (err: any) {
      setError(err?.response?.data?.message || err.message || 'Search execution failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopySnippet = (id: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Intelligent Hybrid Search
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Reciprocal Rank Fusion (RRF) combining dense FAISS vector embeddings and sparse SQLite FTS5 full-text indexing.
        </p>
      </div>

      {/* Search Input Box */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search across policies, access controls, retention rules, or architecture..."
              className="w-full pl-10 pr-4 py-2.5 text-xs text-slate-800 placeholder-slate-400 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-700 focus:outline-none"
            >
              <option value={5}>Top 5 chunks</option>
              <option value={10}>Top 10 chunks</option>
              <option value={20}>Top 20 chunks</option>
            </select>

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {isLoading ? (
                <>
                  <div className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <span>Run Search</span>
              )}
            </button>
          </div>
        </form>

        <div className="text-[11px] text-slate-400 flex items-center gap-1">
          <span className="font-semibold text-slate-600">Note:</span> RRF scores are normalized relative rank indicators across vector & keyword retrieval, not calibrated confidence probabilities.
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Results List */}
      {isLoading ? (
        <div className="py-16 bg-white rounded-2xl border border-slate-200">
          <LoadingSpinner label="Running hybrid fusion search..." />
        </div>
      ) : hasSearched && results.length === 0 ? (
        <div className="py-16 bg-white rounded-2xl border border-slate-200">
          <EmptyState
            title="No relevant chunks discovered"
            description={`No document passages matched the query "${query}". Try alternative compliance keywords.`}
          />
        </div>
      ) : (
        results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500 px-1">
              <span>
                Found <span className="font-semibold text-slate-800">{results.length}</span> matching chunks
              </span>
              <span>Sorted by RRF Fusion Score</span>
            </div>

            <div className="space-y-3">
              {results.map((res: SearchResultItem, index: number) => {
                const docName = res.document_name || res.document_id
                const isCopied = copiedId === res.chunk_id

                return (
                  <div
                    key={res.chunk_id || index}
                    className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-colors space-y-3"
                  >
                    {/* Header: Score, Doc Name, Locator */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 truncate">
                        <span className="h-5 w-5 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs shrink-0">
                          #{index + 1}
                        </span>
                        <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                        <span className="font-bold text-slate-800 text-xs truncate">
                          {docName}
                        </span>
                        {res.section_heading && (
                          <span className="text-[10px] font-medium bg-slate-100 text-slate-700 px-2 py-0.5 rounded truncate">
                            Section: {res.section_heading}
                          </span>
                        )}
                        {res.page_number && (
                          <span className="text-[10px] font-medium bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded shrink-0">
                            p. {res.page_number}
                          </span>
                        )}
                      </div>

                      {/* RRF Relevance Score Pill */}
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full" title="RRF Score represents rank combination from FAISS & FTS5">
                          RRF Rank Score: {(res.rrf_score * 100).toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {/* Verbatim Snippet */}
                    <div className="relative">
                      <pre className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 text-xs font-mono text-slate-800 whitespace-pre-wrap leading-relaxed select-all">
                        {res.content}
                      </pre>
                      <button
                        type="button"
                        onClick={() => handleCopySnippet(res.chunk_id, res.content)}
                        className="absolute top-2 right-2 p-1.5 rounded-md bg-white/90 border border-slate-200 hover:bg-slate-100 text-slate-500 transition-colors text-xs flex items-center gap-1 shadow-xs"
                        title="Copy verbatim passage"
                      >
                        {isCopied ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-600" />
                            <span className="text-[10px] text-emerald-600 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span className="text-[10px]">Copy</span>
                          </>
                        )}
                      </button>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>Chunk ID: {res.chunk_id}</span>
                      <span>Locator: {res.locator}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      )}
    </div>
  )
}
