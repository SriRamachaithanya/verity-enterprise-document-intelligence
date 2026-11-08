import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  RefreshCw,
} from 'lucide-react'
import { Breadcrumb } from './Breadcrumb'
import { useAuth } from '../../context/AuthContext'
import { getReadiness } from '../../services/healthService'
import { RoleBadge } from '../common/Badge'
import type { UserRole } from '../../api/types'

export const Header: React.FC = () => {
  const { currentRole, setRole, user } = useAuth()
  const [roleDropdownOpen, setRoleDropdownOpen] = useState(false)

  const { data: readiness, isFetching, refetch } = useQuery({
    queryKey: ['readiness'],
    queryFn: getReadiness,
    refetchInterval: 30000,
    retry: 1,
  })

  const isReady = readiness?.status === 'ready'
  const isDegraded = readiness?.status === 'degraded'

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-20 shadow-xs">
      {/* Left: Breadcrumbs navigation */}
      <div className="flex items-center gap-4">
        <Breadcrumb />
      </div>

      {/* Right: Status badge, Role selector, & Utilities */}
      <div className="flex items-center gap-4">
        {/* System Health / Readiness Badge */}
        <div
          className="flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors"
          onClick={() => refetch()}
          title={`Click to refresh system readiness.\nStatus: ${readiness?.status || 'checking...'}`}
        >
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isReady ? 'bg-emerald-400' : isDegraded ? 'bg-amber-400' : 'bg-rose-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isReady ? 'bg-emerald-500' : isDegraded ? 'bg-amber-500' : 'bg-rose-500'
              }`}
            />
          </span>
          <span className="text-slate-700 capitalize">
            {readiness?.status ? `System ${readiness.status}` : 'Connecting...'}
          </span>
          {isFetching && <RefreshCw className="h-3 w-3 text-slate-400 animate-spin ml-1" />}
        </div>

        {/* Vertical divider */}
        <div className="h-4 w-px bg-slate-200" />

        {/* Role Switcher Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setRoleDropdownOpen(!roleDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all text-xs text-slate-700 font-medium"
          >
            <RoleBadge role={currentRole} />
            <span className="hidden sm:inline text-slate-600 capitalize">{user.role} User</span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {roleDropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setRoleDropdownOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 text-xs">
                <div className="px-3 py-2 border-b border-slate-100">
                  <p className="font-semibold text-slate-900">Switch Security Role</p>
                  <p className="text-[11px] text-slate-500">
                    Simulates RBAC policies enforced by the backend API keys.
                  </p>
                </div>
                {(['admin', 'auditor', 'user'] as UserRole[]).map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => {
                      setRole(role)
                      setRoleDropdownOpen(false)
                    }}
                    className={`w-full text-left px-3 py-2.5 flex items-center justify-between hover:bg-slate-50 transition-colors ${
                      currentRole === role ? 'bg-blue-50/60 font-semibold text-blue-700' : 'text-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <RoleBadge role={role} />
                      <span className="capitalize">{role}</span>
                    </div>
                    {currentRole === role && (
                      <span className="text-[10px] text-blue-600 font-bold uppercase tracking-wider">
                        Active
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
