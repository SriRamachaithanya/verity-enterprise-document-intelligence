import React, { useMemo } from 'react'
import type { KnowledgeNode } from '../../api/types'

interface GraphCanvasProps {
  centerNode: KnowledgeNode | null
  onNodeClick: (slug: string) => void
  depth: number
  onDepthChange: (depth: number) => void
}

interface GraphItem {
  id: string
  name: string
  slug: string
  type: 'center' | 'forward' | 'backlink'
  relation?: string
  x: number
  y: number
}

interface GraphLink {
  source: GraphItem
  target: GraphItem
  relation: string
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  centerNode,
  onNodeClick,
  depth,
  onDepthChange,
}) => {
  const width = 800
  const height = 500
  const centerX = width / 2
  const centerY = height / 2

  const { nodes, links } = useMemo(() => {
    if (!centerNode) return { nodes: [], links: [] }

    const centerItem: GraphItem = {
      id: centerNode.slug,
      name: centerNode.name,
      slug: centerNode.slug,
      type: 'center',
      x: centerX,
      y: centerY,
    }

    const calculatedNodes: GraphItem[] = [centerItem]
    const calculatedLinks: GraphLink[] = []

    const forward = centerNode.forward_links || []
    const back = centerNode.backlinks || []

    const radius = 180

    // Arrange forward links on right semicircle, backlinks on left semicircle
    forward.forEach((edge, idx) => {
      const angle = -Math.PI / 2 + ((idx + 0.5) / (forward.length || 1)) * Math.PI
      const x = centerX + radius * Math.cos(angle)
      const y = centerY + radius * Math.sin(angle)
      const item: GraphItem = {
        id: edge.target_slug,
        name: edge.target_name || edge.target_slug,
        slug: edge.target_slug,
        type: 'forward',
        relation: edge.relation,
        x,
        y,
      }
      calculatedNodes.push(item)
      calculatedLinks.push({
        source: centerItem,
        target: item,
        relation: edge.relation,
      })
    })

    back.forEach((edge, idx) => {
      const angle = Math.PI / 2 + ((idx + 0.5) / (back.length || 1)) * Math.PI
      const x = centerX + radius * Math.cos(angle)
      const y = centerY + radius * Math.sin(angle)
      const item: GraphItem = {
        id: edge.source_slug,
        name: edge.source_slug,
        slug: edge.source_slug,
        type: 'backlink',
        relation: edge.relation,
        x,
        y,
      }
      calculatedNodes.push(item)
      calculatedLinks.push({
        source: item,
        target: centerItem,
        relation: edge.relation,
      })
    })

    return { nodes: calculatedNodes, links: calculatedLinks }
  }, [centerNode, centerX, centerY])

  return (
    <div className="relative bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-inner">
      {/* Canvas Controls Header */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-slate-800/90 backdrop-blur-xs px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
        <span className="text-slate-400 font-medium">Traversal Depth:</span>
        {[1, 2, 3].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => onDepthChange(d)}
            className={`px-2 py-0.5 rounded font-semibold text-xs transition-colors ${
              depth === d
                ? 'bg-blue-600 text-white'
                : 'text-slate-300 hover:bg-slate-700'
            }`}
          >
            Level {d}
          </button>
        ))}
      </div>

      <div className="absolute top-4 right-4 z-10 flex items-center gap-3 bg-slate-800/90 backdrop-blur-xs px-3 py-1.5 rounded-lg border border-slate-700 text-[11px] text-slate-300">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Focus Node
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Forward Links
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-purple-500" /> Backlinks
        </span>
      </div>

      {/* SVG Interactive Canvas */}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-[520px] select-none cursor-default"
      >
        <defs>
          <marker
            id="arrowhead-forward"
            markerWidth="10"
            markerHeight="7"
            refX="28"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#10B981" />
          </marker>
          <marker
            id="arrowhead-backlink"
            markerWidth="10"
            markerHeight="7"
            refX="28"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#8B5CF6" />
          </marker>
        </defs>

        {/* Links */}
        {links.map((link, idx) => {
          const isForward = link.source.type === 'center'
          const strokeColor = isForward ? '#10B981' : '#8B5CF6'
          const midX = (link.source.x + link.target.x) / 2
          const midY = (link.source.y + link.target.y) / 2

          return (
            <g key={idx}>
              <line
                x1={link.source.x}
                y1={link.source.y}
                x2={link.target.x}
                y2={link.target.y}
                stroke={strokeColor}
                strokeWidth="1.5"
                strokeOpacity="0.6"
                strokeDasharray={isForward ? undefined : '4 2'}
                markerEnd={isForward ? 'url(#arrowhead-forward)' : 'url(#arrowhead-backlink)'}
              />
              <text
                x={midX}
                y={midY - 4}
                fill="#94A3B8"
                fontSize="10"
                textAnchor="middle"
                className="font-mono bg-slate-900"
              >
                {link.relation}
              </text>
            </g>
          )
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const isCenter = node.type === 'center'
          const isForward = node.type === 'forward'

          const fill = isCenter
            ? '#2563EB' // Blue 600
            : isForward
            ? '#059669' // Emerald 600
            : '#7C3AED' // Purple 600

          return (
            <g
              key={node.id}
              onClick={() => onNodeClick(node.slug)}
              className="cursor-pointer group"
              transform={`translate(${node.x}, ${node.y})`}
            >
              <circle
                r={isCenter ? 26 : 20}
                fill={fill}
                stroke="#1E293B"
                strokeWidth="3"
                className="transition-transform group-hover:scale-125"
              />
              <text
                y={isCenter ? 40 : 32}
                fill="#F8FAFC"
                fontSize={isCenter ? '12' : '11'}
                fontWeight={isCenter ? 'bold' : 'normal'}
                textAnchor="middle"
                className="pointer-events-none drop-shadow-md"
              >
                {node.name.length > 22 ? `${node.name.slice(0, 20)}...` : node.name}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
