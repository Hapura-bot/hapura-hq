import { motion } from 'framer-motion'
import { ExternalLink, Smartphone, Globe, Zap, GitBranch, RefreshCw } from 'lucide-react'
import { NeonBadge } from '../shared/NeonBadge'
import { MetricTile } from '../shared/MetricTile'
import { MiniSparkBar } from '../shared/MiniSparkBar'
import type { ProjectRoom, MetricEntry, GPScore, IntegrationCache, HealthStatus } from '../../api/client'
import { formatVND, formatCount } from '../../api/client'

interface ProjectRoomCardProps {
  project: ProjectRoom
  metric?: MetricEntry
  gp?: GPScore
  integration?: IntegrationCache
  index: number
  onAddMetric: (projectId: string) => void
  onRefresh?: (projectId: string) => void
}

const HEALTH_DOT: Record<HealthStatus, { color: string; label: string; pulse: boolean }> = {
  healthy:  { color: 'bg-neon-green',  label: 'LIVE',    pulse: true  },
  degraded: { color: 'bg-neon-amber',  label: 'SLOW',    pulse: true  },
  timeout:  { color: 'bg-neon-amber',  label: 'TIMEOUT', pulse: false },
  offline:  { color: 'bg-neon-red',    label: 'DOWN',    pulse: false },
  unknown:  { color: 'bg-slate-600',   label: '—',       pulse: false },
}

const STATUS_COLOR: Record<string, 'green' | 'amber' | 'red'> = {
  deployed: 'green',
  dev:      'amber',
  planned:  'red',
}

const STATUS_LABEL: Record<string, string> = {
  deployed: 'LIVE',
  dev:      'DEV',
  planned:  'PLANNED',
}

export function ProjectRoomCard({ project, metric, gp, integration, index, onAddMetric, onRefresh }: ProjectRoomCardProps) {
  const statusColor = STATUS_COLOR[project.status] ?? 'amber'
  const isFocus = gp?.is_focus ?? false
  const healthStatus = (integration?.cloudrun_status ?? 'unknown') as HealthStatus
  const healthDot = HEALTH_DOT[healthStatus]
  const latency = integration?.cloudrun_latency_ms

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.35 }}
      className={`room-card group cursor-default ${isFocus ? 'ring-1' : ''}`}
      style={{
        borderLeftColor: project.color_accent,
        borderLeftWidth: 3,
        ...(isFocus ? { ringColor: project.color_accent } : {}),
      }}
    >
      {/* FOCUS badge */}
      {isFocus && (
        <div
          className="absolute top-3 right-3 px-2 py-0.5 rounded text-xs font-game font-bold tracking-widest animate-pulse-slow"
          style={{ color: project.color_accent, border: `1px solid ${project.color_accent}40`, background: `${project.color_accent}15` }}
        >
          ★ FOCUS
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-lg"
          style={{ background: `${project.color_accent}20`, border: `1px solid ${project.color_accent}40` }}
        >
          {project.platform === 'android' ? <Smartphone size={16} style={{ color: project.color_accent }} /> : <Globe size={16} style={{ color: project.color_accent }} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-game font-bold text-base text-slate-100 tracking-wide">{project.name}</h3>
            <NeonBadge label={STATUS_LABEL[project.status]} color={statusColor} pulse={project.status === 'deployed'} />
            {/* Cloud Run health dot */}
            {integration && (
              <div className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${healthDot.color} ${healthDot.pulse ? 'animate-pulse' : ''}`} />
                <span className="text-xs font-mono text-slate-600">
                  {latency != null ? `${latency}ms` : healthDot.label}
                </span>
              </div>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5 truncate">{project.tagline}</p>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricTile
          label="Revenue"
          value={metric ? `${formatVND(metric.revenue_vnd)}đ` : '—'}
          sub={metric ? 'this month' : 'no data'}
          color="green"
        />
        <MetricTile
          label="Users"
          value={metric ? formatCount(metric.active_users) : '—'}
          sub={metric ? `+${metric.new_signups} new` : ''}
          color="cyan"
        />
        <MetricTile
          label="GP Score"
          value={gp ? gp.gp_total.toString() : '—'}
          sub={gp ? `${gp.investment_multiplier}x` : ''}
          color="purple"
        />
      </div>

      {/* Phase bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-500 font-mono">
            Phase {project.phase_current}/{project.phase_total}
          </span>
          <span className="text-xs text-slate-400">{project.phase_label}</span>
        </div>
        <div className="h-1.5 bg-dark-600 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${(project.phase_current / project.phase_total) * 100}%`,
              background: project.color_accent,
            }}
          />
        </div>
      </div>

      {/* Tech stack */}
      <div className="flex flex-wrap gap-1 mb-4">
        {project.tech_stack.slice(0, 4).map((t) => (
          <span key={t} className="text-xs font-mono text-slate-600 bg-dark-700 px-1.5 py-0.5 rounded border border-dark-600">
            {t}
          </span>
        ))}
        {project.tech_stack.length > 4 && (
          <span className="text-xs font-mono text-slate-700">+{project.tech_stack.length - 4}</span>
        )}
      </div>

      {/* GitHub commit spark */}
      {integration && integration.github_commits_4w.length > 0 && (
        <div className="mb-3 flex items-center gap-2">
          <GitBranch size={10} className="text-slate-600 shrink-0" />
          <MiniSparkBar
            values={integration.github_commits_4w}
            color={project.color_accent}
            width={80}
            height={20}
          />
          <span className="text-xs font-mono text-slate-600">
            {integration.github_commits_7d} commits/wk
          </span>
        </div>
      )}

      {/* Footer actions */}
      <div className="flex items-center justify-between pt-3 border-t border-dark-600">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onAddMetric(project.id)}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-neon-green transition-colors font-mono"
          >
            <Zap size={11} />
            + Revenue
          </button>
          {onRefresh && (
            <button
              onClick={() => onRefresh(project.id)}
              className="flex items-center gap-1 text-xs text-slate-700 hover:text-brand transition-colors font-mono"
              title="Refresh live data"
            >
              <RefreshCw size={10} />
            </button>
          )}
        </div>
        {project.frontend_url && (
          <a
            href={project.frontend_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-slate-600 hover:text-brand transition-colors"
          >
            <ExternalLink size={11} />
            Open
          </a>
        )}
      </div>
    </motion.div>
  )
}
