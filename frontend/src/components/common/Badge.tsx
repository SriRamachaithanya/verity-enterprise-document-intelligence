import React from 'react'
import type { ComplianceStatus, AssuranceTier, UserRole } from '../../api/types'

export type BadgeVariant =
  | 'covered'
  | 'partially_covered'
  | 'missing'
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'operating'
  | 'implementation'
  | 'policy'
  | 'primary'
  | 'neutral'
  | 'success'
  | 'danger'
  | 'warning'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant | string
  className?: string
  dot?: boolean
}

const variantStyles: Record<string, string> = {
  covered: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  partially_covered: 'bg-amber-50 text-amber-700 border-amber-200',
  missing: 'bg-rose-50 text-rose-700 border-rose-200',
  critical: 'bg-purple-50 text-purple-700 border-purple-200 font-semibold',
  high: 'bg-rose-50 text-rose-700 border-rose-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-blue-50 text-blue-700 border-blue-200',
  operating: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  implementation: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  policy: 'bg-slate-100 text-slate-700 border-slate-300',
  primary: 'bg-blue-50 text-blue-700 border-blue-200',
  neutral: 'bg-slate-100 text-slate-600 border-slate-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  danger: 'bg-rose-50 text-rose-700 border-rose-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  className = '',
  dot = false,
}) => {
  const normKey = variant.toString().toLowerCase()
  const style = variantStyles[normKey] || variantStyles.neutral

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${style} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />}
      {children}
    </span>
  )
}

export const ComplianceBadge: React.FC<{ status: ComplianceStatus | string }> = ({ status }) => {
  const s = status.toUpperCase()
  if (s === 'COVERED') {
    return <Badge variant="covered" dot>Covered</Badge>
  }
  if (s === 'PARTIALLY_COVERED') {
    return <Badge variant="partially_covered" dot>Partially Covered</Badge>
  }
  return <Badge variant="missing" dot>Missing Evidence</Badge>
}

export const AssuranceBadge: React.FC<{ tier: AssuranceTier | string }> = ({ tier }) => {
  const t = tier.toLowerCase()
  if (t === 'high') {
    return <Badge variant="success">High Assurance</Badge>
  }
  if (t === 'medium') {
    return <Badge variant="warning">Medium Assurance</Badge>
  }
  if (t === 'low') {
    return <Badge variant="neutral">Low Assurance</Badge>
  }
  return <Badge variant="neutral">Unverified</Badge>
}

export const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const sev = severity.toLowerCase()
  if (sev === 'critical') {
    return <Badge variant="critical">Critical Severity</Badge>
  }
  if (sev === 'high') {
    return <Badge variant="high">High Severity</Badge>
  }
  if (sev === 'medium') {
    return <Badge variant="medium">Medium Severity</Badge>
  }
  return <Badge variant="low">Low Severity</Badge>
}

export const RoleBadge: React.FC<{ role: UserRole | string }> = ({ role }) => {
  const r = role.toLowerCase()
  if (r === 'admin') {
    return (
      <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-purple-100 text-purple-700 border border-purple-200">
        Admin
      </span>
    )
  }
  if (r === 'auditor') {
    return (
      <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-blue-700 border border-blue-200">
        Auditor
      </span>
    )
  }
  return (
    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200">
      User
    </span>
  )
}
