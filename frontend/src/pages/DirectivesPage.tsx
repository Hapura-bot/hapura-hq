import { useState } from 'react'
import { FileText, CheckCircle, Clock, AlertTriangle, Loader2, Play, ChevronDown, ChevronRight } from 'lucide-react'
import { useDirectives, useApproveDirective } from '../hooks/useWorkspace'
import type { Directive } from '../hooks/useWorkspace'
import { triggerAgent } from '../api/client'

const STATUS_STYLES: Record<string, string> = {
  draft:    'text-neon-amber  border-neon-amber/30  bg-neon-amber/10',
  approved: 'text-neon-green  border-neon-green/30  bg-neon-green/10',
  active:   'text-brand       border-brand/30       bg-brand/10',
  archived: 'text-slate-600   border-slate-700      bg-slate-800/30',
}

function DirectiveCard({ directive }: { directive: Directive }) {
  const [expanded, setExpanded] = useState(directive.status === 'draft')
  const { mutate: approve, isPending } = useApproveDirective()

  return (
    <div className={`bg-dark-800 border rounded-lg overflow-hidden transition-all ${
      directive.status === 'active' ? 'border-brand/40' :
      directive.status === 'draft'  ? 'border-neon-amber/40' : 'border-dark-600'
    }`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between p-5 hover:bg-dark-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <FileText size={15} className={
            directive.status === 'active' ? 'text-brand' :
            directive.status === 'draft'  ? 'text-neon-amber' : 'text-slate-600'
          } />
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-game font-bold text-sm text-slate-100 tracking-wide">
                WEEKLY DIRECTIVE
              </span>
              <span className="text-xs font-mono text-slate-500">{directive.period}</span>
              <span className={`text-xs font-mono border px-1.5 py-0.5 rounded ${STATUS_STYLES[directive.status] ?? STATUS_STYLES['archived']}`}>
                {directive.status.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs text-slate-600 font-mono flex items-center gap-1">
                <Clock size={10} />
                {new Date(directive.generated_at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}
              </span>
              {directive.approved_by && (
                <span className="text-xs text-neon-green font-mono flex items-center gap-1">
                  <CheckCircle size={10} />
                  Approved by {directive.approved_by.split(':').pop()}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {directive.status === 'draft' && (
            <button
              onClick={(e) => { e.stopPropagation(); approve(directive.id) }}
              disabled={isPending}
              className="flex items-center gap-1.5 text-xs font-game font-bold tracking-wider px-3 py-1.5 rounded border border-neon-green/30 bg-neon-green/10 text-neon-green transition-all disabled:opacity-50"
            >
              {isPending ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle size={11} />}
              APPROVE
            </button>
          )}
          {expanded ? <ChevronDown size={14} className="text-slate-600" /> : <ChevronRight size={14} className="text-slate-600" />}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-dark-600 p-5 space-y-4">
          {/* Priorities */}
          {directive.priorities?.length > 0 && (
            <div>
              <h4 className="font-game font-bold text-xs text-slate-500 tracking-wider mb-2">TOP PRIORITIES</h4>
              <div className="space-y-1.5">
                {directive.priorities.map((p, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-brand font-mono text-xs mt-0.5">{i + 1}.</span>
                    <span className="text-sm text-slate-300">{p}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Department actions */}
          {Object.keys(directive.department_actions ?? {}).length > 0 && (
            <div>
              <h4 className="font-game font-bold text-xs text-slate-500 tracking-wider mb-2">DEPARTMENT ACTIONS</h4>
              <div className="space-y-2">
                {Object.entries(directive.department_actions).map(([dept, actions]) => (
                  <div key={dept} className="bg-dark-700 rounded p-3">
                    <span className="text-xs font-mono text-brand font-bold uppercase">{dept}</span>
                    <ul className="mt-1 space-y-1">
                      {(Array.isArray(actions) ? actions : [String(actions)]).map((a, i) => (
                        <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                          <span className="text-slate-700 mt-0.5">→</span>
                          {a}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full report */}
          {directive.directive_markdown && (
            <div>
              <h4 className="font-game font-bold text-xs text-slate-500 tracking-wider mb-2">FULL REPORT</h4>
              <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap leading-relaxed bg-dark-700 rounded p-3 max-h-64 overflow-y-auto">
                {directive.directive_markdown}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function DirectivesPage() {
  const { data: directives = [], isLoading } = useDirectives()
  const [triggering, setTriggering] = useState(false)

  async function handleRunDirector() {
    setTriggering(true)
    try {
      await triggerAgent('director')
    } finally {
      setTriggering(false)
    }
  }

  const drafts    = directives.filter(d => d.status === 'draft')
  const active    = directives.filter(d => d.status === 'active')
  const archived  = directives.filter(d => d.status === 'approved' || d.status === 'archived')

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={18} className="text-brand" />
          <h1 className="font-game font-bold text-xl text-slate-100 tracking-wide">WEEKLY DIRECTIVES</h1>
        </div>
        <button
          onClick={handleRunDirector}
          disabled={triggering}
          className="flex items-center gap-1.5 text-xs font-game font-bold tracking-wider px-3 py-2 rounded border border-brand/30 bg-brand/10 text-brand transition-all disabled:opacity-50"
        >
          {triggering ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          RUN DIRECTOR
        </button>
      </div>

      {/* Info banner */}
      <div className="bg-dark-700 border border-dark-600 rounded-lg p-4 mb-6 text-xs text-slate-500 font-mono">
        ⚡ Director Agent đọc tất cả báo cáo phòng ban → tạo Weekly Directive → CEO approve → active policy.
        Chạy Director sau khi các phòng ban đã có reports.
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 size={24} className="animate-spin text-brand" />
        </div>
      ) : directives.length === 0 ? (
        <div className="text-center py-16">
          <FileText size={40} className="text-slate-700 mx-auto mb-3" />
          <p className="text-slate-500 font-mono text-sm">Chưa có directive nào</p>
          <p className="text-slate-700 font-mono text-xs mt-1">
            Chạy Director Agent để tạo Weekly Directive đầu tiên
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Drafts — needs approval */}
          {drafts.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={13} className="text-neon-amber" />
                <span className="text-xs font-game font-bold text-neon-amber tracking-wider">
                  AWAITING APPROVAL ({drafts.length})
                </span>
              </div>
              {drafts.map(d => <DirectiveCard key={d.id} directive={d} />)}
            </div>
          )}

          {/* Active */}
          {active.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle size={13} className="text-brand" />
                <span className="text-xs font-game font-bold text-brand tracking-wider">
                  ACTIVE ({active.length})
                </span>
              </div>
              {active.map(d => <DirectiveCard key={d.id} directive={d} />)}
            </div>
          )}

          {/* History */}
          {archived.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Clock size={13} className="text-slate-600" />
                <span className="text-xs font-game font-bold text-slate-600 tracking-wider">
                  HISTORY ({archived.length})
                </span>
              </div>
              {archived.map(d => <DirectiveCard key={d.id} directive={d} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
