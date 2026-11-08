import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getGapAnalysis } from '../services/complianceService'
import { SeverityBadge } from '../components/common/Badge'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import type { GapItem } from '../api/types'
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  GitBranch,
} from 'lucide-react'

interface RemediationTask {
  id: string
  code: string
  title: string
  priority: string
  effortDays: number
  actionItems: string[]
  dependencies: string[]
  completed: boolean
}

export const RemediationPage: React.FC = () => {
  const [framework, setFramework] = useState<'SOC2' | 'ISO27001'>('SOC2')
  const [tasksState, setTasksState] = useState<Record<string, boolean>>({})

  const { data: gapData, isLoading } = useQuery({
    queryKey: ['gap-analysis', framework],
    queryFn: () => getGapAnalysis(framework),
  })

  const gaps = gapData?.remediation_roadmap || []

  // Derive prioritized actionable tasks from gaps
  const tasks: RemediationTask[] = gaps.map((gap: GapItem, index: number) => {
    return {
      id: gap.requirement_code,
      code: gap.requirement_code,
      title: gap.title,
      priority: gap.severity,
      effortDays: gap.estimated_effort_days || 3,
      actionItems: [
        gap.remediation_recommendation || 'Draft formal policy documentation and obtain executive sign-off.',
        'Implement automated evidence collection or telemetry logging.',
        'Ingest updated policy and log proof into VERITY repository.',
      ],
      dependencies: index > 0 ? [gaps[index - 1].requirement_code] : [],
      completed: !!tasksState[gap.requirement_code],
    }
  })

  const toggleTask = (code: string) => {
    setTasksState((prev) => ({ ...prev, [code]: !prev[code] }))
  }

  const totalEffortDays = tasks.reduce((sum, t) => sum + (t.completed ? 0 : t.effortDays), 0)
  const completedCount = tasks.filter((t) => t.completed).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Prioritized Remediation Roadmap
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Actionable engineering and policy steps to close compliance gaps and achieve audit readiness.
          </p>
        </div>

        <div className="flex items-center rounded-lg border border-slate-200 bg-white p-1">
          <button
            type="button"
            onClick={() => setFramework('SOC2')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              framework === 'SOC2'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            SOC 2 Roadmap
          </button>
          <button
            type="button"
            onClick={() => setFramework('ISO27001')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              framework === 'ISO27001'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            ISO 27001 Roadmap
          </button>
        </div>
      </div>

      {/* Mandatory Engineering Effort Disclaimer Alert */}
      <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-800 text-xs flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-slate-900">
            Engineering Planning Disclaimer
          </p>
          <p className="text-slate-700 leading-relaxed">
            All effort estimates (days) are heuristic engineering planning guidelines based on typical policy drafting, review cycles, and technical implementation. They are not guaranteed delivery dates or binding audit SLAs.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="py-20 bg-white rounded-2xl border border-slate-200">
          <LoadingSpinner label="Formulating remediation roadmap..." />
        </div>
      ) : (
        <>
          {/* Progress Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Remediation Effort
              </span>
              <p className="text-2xl font-black text-slate-900">
                ~{totalEffortDays} Engineering Days
              </p>
              <p className="text-[11px] text-slate-400">Remaining to close identified gaps</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Roadmap Tasks
              </span>
              <p className="text-2xl font-black text-blue-600">
                {tasks.length} Action Items
              </p>
              <p className="text-[11px] text-slate-400">Derived from automated gap analysis</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Completed in Session
              </span>
              <p className="text-2xl font-black text-emerald-600">
                {completedCount} of {tasks.length}
              </p>
              <p className="text-[11px] text-slate-400">
                {tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 100}% roadmap complete
              </p>
            </div>
          </div>

          {/* Remediation Tasks Timeline */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-800">Prioritized Action Items</h3>

            {tasks.length > 0 ? (
              <div className="space-y-4">
                {tasks.map((task) => (
                  <div
                    key={task.code}
                    className={`bg-white rounded-xl border p-5 shadow-xs transition-all ${
                      task.completed
                        ? 'border-emerald-200 bg-emerald-50/20 opacity-75'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {/* Top Row: Checkbox, Code, Title, Priority */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={task.completed}
                          onChange={() => toggleTask(task.code)}
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                              {task.code}
                            </span>
                            <h4
                              className={`text-sm font-bold ${
                                task.completed
                                  ? 'text-slate-500 line-through'
                                  : 'text-slate-800'
                              }`}
                            >
                              {task.title}
                            </h4>
                          </div>

                          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                            <span className="flex items-center gap-1 font-medium text-slate-700">
                              <Clock className="h-3.5 w-3.5 text-slate-400" />
                              Estimated: ~{task.effortDays} Days
                            </span>
                            {task.dependencies.length > 0 && (
                              <span className="flex items-center gap-1 text-[11px] text-slate-500">
                                <GitBranch className="h-3.5 w-3.5 text-slate-400" />
                                Depends on: {task.dependencies.join(', ')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <SeverityBadge severity={task.priority} />
                    </div>

                    {/* Step-by-step guidance */}
                    {!task.completed && (
                      <div className="mt-4 pt-3 border-t border-slate-100 text-xs space-y-2">
                        <span className="font-semibold text-slate-700 uppercase text-[10px] tracking-wider">
                          Recommended Action Sequence:
                        </span>
                        <div className="space-y-1.5 pl-2 border-l-2 border-blue-500">
                          {task.actionItems.map((action, i) => (
                            <p key={i} className="text-slate-600">
                              <span className="font-bold text-slate-700">{i + 1}.</span> {action}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-16 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">
                <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                No remediation actions currently required. All framework requirements are verified.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
