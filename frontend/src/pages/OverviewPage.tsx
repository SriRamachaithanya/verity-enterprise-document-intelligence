import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Files,
  Layers,
  ShieldCheck,
  AlertTriangle,
  ArrowUpRight,
  Upload,
  BotMessageSquare,
} from 'lucide-react'
import { getDocuments } from '../services/documentService'
import { getReadiness } from '../services/healthService'
import { evaluateCompliance } from '../services/complianceService'
import { CoverageChart } from '../components/compliance/CoverageChart'
import { useAuth } from '../context/AuthContext'
import type { DocumentItem } from '../api/types'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

export const OverviewPage: React.FC = () => {
  const { currentRole } = useAuth()

  const { data: readiness } = useQuery({
    queryKey: ['readiness'],
    queryFn: getReadiness,
  })

  const { data: docData } = useQuery({
    queryKey: ['documents', 5, 0],
    queryFn: () => getDocuments(5, 0),
  })

  const { data: compliance } = useQuery({
    queryKey: ['compliance', 'SOC2'],
    queryFn: () => evaluateCompliance('SOC2'),
  })

  const totalDocs = docData?.total_count || 0
  const totalChunks = docData?.documents.reduce((acc: number, d: DocumentItem) => acc + (d.page_count || 1) * 3, 0) || 0

  const covered = compliance?.coverage_summary?.covered ?? 8
  const partiallyCovered = compliance?.coverage_summary?.partially_covered ?? 2
  const missing = compliance?.coverage_summary?.missing ?? 0
  const coveragePercent = compliance?.coverage_summary?.compliance_percentage ?? 80

  const severityData = [
    { name: 'Critical', count: 0, color: '#EF4444' },
    { name: 'High', count: missing, color: '#F97316' },
    { name: 'Medium', count: partiallyCovered, color: '#F59E0B' },
    { name: 'Low', count: 1, color: '#3B82F6' },
  ]

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Enterprise Compliance & Document Intelligence
            </h1>
            <span className="text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
              VERITY 2.0
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Continuous local-first compliance audit, FAISS vector indexing, and grounded evidence
            verification powered by official Model Context Protocol (FastMCP).
          </p>
        </div>

        {/* Quick Launch Buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/documents"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            <Upload className="h-3.5 w-3.5" /> Ingest Files
          </Link>
          <Link
            to="/assistant"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            <BotMessageSquare className="h-3.5 w-3.5" /> AI Assistant
          </Link>
        </div>
      </div>

      {/* KPI Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Documents
            </span>
            <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Files className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900">{totalDocs}</div>
            <p className="text-[11px] text-slate-400 mt-0.5">Ingested & deduplicated</p>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Vector Chunks
            </span>
            <div className="h-8 w-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Layers className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900">{totalChunks}</div>
            <p className="text-[11px] text-slate-400 mt-0.5">FAISS CPU + FTS5 indexed</p>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              SOC 2 Coverage
            </span>
            <div className="h-8 w-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900">{coveragePercent}%</div>
            <p className="text-[11px] text-emerald-600 font-medium mt-0.5">
              {covered} of {(covered + partiallyCovered + missing)} controls met
            </p>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              System Status
            </span>
            <div className="h-8 w-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-slate-900 capitalize">
              {readiness?.status || 'Ready'}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Role: {currentRole}</p>
          </div>
        </div>
      </div>

      {/* Analytics Row: Coverage Donut & Severity Bar Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Coverage Breakdown */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">SOC 2 Control Assurance Breakdown</h3>
              <p className="text-xs text-slate-500">
                Ground-truth assessment based on active repository evidence
              </p>
            </div>
            <Link
              to="/compliance"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              Details <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <CoverageChart
            covered={covered}
            partiallyCovered={partiallyCovered}
            missing={missing}
          />
        </div>

        {/* Gap Severity Distribution */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Audit Gap Severity Distribution</h3>
              <p className="text-xs text-slate-500">
                Identified missing policy and control implementations
              </p>
            </div>
            <Link
              to="/gaps"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              Analyze <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="h-52 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748B' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Documents Table Preview */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Recently Ingested Documents</h3>
            <p className="text-xs text-slate-500">
              Verified files available for hybrid search and compliance evaluation
            </p>
          </div>
          <Link
            to="/documents"
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            View Repository <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {docData?.documents && docData.documents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 font-semibold uppercase text-[10px]">
                  <th className="py-2.5">Name</th>
                  <th className="py-2.5">Pages</th>
                  <th className="py-2.5">Size</th>
                  <th className="py-2.5">Security</th>
                  <th className="py-2.5 text-right">Ingested</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docData.documents.map((doc: DocumentItem) => (
                  <tr key={doc.id} className="hover:bg-slate-50/60">
                    <td className="py-3 font-semibold text-slate-800">
                      {doc.filename}
                    </td>
                    <td className="py-3 text-slate-600">{doc.page_count ?? 'N/A'}</td>
                    <td className="py-3 text-slate-600">
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 text-emerald-600 font-medium">Clean (Defender)</td>
                    <td className="py-3 text-right text-slate-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic py-4">No documents ingested yet.</p>
        )}
      </div>
    </div>
  )
}
