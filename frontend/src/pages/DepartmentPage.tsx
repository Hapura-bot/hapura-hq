import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import {
  ArrowLeft, Bot, Play, Clock, CheckCircle, AlertTriangle,
  Loader2, MessageSquare, FileText, Crown, TrendingUp,
  Code2, DollarSign, HeartHandshake, BarChart3, Server, Building2,
} from 'lucide-react'
import { useDepartment, useRunDepartment } from '../hooks/useWorkspace'
import { useTriggerAgent, useLatestAgentRun } from '../hooks/useAgents'
import type { AgentDetail } from '../hooks/useWorkspace'

const ICON_MAP: Record<string, React.ElementType> = {
  Crown, TrendingUp, Code2, DollarSign,
  HeartHandshake, BarChart3, Server,
}

const COLOR_CLASSES: Record<string, string> = {
  'neon-green':  'text-neon-green  border-neon-green/30  bg-neon-green/10',
  'neon-purple': 'text-neon-purple border-neon-purple/30 bg-neon-purple/10',
  'neon-amber':  'text-neon-amber  border-neon-amber/30  bg-neon-amber/10',
  'neon-red':    'text-neon-red    border-neon-red/30    bg-neon-red/10',
  'neon-cyan':   'text-brand       border-brand/30       bg-brand/10',
  'brand':       'text-brand       border-brand/30       bg-brand/10',
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'running') return <Loader2 size={13} className="animate-spin text-neon-purple" />
  if (status === 'done')    return <CheckCircle size={13} className="text-neon-green" />
  if (status === 'error')   return <AlertTriangle size={13} className="text-neon-red" />
  return <Clock size={13} className="text-slate-600" />
}

function ReportModal({ agentId, onClose }: { agentId: string; onClose: () => void }) {
  const { data: run, isLoading } = useLatestAgentRun(agentId)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-dark-800 border border-dark-600 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-dark-600">
          <h2 className="font-game font-bold text-sm tracking-wide text-slate-100">AGENT REPORT</h2>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-300 transition-colors">x</button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 size={24} className="animate-spin text-brand" />
            </div>
          ) : run ? (
            <div>
              {run.status === 'running' && (
                <div className="flex items-center gap-2 mb-4 text-neon-purple text-sm font-mono">
                  <Loader2 size={14} className="animate-spin" />
                  Agent running... auto-refresh
                </div>
              )}
              <pre className="text-sm text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                {run.report_markdown || run.summary || 'No report yet'}
              </pre>
              <p className="text-xs text-slate-700 font-mono mt-4">
                {run.started_at} · {run.triggered_by}
              </p>
            </div>
          ) : (
            <p className="text-slate-600 text-sm text-center py-8">No runs yet</p>
          )}
        </div>
      </div>
    </div>
  )
}

