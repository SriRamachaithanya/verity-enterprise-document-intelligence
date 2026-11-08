import React, { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Files,
  Search,
  BotMessageSquare,
  ShieldCheck,
  AlertOctagon,
  Network,
  Wrench,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react'

const navItems = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/documents', label: 'Documents', icon: Files },
  { path: '/search', label: 'Intelligent Search', icon: Search },
  { path: '/assistant', label: 'AI Assistant', icon: BotMessageSquare },
  { path: '/compliance', label: 'Compliance', icon: ShieldCheck },
  { path: '/gaps', label: 'Gap Analysis', icon: AlertOctagon },
  { path: '/knowledge', label: 'Knowledge Graph', icon: Network },
  { path: '/remediation', label: 'Remediation', icon: Wrench },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`relative bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-300 z-30 shrink-0 ${
        collapsed ? 'w-18' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800/80">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="h-9 w-9 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shrink-0">
            <Shield className="h-5 w-5 text-blue-400" />
          </div>
          {!collapsed && (
            <div className="truncate">
              <span className="font-bold text-white tracking-wide text-base">VERITY</span>
              <span className="block text-[10px] text-slate-400 uppercase tracking-widest font-medium truncate">
                Compliance Agent
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`
              }
              title={collapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Collapse Toggle Footer */}
      <div className="p-3 border-t border-slate-800/80">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-xs font-medium"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse Sidebar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

