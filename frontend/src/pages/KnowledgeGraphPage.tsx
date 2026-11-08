import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getKnowledgeNode } from '../services/knowledgeService'
import { GraphCanvas } from '../components/knowledge/GraphCanvas'
import { NodeDetailDrawer } from '../components/knowledge/NodeDetailDrawer'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import type { KnowledgeNode } from '../api/types'
import { Search, Info } from 'lucide-react'

const DEFAULT_NODES = [
  'logical-access-control',
  'soc2-cc6.1',
  'mfa-policy',
  'incident-response-plan',
  'iso-27001-a.9',
]

export const KnowledgeGraphPage: React.FC = () => {
  const [currentSlug, setCurrentSlug] = useState<string>('logical-access-control')
  const [searchSlug, setSearchSlug] = useState<string>('')
  const [depth, setDepth] = useState<number>(1)
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false)

  const { data: rawData, isLoading, error } = useQuery({
    queryKey: ['knowledge-node', currentSlug, depth],
    queryFn: () => getKnowledgeNode(currentSlug, depth),
    retry: 1,
  })

  const node: KnowledgeNode | null = rawData
    ? {
        id: rawData.root_node.id,
        slug: rawData.root_node.slug,
        name: rawData.root_node.title,
        category: rawData.root_node.node_type,
        summary: rawData.root_node.content_markdown,
        forward_links: rawData.outgoing_links?.map((link, idx) => ({
          id: `fw-${idx}`,
          source_slug: rawData.root_node.slug,
          target_slug: link.target_slug,
          target_name: link.target_title || link.target_slug,
          relation: link.link_text || 'relates_to',
        })),
        backlinks: rawData.backlinks?.map((back, idx) => ({
          id: `bk-${idx}`,
          source_slug: back.source_slug,
          target_slug: rawData.root_node.slug,
          target_name: back.source_title || back.source_slug,
          relation: back.source_type || 'referenced_by',
        })),
      }
    : null

  const handleNodeClick = (slug: string) => {
    setCurrentSlug(slug)
    setDrawerOpen(true)
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchSlug.trim()) {
      setCurrentSlug(searchSlug.trim().toLowerCase().replace(/\s+/g, '-'))
      setSearchSlug('')
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Knowledge Graph & Compliance Ontologies
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Traverse interconnected relationships between controls, policies, systems, and evidence chunks.
          </p>
        </div>

        {/* Node search input */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search entity slug..."
              value={searchSlug}
              onChange={(e) => setSearchSlug(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-48"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs"
          >
            Locate
          </button>
        </form>
      </div>

      {/* Suggested Entities Quick Bar */}
      <div className="flex items-center gap-2 overflow-x-auto text-xs pb-1">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider shrink-0">
          Featured Ontologies:
        </span>
        {DEFAULT_NODES.map((slug) => (
          <button
            key={slug}
            type="button"
            onClick={() => setCurrentSlug(slug)}
            className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium transition-colors shrink-0 ${
              currentSlug === slug
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {slug}
          </button>
        ))}
      </div>

      {/* Canvas Area */}
      {isLoading ? (
        <div className="py-24 bg-white rounded-2xl border border-slate-200">
          <LoadingSpinner label={`Traversing knowledge ontology for "${currentSlug}"...`} />
        </div>
      ) : error ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-3">
          <Info className="h-8 w-8 text-amber-500 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">Entity Not Found in Graph</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            The entity node <code className="font-mono text-blue-600 font-bold">{currentSlug}</code> does not currently exist in the SQLite knowledge database. Select one of the featured ontologies above.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-600 px-1">
            <span>
              Active Node: <span className="font-bold text-slate-900">{node?.name}</span> ({node?.category})
            </span>
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="text-blue-600 hover:text-blue-800 font-semibold"
            >
              Open Entity Inspector
            </button>
          </div>

          <GraphCanvas
            centerNode={node}
            depth={depth}
            onDepthChange={(newDepth) => setDepth(newDepth)}
            onNodeClick={handleNodeClick}
          />
        </div>
      )}

      {/* Node Detail Drawer */}
      <NodeDetailDrawer
        node={node}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSelectNode={(nextSlug) => {
          setCurrentSlug(nextSlug)
          setDrawerOpen(true)
        }}
      />
    </div>
  )
}
