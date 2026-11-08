import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { getHealth, getReadiness } from '../services/healthService'
import { useAuth } from '../context/AuthContext'
import type { UserRole, ComponentHealth } from '../api/types'
import { RoleBadge } from '../components/common/Badge'
import { API_BASE_URL } from '../api/client'
import {
  Shield,
  Server,
  Cpu,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react'

export const SettingsPage: React.FC = () => {
  const { currentRole, setRole, user } = useAuth()

  const {
    data: health,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  })

  const {
    data: readiness,
    refetch: refetchReadiness,
  } = useQuery({
    queryKey: ['readiness'],
    queryFn: getReadiness,
  })

  const handleRefreshAll = () => {
    refetchHealth()
    refetchReadiness()
  }

  const roleDescriptions: Record<UserRole, { title: string; desc: string; perms: string[] }> = {
    admin: {
      title: 'Enterprise Administrator',
      desc: 'Full read and write control over document ingestion, deletion, knowledge graph modification, and compliance audits.',
      perms: [
        'Document Upload & Deletion',
        'Compliance Evaluation & Gap Auditing',
        'AI Assistant Chat & Tool Invocation',
        'Raw Database & FAISS Vector Maintenance',
      ],
    },
    auditor: {
      title: 'Compliance Auditor',
      desc: 'Read-only access to documents, assurance rationales, historical audit logs, and compliance evidence matrices.',
      perms: [
        'Document Viewing & Chunk Inspection',
        'Compliance Matrix & Gap Analysis',
        'Historical Audit Review',
        'No deletion or system modification privileges',
      ],
    },
    user: {
      title: 'General Team Member',
      desc: 'Access to Intelligent Search and AI Assistant for policy and procedural Q&A.',
      perms: [
        'Intelligent Hybrid Search',
        'AI Assistant Grounded Q&A',
        'Restricted from administrative configurations',
      ],
    },
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            System Diagnostics & Access Control
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage local environment configuration, role-based access controls, and infrastructure health.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRefreshAll}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh Diagnostics</span>
        </button>
      </div>

      {/* Role-Based Access Control Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-800">Security Role & Authentication</h2>
          </div>
          <span className="text-xs text-slate-400">Enforces backend X-API-Key verification</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(['admin', 'auditor', 'user'] as UserRole[]).map((role) => {
            const isSelected = currentRole === role
            const info = roleDescriptions[role]

            return (
              <div
                key={role}
                onClick={() => setRole(role)}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all space-y-3 ${
                  isSelected
                    ? 'border-blue-600 bg-blue-50/30 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between">
                  <RoleBadge role={role} />
                  {isSelected && (
                    <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">
                      Active
                    </span>
                  )}
                </div>

                <div>
                  <h4 className="font-bold text-slate-800 text-xs">{info.title}</h4>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">{info.desc}</p>
                </div>

                <div className="pt-2 border-t border-slate-100 text-[10px] space-y-1">
                  <span className="font-semibold text-slate-400 uppercase tracking-wider">
                    Permissions:
                  </span>
                  <ul className="text-slate-600 space-y-0.5 pl-3 list-disc">
                    {info.perms.map((p, idx) => (
                      <li key={idx}>{p}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Backend & Diagnostics Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend Connection */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Server className="h-5 w-5 text-slate-700" />
            <h2 className="text-sm font-bold text-slate-800">Backend API Services</h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">API Host URL:</span>
              <span className="font-mono font-semibold text-slate-800">{API_BASE_URL}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">FastAPI Status:</span>
              <span className="font-semibold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                {health?.status ? health.status.toUpperCase() : 'ONLINE'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">FastMCP Protocol:</span>
              <span className="font-mono text-slate-700">STDIO (Python MCP SDK)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-500">Active API Token:</span>
              <span className="font-mono text-[11px] text-slate-500">
                {user.apiKey.slice(0, 14)}...
              </span>
            </div>
          </div>
        </div>

        {/* Component Readiness Breakdown */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Cpu className="h-5 w-5 text-slate-700" />
            <h2 className="text-sm font-bold text-slate-800">Component Readiness Checks</h2>
          </div>

          <div className="space-y-3 text-xs">
            {readiness?.components ? (
              Object.entries(readiness.components).map(([name, comp]: [string, ComponentHealth]) => (
                <div
                  key={name}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100"
                >
                  <span className="font-semibold text-slate-700 uppercase text-[11px] tracking-wider">
                    {name.replace(/_/g, ' ')}
                  </span>
                  <span
                    className={`font-semibold capitalize flex items-center gap-1 ${
                      comp.status === 'healthy'
                        ? 'text-emerald-600'
                        : comp.status === 'degraded'
                        ? 'text-amber-600'
                        : 'text-rose-600'
                    }`}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {comp.status} ({comp.latency_ms}ms)
                  </span>
                </div>
              ))
            ) : (
              <div className="text-slate-400 italic">No component diagnostics available.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
