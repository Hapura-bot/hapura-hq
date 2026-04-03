import { useState } from 'react'
import { Activity, Zap } from 'lucide-react'
import { useProjects, useMetrics, useGPScore } from '../hooks/useProjects'
import { useIntegrations, useIntegrationMap, useRefreshIntegration } from '../hooks/useIntegrations'
import { ProjectRoomCard } from '../components/rooms/ProjectRoomCard'
import { RevenueLeaderboard } from '../components/war-board/RevenueLeaderboard'
import { MetricModal } from '../components/shared/MetricModal'
import { formatVND, formatCount } from '../api/client'

function GPScoreRow({ projectId }: { projectId: string }) {
  const { data: gp } = useGPScore(projectId)
  return gp ? (
    <div className="flex items-center gap-2 text-xs font-mono">
      <span className="text-slate-600">{gp.project_id}</span>
      <div className="flex-1 h-1 bg-dark-600 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-neon-purple transition-all"
          style={{ width: `${(gp.gp_total / 1000) * 100}%` }}
        />
      </div>
      <span className="text-neon-purple w-12 text-right">{gp.gp_total} GP</span>
    </div>
  ) : null
}

export default function DashboardPage() {
  const { data: projects = [], isLoading: loadingProjects } = useProjects()
  const { data: metrics = [] }   = useMetrics()
  const { data: integrations }   = useIntegrations()
  const integrationMap           = useIntegrationMap(integrations)
  const { mutate: doRefresh }    = useRefreshIntegration()
  const [metricModal, setMetricModal] = useState<{ projectId: string; projectName: string } | null>(null)

  function getMetric(projectId: string) {
    return metrics.find(m => m.project_id === projectId)
  }

  function openMetricModal(projectId: string) {
    const p = projects.find(p => p.id === projectId)
    if (p) setMetricModal({ projectId: p.id, projectName: p.name })
  }

  const leaderboardEntries = projects.map(p => ({
    project: p,
    metric: getMetric(p.id),
    integration: integrationMap[p.id],
  }))

  if (loadingProjects) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-600 tracking-widest">LOADING WAR ROOM...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-game font-bold text-2xl text-slate-100 tracking-wide flex items-center gap-2">
            <Activity size={20} className="text-brand animate-pulse-slow" />
            COMMAND CENTER
          </h1>
          <p className="text-xs text-slate-600 mt-1 font-mono">
            {new Date().toLocaleString('vi-VN', { dateStyle: 'full', timeStyle: 'short' })}
          </p>
        </div>

        {/* Quick stats */}
        <div className="hidden md:flex items-center gap-6 text-center">
          <div>
            <div className="text-xs text-slate-600 font-mono uppercase">Projects</div>
            <div className="text-xl font-game font-bold text-brand">{projects.length}</div>
          </div>
          <div>
            <div className="text-xs text-slate-600 font-mono uppercase">Live</div>
            <div className="text-xl font-game font-bold text-neon-green">
              {projects.filter(p => p.status === 'deployed').length}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-600 font-mono uppercase">Total Rev</div>
            <div className="text-xl font-game font-bold text-neon-amber">
              {formatVND(metrics.reduce((s, m) => s + m.revenue_vnd, 0))}đ
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-600 font-mono uppercase">Users</div>
            <div className="text-xl font-game font-bold text-slate-300">
              {formatCount(metrics.reduce((s, m) => s + m.active_users, 0))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Project rooms grid */}
        <div className="xl:col-span-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map((project, i) => (
              <ProjectRoomCard
                key={project.id}
                project={project}
                metric={getMetric(project.id)}
                integration={integrationMap[project.id]}
                index={i}
                onAddMetric={openMetricModal}
                onRefresh={doRefresh}
              />
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <RevenueLeaderboard entries={leaderboardEntries} />

          {/* GP Scores panel */}
          <div className="bg-dark-800 border border-dark-600 rounded-lg p-5">
            <h2 className="font-game font-bold text-sm tracking-widest text-slate-400 mb-4 flex items-center gap-2">
              <Zap size={13} className="text-neon-purple" />
              GP SCORES
            </h2>
            <div className="space-y-2">
              {projects.map(p => (
                <GPScoreRow key={p.id} projectId={p.id} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Metric modal */}
      {metricModal && (
        <MetricModal
          projectId={metricModal.projectId}
          projectName={metricModal.projectName}
          onClose={() => setMetricModal(null)}
        />
      )}
    </div>
  )
}
