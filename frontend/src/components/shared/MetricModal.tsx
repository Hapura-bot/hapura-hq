import { useState } from 'react'
import { X, TrendingUp } from 'lucide-react'
import { useCreateMetric } from '../../hooks/useProjects'
import { currentPeriod } from '../../api/client'

interface MetricModalProps {
  projectId: string
  projectName: string
  onClose: () => void
}

export function MetricModal({ projectId, projectName, onClose }: MetricModalProps) {
  const [revenue, setRevenue]   = useState('')
  const [users, setUsers]       = useState('')
  const [signups, setSignups]   = useState('')
  const [period, setPeriod]     = useState(currentPeriod())
  const { mutate, isPending, isSuccess } = useCreateMetric()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutate({
      project_id:   projectId,
      period,
      revenue_vnd:  parseInt(revenue || '0'),
      active_users: parseInt(users || '0'),
      new_signups:  parseInt(signups || '0'),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-dark-800 border border-dark-600 rounded-xl w-full max-w-md mx-4 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-neon-green" />
            <h2 className="font-game font-bold text-base tracking-wide text-slate-100">
              Update Metrics
            </h2>
          </div>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        <p className="text-sm text-slate-500 mb-5">
          Project: <span className="text-slate-300 font-medium">{projectName}</span>
        </p>

        {isSuccess ? (
          <div className="text-center py-6">
            <div className="text-neon-green text-4xl mb-2">✓</div>
            <p className="text-slate-300 font-game font-bold tracking-wide">METRICS UPDATED</p>
            <button onClick={onClose} className="mt-4 text-sm text-slate-500 hover:text-slate-300">
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Period */}
            <div>
              <label className="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
                Period (YYYY-MM)
              </label>
              <input
                type="text"
                value={period}
                onChange={e => setPeriod(e.target.value)}
                pattern="\d{4}-\d{2}"
                placeholder="2026-04"
                className="w-full bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-brand"
              />
            </div>

            {/* Revenue */}
            <div>
              <label className="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
                Revenue (VND)
              </label>
              <input
                type="number"
                value={revenue}
                onChange={e => setRevenue(e.target.value)}
                placeholder="0"
                min="0"
                className="w-full bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm font-mono text-neon-green focus:outline-none focus:border-neon-green/50"
              />
            </div>

            {/* Active users */}
            <div>
              <label className="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
                Active Users
              </label>
              <input
                type="number"
                value={users}
                onChange={e => setUsers(e.target.value)}
                placeholder="0"
                min="0"
                className="w-full bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm font-mono text-brand focus:outline-none focus:border-brand/50"
              />
            </div>

            {/* New signups */}
            <div>
              <label className="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
                New Signups
              </label>
              <input
                type="number"
                value={signups}
                onChange={e => setSignups(e.target.value)}
                placeholder="0"
                min="0"
                className="w-full bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm font-mono text-slate-300 focus:outline-none focus:border-brand/50"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2 rounded border border-dark-600 text-sm text-slate-500 hover:text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="flex-1 py-2 rounded bg-neon-green/10 border border-neon-green/30 text-neon-green text-sm font-game font-bold tracking-wider hover:bg-neon-green/20 transition-all disabled:opacity-50"
              >
                {isPending ? 'SAVING...' : 'SAVE'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
