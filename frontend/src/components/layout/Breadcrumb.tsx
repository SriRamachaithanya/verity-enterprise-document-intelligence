import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'

const routeNameMap: Record<string, string> = {
  documents: 'Documents Repository',
  search: 'Intelligent Search',
  assistant: 'AI Assistant',
  compliance: 'Compliance Overview',
  gaps: 'Gap Analysis',
  knowledge: 'Knowledge Graph',
  remediation: 'Remediation Roadmap',
  settings: 'System Settings',
}

export const Breadcrumb: React.FC = () => {
  const location = useLocation()
  const pathnames = location.pathname.split('/').filter((x) => x)

  return (
    <nav className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium">
      <Link
        to="/"
        className="flex items-center hover:text-slate-800 transition-colors gap-1"
      >
        <Home className="h-3.5 w-3.5" />
        <span>Dashboard</span>
      </Link>

      {pathnames.map((segment, index) => {
        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`
        const isLast = index === pathnames.length - 1
        const displayName = routeNameMap[segment] || segment

        return (
          <React.Fragment key={routeTo}>
            <ChevronRight className="h-3 w-3 text-slate-400" />
            {isLast ? (
              <span className="text-slate-800 font-semibold">{displayName}</span>
            ) : (
              <Link to={routeTo} className="hover:text-slate-800 transition-colors">
                {displayName}
              </Link>
            )}
          </React.Fragment>
        )
      })}
    </nav>
  )
}

