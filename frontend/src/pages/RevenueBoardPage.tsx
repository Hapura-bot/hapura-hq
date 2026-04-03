import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, Trophy } from 'lucide-react'
import { useProjects, useMetrics, useAllGPScores, useDeclareWinner } from '../hooks/useProjects'
import { RevenueLeaderboard } from '../components/war-board/RevenueLeaderboard'
import { formatVND } from '../api/client'
import type { GPScore } from '../api/client'

function GPBar({ gp }: { gp: GPScore }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-mono text-slate-500 w-28 truncate">{gp.project_id}</span>
      <div className="flex-1 h-1.5 bg-dark-600 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-neon-purple"
          initial={{ width: 0 }}
          animate={{ width: `${(gp.gp_total / 1000) * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs font-mono text-neon-purple w-16 text-right">{gp.gp_total}/1000</span>
      {gp.is_focus && <span className="text-xs text-neon-amber font-game font-bold">★</span>}
    </div>
  )
}

export default function RevenueBoardPage() {
  const { data: projects = [] }         = useProjects()
  const { data: metrics = [] }          = useMetrics()
  const gpScores                        = useAllGPScores()
  const { mutate: declareWinner, isPending: declaring } = useDeclareWinner()
  const [winnerBanner, setWinnerBanner] = useState<{ name: string; period: string } | null>(null)

  const gpMap = Object.fromEntries(gpScores.map(g => [g.project_id, g]))
  const entries = projects.map(p => ({
    project: p,
    metric: metrics.find(m => m.project_id === p.id),
    gp: gpMap[p.id],
  }))
  const totalRevenue = metrics.reduce((s, m) => s + m.revenue_vnd, 0)

  function handleDeclareWinner() {
    declareWinner(undefined, {
      onSuccess: (data) => setWinnerBanner({ name: data.winner_name, period: data.period }),
    })
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="mb-6 flex items-center gap-2">
        <BarChart3 size={18} className="text-neon-amber" />
        <h1 className="font-game font-bold text-xl text-slate-100 tracking-wide">REVENUE BOARD</h1>
      </div>

      {/* Animated total revenue */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-dark-800 border border-dark-600 rounded-lg p-5 mb-6 text-center"
      >
        <div className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">
          Total Revenue — This Month
        </div>
        <motion.div
          key={totalRevenue}
          initial={{ scale: 0.92, opacity: 0.5 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="text-4xl font-game font-bold text-neon-green text-glow-green"
        >
          {totalRevenue > 0 ? `${formatVND(totalRevenue)}đ` : '0đ'}
        </motion.div>
      </motion.div>

      {/* Winner banner */}
      {winnerBanner && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-neon-amber/10 border border-neon-amber/30 rounded-lg p-4 mb-6 flex items-center gap-3"
        >
          <Trophy size={18} className="text-neon-amber shrink-0" />
          <div>
            <p className="text-sm font-game font-bold text-neon-amber tracking-wide">
              🏆 WINNER THÁNG {winnerBanner.period}: {winnerBanner.name}
            </p>
            <p className="text-xs font-mono text-slate-400 mt-0.5">
              Telegram announcement sent · Sprint tiếp theo sẽ FOCUS vào {winnerBanner.name}
            </p>
          </div>
        </motion.div>
      )}

      <RevenueLeaderboard
        entries={entries}
        showDeclareButton
        isDeclaring={declaring}
        onDeclareWinner={handleDeclareWinner}
      />

      {/* GP Score breakdown */}
      {gpScores.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-dark-800 border border-dark-600 rounded-lg p-5 mt-4"
        >
          <h2 className="font-game font-bold text-sm tracking-widest text-slate-400 mb-4">GP SCORES</h2>
          <div className="space-y-3">
            {gpScores
              .sort((a, b) => b.gp_total - a.gp_total)
              .map(gp => <GPBar key={gp.project_id} gp={gp} />)}
          </div>
          <p className="text-xs font-mono text-slate-700 mt-4">
            GP = Revenue(400) + Users(200) + Velocity(200) + Uptime(200)
          </p>
        </motion.div>
      )}
    </div>
  )
}
