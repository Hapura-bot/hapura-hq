import { useState } from 'react'
import { Bot, Play, Clock, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { useAgents, useTriggerAgent, useLatestAgentRun } from '../hooks/useAgents'
import type { AgentMeta } from '../api/client'

const COLOR_CLASSES: Record<string, string> = {
  'neon-green':  'text-neon-green  border-neon-green/30  bg-neon-green/10',
  'neon-purple': 'text-neon-purple border-neon-purple/30 bg-neon-purple/10',
  'neon-amber':  'text-neon-amber  border-neon-amber/30  bg-neon-amber/10',
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
          <button onClick={onClose} className="text-slate-600 hover:text-slate-300 transition-colors">✕</button>
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
                  Agent đang chạy... tự động refresh
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
            <p className="text-slate-600 text-sm text-center py-8">Chưa có run nào</p>
          )}
        </div>
      </div>
    </div>
  )
}

function AgentCard({ agent }: { agent: AgentMeta }) {
  const [showReport, setShowReport] = useState(false)
  const { mutate: trigger, isPending } = useTriggerAgent()
  const colorClass = COLOR_CLASSES[agent.color] ?? COLOR_CLASSES['brand']
  const isRunning = agent.last_run_status === 'running' || isPending

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-lg p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          {/* Icon */}
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border ${colorClass}`}>
            <Bot size={15} />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-game font-bold text-sm text-slate-100 tracking-wide">{agent.name}</h3>
              <span className={`flex items-center gap-1 text-xs font-mono border px-1.5 py-0.5 rounded ${colorClass}`}>
                <StatusIcon status={agent.last_run_status} />
                {agent.last_run_status === 'never' ? 'IDLE' : agent.last_run_status.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{agent.role}</p>

            {agent.last_run_summary && agent.last_run_status !== 'never' && (
              <p className="text-xs text-slate-600 mt-1.5 font-mono line-clamp-2">
                {agent.last_run_summary}
              </p>
            )}

            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs text-slate-700 font-mono flex items-center gap-1">
                <Clock size={10} /> {agent.schedule}
              </span>
              {agent.last_run_at && (
                <span className="text-xs text-slate-700 font-mono">
                  Last: {new Date(agent.last_run_at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {agent.last_run_id && (
            <button
              onClick={() => setShowReport(true)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 border border-dark-600 hover:border-dark-500 px-2 py-1.5 rounded transition-all"
            >
              Report
            </button>
          )}
          <button
            onClick={() => trigger(agent.id)}
            disabled={isRunning}
            className={`flex items-center gap-1.5 text-xs font-game font-bold tracking-wider px-3 py-1.5 rounded border transition-all disabled:opacity-50 ${colorClass}`}
          >
            {isRunning ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
            {isRunning ? 'RUNNING' : 'RUN'}
          </button>
        </div>
      </div>

      {showReport && <ReportModal agentId={agent.id} onClose={() => setShowReport(false)} />}
    </div>
  )
}

export default function AgentCouncilPage() {
  const { data: agents = [], isLoading } = useAgents()

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="mb-6 flex items-center gap-2">
        <Bot size={18} className="text-neon-purple" />
        <h1 className="font-game font-bold text-xl text-slate-100 tracking-wide">AI WAR COUNCIL</h1>
      </div>

      <div className="bg-dark-700 border border-dark-600 rounded-lg p-4 mb-6 text-xs text-slate-500 font-mono">
        ⚡ Cần backend đang chạy + OpenAI/Vertex Key config để agents hoạt động.
        Telegram alerts tự động gửi sau mỗi run.
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 size={24} className="animate-spin text-brand" />
        </div>
      ) : (
        <div className="space-y-3">
          {agents.map(agent => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  )
}
