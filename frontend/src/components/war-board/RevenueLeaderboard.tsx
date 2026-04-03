import { motion, AnimatePresence } from 'framer-motion'
import { Crown, AlertCircle, Trophy } from 'lucide-react'
import type { ProjectRoom, MetricEntry, GPScore, IntegrationCache } from '../../api/client'
import { formatVND } from '../../api/client'

interface LeaderboardEntry {
  project: ProjectRoom
  metric?: MetricEntry
  gp?: GPScore
  integration?: IntegrationCache
}

interface Props {
  entries: LeaderboardEntry[]
  showDeclareButton?: boolean
  onDeclareWinner?: () => void
  isDeclaring?: boolean
}

export function RevenueLeaderboard({ entries, showDeclareButton, onDeclareWinner, isDeclaring }: Props) {
  const sorted = [...entries].sort((a, b) =>
    (b.metric?.revenue_vnd ?? 0) - (a.metric?.revenue_vnd ?? 0)
  )
  const maxRevenue = Math.max(...sorted.map(e => e.metric?.revenue_vnd ?? 0), 1)
  const hasWinner = (sorted[0]?.metric?.revenue_vnd ?? 0) > 0

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-game font-bold text-sm tracking-widest text-slate-400 flex items-center gap-2">
          <Crown size={14} className="text-neon-amber" />
          REVENUE WAR — THIS MONTH
        </h2>
        {showDeclareButton && hasWinner && (
          <button
            onClick={onDeclareWinner}
            disabled={isDeclaring}
            className="flex items-center gap-1.5 text-xs font-game font-bold tracking-wider px-2.5 py-1 rounded border border-neon-amber/30 bg-neon-amber/10 text-neon-amber hover:bg-neon-amber/20 transition-all disabled:opacity-50"
          >
            <Trophy size={10} />
            {isDeclaring ? 'DECLARING...' : 'DECLARE WINNER'}
          </button>
        )}
      </div>

      <div className="space-y-3">
        <AnimatePresence mode="popLayout">
          {sorted.map((entry, i) => {
            const revenue = entry.metric?.revenue_vnd ?? 0
            const pct = Math.round((revenue / maxRevenue) * 100)
            const isWinner = i === 0 && revenue > 0

            return (
              <motion.div
                key={entry.project.id}
                layout
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: isWinner ? 1 : 0.72, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: i * 0.06, duration: 0.3 }}
                className="relative hover:opacity-100 transition-opacity"
              >
                <div className="flex items-center gap-3 mb-1">
                  <motion.span
                    layout="position"
                    className={`w-5 text-center font-game font-bold text-sm ${
                      i === 0 ? 'text-neon-amber' : i === 1 ? 'text-slate-400' : 'text-slate-600'
                    }`}
                  >
                    {isWinner ? '★' : `${i + 1}`}
                  </motion.span>

                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: entry.project.color_accent }} />
                    <span className="text-sm font-medium text-slate-200 truncate">{entry.project.name}</span>
                    {entry.gp?.is_focus && (
                      <motion.span
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                        className="shrink-0 text-xs font-game font-bold tracking-widest px-1.5 py-0.5 rounded animate-pulse-slow"
                        style={{
                          color: entry.project.color_accent,
                          border: `1px solid ${entry.project.color_accent}40`,
                          background: `${entry.project.color_accent}15`,
                        }}
                      >
                        FOCUS
                      </motion.span>
                    )}
                  </div>

                  <span className={`font-mono text-sm font-bold shrink-0 ${isWinner ? 'text-neon-green' : 'text-slate-400'}`}>
                    {revenue > 0 ? `${formatVND(revenue)}đ` : '—'}
                  </span>

                  {(entry.integration?.github_open_issues ?? 0) > 0 && (
                    <span className="flex items-center gap-0.5 text-xs font-mono text-neon-amber shrink-0">
                      <AlertCircle size={9} />
                      {entry.integration!.github_open_issues}
                    </span>
                  )}

                  {entry.gp && (
                    <span className="font-mono text-xs text-neon-purple w-10 text-right shrink-0">
                      {entry.gp.investment_multiplier}x
                    </span>
                  )}
                </div>

                {/* Animated revenue bar */}
                <div className="ml-8 h-1 bg-dark-600 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.9, delay: i * 0.1, ease: 'easeOut' }}
                    style={{ background: entry.project.color_accent }}
                  />
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