function AgentCard({ agent }: { agent: AgentDetail; deptColor?: string }) {
  const [showReport, setShowReport] = useState(false)
  const { mutate: trigger, isPending } = useTriggerAgent()
  const colorClass = COLOR_CLASSES[agent.color] ?? COLOR_CLASSES['brand']
  const latestRun = agent.runs[0]
  const isRunning = latestRun?.status === 'running' || isPending

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-lg p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${colorClass}`}>
            <Bot size={14} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-game font-bold text-sm text-slate-100 tracking-wide">{agent.name}</h3>
              {latestRun && (
                <span className={`flex items-center gap-1 text-xs font-mono border px-1.5 py-0.5 rounded ${colorClass}`}>
                  <StatusIcon status={latestRun.status} />
                  {latestRun.status.toUpperCase()}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">{agent.role}</p>
            <div className="flex items-center gap-3 mt-1.5">
              <span className="text-xs text-slate-700 font-mono flex items-center gap-1">
                <Clock size={10} /> {agent.schedule}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {latestRun && (
            <button
              onClick={() => setShowReport(true)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 border border-dark-600 hover:border-dark-500 px-2 py-1.5 rounded transition-all"
            >
              <FileText size={10} />
              Report
            </button>
          )}
          <button
            onClick={() => trigger(agent.id)}
            disabled={isRunning}
            className={`flex items-center gap-1 text-xs font-game font-bold tracking-wider px-2.5 py-1.5 rounded border transition-all disabled:opacity-50 ${colorClass}`}
          >
            {isRunning ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
            {isRunning ? 'RUN...' : 'RUN'}
          </button>
        </div>
      </div>

      {/* Latest run summary */}
      {latestRun?.summary && (
        <p className="text-xs text-slate-600 mt-3 font-mono line-clamp-2 border-t border-dark-700 pt-2">
          {latestRun.summary}
        </p>
      )}

      {showReport && <ReportModal agentId={agent.id} onClose={() => setShowReport(false)} />}
    </div>
  )
}

export default function DepartmentPage() {
  const { deptId } = useParams<{ deptId: string }>()
  const { data: dept, isLoading } = useDepartment(deptId ?? '')
  const { mutate: runDept, isPending: isDeptRunning } = useRunDepartment()

  if (isLoading || !dept) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={24} className="animate-spin text-brand" />
      </div>
    )
  }

  const Icon = ICON_MAP[dept.icon] ?? Building2
  const colorClass = COLOR_CLASSES[dept.color] ?? COLOR_CLASSES['brand']

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Back nav */}
      <Link to="/workplace" className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-4 transition-colors">
        <ArrowLeft size={13} />
        AI WORKPLACE
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`w-11 h-11 rounded-lg flex items-center justify-center border ${colorClass}`}>
            <Icon size={20} />
          </div>
          <div>
            <h1 className="font-game font-bold text-xl text-slate-100 tracking-wide">{dept.name_vi}</h1>
            <p className="text-xs text-slate-500">{dept.name} — {dept.description}</p>
          </div>
        </div>
        <button
          onClick={() => runDept(dept.id)}
          disabled={isDeptRunning}
          className={`flex items-center gap-1.5 text-sm font-game font-bold tracking-wider px-4 py-2 rounded border transition-all disabled:opacity-50 ${colorClass}`}
        >
          {isDeptRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {isDeptRunning ? 'RUNNING...' : 'RUN ALL'}
        </button>
      </div>

      {/* Agents */}
      <section className="mb-8">
        <h2 className="font-game font-bold text-sm text-slate-400 tracking-wider mb-3 flex items-center gap-2">
          <Bot size={14} />
          AGENTS ({dept.agents_detail?.length ?? 0})
        </h2>
        <div className="space-y-3">
          {(dept.agents_detail ?? []).map(agent => (
            <AgentCard key={agent.id} agent={agent} deptColor={dept.color} />
          ))}
        </div>
      </section>

      {/* Department Reports */}
      {dept.reports && dept.reports.length > 0 && (
        <section className="mb-8">
          <h2 className="font-game font-bold text-sm text-slate-400 tracking-wider mb-3 flex items-center gap-2">
            <FileText size={14} />
            DEPARTMENT REPORTS
          </h2>
          <div className="space-y-3">
            {dept.reports.map(report => (
              <div key={report.id} className="bg-dark-800 border border-dark-600 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-slate-400">{report.period}</span>
                  <span className="text-xs font-mono text-slate-700">
                    {new Date(report.generated_at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}
                  </span>
                </div>
                <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                  {report.report_markdown?.slice(0, 1000) || report.summary}
                </pre>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cross-Department Messages */}
      {((dept.messages_incoming?.length ?? 0) > 0 || (dept.messages_outgoing?.length ?? 0) > 0) && (
        <section>
          <h2 className="font-game font-bold text-sm text-slate-400 tracking-wider mb-3 flex items-center gap-2">
            <MessageSquare size={14} />
            MESSAGES
          </h2>
          <div className="space-y-2">
            {[...(dept.messages_incoming ?? []), ...(dept.messages_outgoing ?? [])]
              .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
              .slice(0, 10)
              .map(msg => (
                <div key={msg.id} className="bg-dark-800 border border-dark-600 rounded-lg p-3 flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-1.5 ${
                    msg.priority === 'high' ? 'bg-neon-red' :
                    msg.priority === 'medium' ? 'bg-neon-amber' : 'bg-neon-green'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                      <span>{msg.from_department}</span>
                      <span className="text-slate-700">-&gt;</span>
                      <span>{msg.to_department}</span>
                      <span className="text-slate-700">·</span>
                      <span>{msg.message_type}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {typeof msg.payload === 'object' ? JSON.stringify(msg.payload).slice(0, 200) : String(msg.payload)}
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}
    </div>
  )
}
