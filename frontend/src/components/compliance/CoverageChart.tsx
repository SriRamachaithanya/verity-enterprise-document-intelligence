import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

interface CoverageChartProps {
  covered: number
  partiallyCovered: number
  missing: number
}

const COLORS = {
  covered: '#10B981', // Emerald 500
  partiallyCovered: '#F59E0B', // Amber 500
  missing: '#EF4444', // Rose 500
}

export const CoverageChart: React.FC<CoverageChartProps> = ({
  covered,
  partiallyCovered,
  missing,
}) => {
  const total = covered + partiallyCovered + missing
  const percentage = total > 0 ? Math.round((covered / total) * 100) : 0

  const data = [
    { name: 'Covered', value: covered, color: COLORS.covered },
    { name: 'Partially Covered', value: partiallyCovered, color: COLORS.partiallyCovered },
    { name: 'Missing', value: missing, color: COLORS.missing },
  ].filter((item) => item.value > 0)

  return (
    <div className="flex flex-col sm:flex-row items-center justify-around gap-6 p-4">
      {/* Donut Chart with Centered Metric */}
      <div className="relative h-44 w-44 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              formatter={(value: any, name: any) => [
                `${value} requirements (${total > 0 ? Math.round((Number(value) / total) * 100) : 0}%)`,
                name,
              ]}
              contentStyle={{
                backgroundColor: '#1E293B',
                borderColor: '#334155',
                borderRadius: '8px',
                color: '#fff',
                fontSize: '12px',
              }}
            />
            <Pie
              data={data.length > 0 ? data : [{ name: 'None', value: 1, color: '#E2E8F0' }]}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={70}
              paddingAngle={3}
              dataKey="value"
            >
              {(data.length > 0 ? data : [{ name: 'None', value: 1, color: '#E2E8F0' }]).map(
                (entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                )
              )}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-black text-slate-800">{percentage}%</span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
            Compliance
          </span>
        </div>
      </div>

      {/* Legend & Breakdown stats */}
      <div className="space-y-3 w-full max-w-xs text-xs">
        <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-50/70 border border-emerald-100">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-emerald-500 shrink-0" />
            <span className="font-semibold text-emerald-900">Covered</span>
          </div>
          <span className="font-bold text-emerald-800">
            {covered} <span className="text-[10px] font-normal text-emerald-600">({total > 0 ? Math.round((covered / total) * 100) : 0}%)</span>
          </span>
        </div>

        <div className="flex items-center justify-between p-2 rounded-lg bg-amber-50/70 border border-amber-100">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-amber-500 shrink-0" />
            <span className="font-semibold text-amber-900">Partially Covered</span>
          </div>
          <span className="font-bold text-amber-800">
            {partiallyCovered} <span className="text-[10px] font-normal text-amber-600">({total > 0 ? Math.round((partiallyCovered / total) * 100) : 0}%)</span>
          </span>
        </div>

        <div className="flex items-center justify-between p-2 rounded-lg bg-rose-50/70 border border-rose-100">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-rose-500 shrink-0" />
            <span className="font-semibold text-rose-900">Missing Evidence</span>
          </div>
          <span className="font-bold text-rose-800">
            {missing} <span className="text-[10px] font-normal text-rose-600">({total > 0 ? Math.round((missing / total) * 100) : 0}%)</span>
          </span>
        </div>
      </div>
    </div>
  )
}

