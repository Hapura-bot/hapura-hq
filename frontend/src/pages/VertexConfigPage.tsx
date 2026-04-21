import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Zap, Plus, RefreshCw, TestTube2, Pencil, Trash2, RotateCcw,
  ChevronRight, Clock, CheckCircle2, AlertTriangle, Loader2,
  Copy, X,
} from 'lucide-react'
import {
  vcApi,
  type VertexConfigDoc,
  type EndpointConfig,
  type ModelEntry,
  type ReloadWebhook,
  type VertexConfigUpdate,
  DEFAULT_WEBHOOK,
} from '../api/vertexConfig'

// ─── Sub-components ──────────────────────────────────────────────────────────

function HealthBadge({ doc }: { doc: VertexConfigDoc }) {
  if (!doc.updated_at) return <span className="badge-gray text-xs px-2 py-0.5 rounded-full border border-dark-500 text-slate-600">no sync</span>
  const mins = (Date.now() - new Date(doc.updated_at).getTime()) / 60000
  if (mins < 2) return <span className="text-xs px-2 py-0.5 rounded-full bg-neon-green/10 border border-neon-green/25 text-neon-green font-semibold">healthy</span>
  if (mins < 10) return <span className="text-xs px-2 py-0.5 rounded-full bg-neon-amber/10 border border-neon-amber/25 text-neon-amber font-semibold">stale</span>
  return <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/40 border border-dark-500 text-slate-500 font-semibold">old</span>
}

function SyncDot({ doc }: { doc: VertexConfigDoc }) {
  if (!doc.updated_at) return <span className="inline-block w-2 h-2 rounded-full bg-slate-700 mr-1.5" />
  const mins = (Date.now() - new Date(doc.updated_at).getTime()) / 60000
  if (mins < 2) return <span className="inline-block w-2 h-2 rounded-full bg-neon-green animate-pulse mr-1.5" />
  if (mins < 10) return <span className="inline-block w-2 h-2 rounded-full bg-neon-amber mr-1.5" />
  return <span className="inline-block w-2 h-2 rounded-full bg-slate-600 mr-1.5" />
}

function relativeTime(iso: string): string {
  if (!iso) return '—'
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

// ─── Toast ────────────────────────────────────────────────────────────────────

type ToastType = 'success' | 'error' | 'info'
interface Toast { id: number; msg: string; type: ToastType }

function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = (msg: string, type: ToastType = 'success') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }
  return { toasts, push }
}

function ToastContainer({ toasts }: { toasts: Toast[] }) {
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl text-sm font-medium
            ${t.type === 'success' ? 'bg-dark-700 border-neon-green/30 text-neon-green' : ''}
            ${t.type === 'error'   ? 'bg-dark-700 border-neon-red/30 text-neon-red'   : ''}
            ${t.type === 'info'    ? 'bg-dark-700 border-brand/30 text-brand'          : ''}
          `}
        >
          {t.type === 'success' && <CheckCircle2 size={14} />}
          {t.type === 'error'   && <AlertTriangle size={14} />}
          {t.type === 'info'    && <Zap size={14} />}
          {t.msg}
        </div>
      ))}
    </div>
  )
}

// ─── Add Project Modal ────────────────────────────────────────────────────────

function AddProjectModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (token: string, projectId: string) => void
}) {
  const qc = useQueryClient()
  const [step, setStep] = useState(1)
  const [projectId, setProjectId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [baseUrl, setBaseUrl] = useState('https://vertex-key.com/api/v1')
  const [apiKeyRef, setApiKeyRef] = useState('')
  const [modelKey, setModelKey] = useState('')
  const [modelVal, setModelVal] = useState('omega/claude-haiku-4-5-20251001')
  const [createdToken, setCreatedToken] = useState('')

  const create = useMutation({
    mutationFn: () =>
      vcApi.create({
        project_id: projectId.trim(),
        display_name: displayName.trim(),
        endpoints: { default: { base_url: baseUrl.trim(), api_key_ref: apiKeyRef.trim() } },
        models: modelKey.trim()
          ? { [modelKey.trim()]: { value: modelVal.trim(), endpoint: 'default' } }
          : {},
        env_map: modelKey.trim()
          ? { [`${modelKey.trim()}`]: `models.${modelKey.trim()}.value` }
          : {},
        reload_webhook: DEFAULT_WEBHOOK,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['vertex-configs'] })
      setCreatedToken(data.client_token)
      setStep(3)
    },
  })

  const sdkSnippet = `# .env
VERTEX_CONFIG_HUB_URL=https://hq.hapura.vn/api/v1
VERTEX_CONFIG_PROJECT_ID=${projectId || 'your-project'}
VERTEX_CONFIG_TOKEN=${createdToken || 'hpv-xxxxxxxxxxxx'}

# main.py
from vertex_config_client import vertex_config

@app.on_event("startup")
async def startup():
    vertex_config.bootstrap("${projectId || 'your-project'}")`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-dark-800 border border-dark-600 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-dark-600">
          <h2 className="font-game font-bold text-sm tracking-wider text-slate-100">
            REGISTER NEW PROJECT
          </h2>
          <div className="flex items-center gap-1.5">
            {[1,2,3].map(s => (
              <div
                key={s}
                className={`rounded-full transition-all ${
                  step === s ? 'w-5 h-2 bg-brand' :
                  step > s  ? 'w-2 h-2 bg-neon-green' :
                               'w-2 h-2 bg-dark-500'
                }`}
              />
            ))}
          </div>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-300"><X size={16} /></button>
        </div>

        <div className="p-5 flex-1">
          {step === 1 && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-slate-500">Project identity</p>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400">Project ID (slug)</label>
                <input
                  className="input-field font-mono text-xs"
                  value={projectId}
                  onChange={e => setProjectId(e.target.value)}
                  placeholder="my-new-project"
                />
                <p className="text-xs text-slate-600">Dùng làm Firestore doc ID và SDK param</p>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400">Display Name</label>
                <input
                  className="input-field"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  placeholder="My New Service"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-slate-500">Default endpoint &amp; model</p>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400">Base URL</label>
                <input className="input-field font-mono text-xs" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400">API Key (Secret Manager ref)</label>
                <input className="input-field font-mono text-xs" value={apiKeyRef} onChange={e => setApiKeyRef(e.target.value)} placeholder="MY_API_KEY" />
                <p className="text-xs text-slate-600">Tên secret trong GCP Secret Manager, không phải raw key</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-400">Model env key (optional)</label>
                  <input className="input-field font-mono text-xs" value={modelKey} onChange={e => setModelKey(e.target.value)} placeholder="MY_MODEL" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-400">Model string</label>
                  <input className="input-field font-mono text-xs" value={modelVal} onChange={e => setModelVal(e.target.value)} />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-neon-green text-sm font-semibold">
                <CheckCircle2 size={16} /> Project registered!
              </div>
              <div className="bg-dark-900/60 border border-dark-500 rounded-lg p-3">
                <p className="text-xs text-slate-500 mb-2">Copy snippet này vào backend/ của project:</p>
                <pre className="text-[11px] font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {sdkSnippet}
                </pre>
              </div>
              <button
                className="flex items-center gap-1.5 text-xs text-brand hover:text-brand/80 transition-colors"
                onClick={() => { navigator.clipboard.writeText(sdkSnippet) }}
              >
                <Copy size={12} /> Copy snippet
              </button>
              <p className="text-xs text-neon-amber">
                ⚠ Token chỉ hiển thị 1 lần. Lưu vào Cloud Run secret ngay.
              </p>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-dark-600 flex justify-end gap-2">
          {step < 3 && (
            <>
              <button className="btn-ghost text-xs px-3 py-1.5" onClick={onClose}>Cancel</button>
              {step === 1 && (
                <button
                  className="btn-primary text-xs px-4 py-1.5"
                  disabled={!projectId.trim() || !displayName.trim()}
                  onClick={() => setStep(2)}
                >
                  Next →
                </button>
              )}
              {step === 2 && (
                <button
                  className="btn-primary text-xs px-4 py-1.5"
                  disabled={create.isPending}
                  onClick={() => create.mutate()}
                >
                  {create.isPending ? <Loader2 size={12} className="animate-spin" /> : 'Register →'}
                </button>
              )}
            </>
          )}
          {step === 3 && (
            <button
              className="btn-primary text-xs px-4 py-1.5"
              onClick={() => { onCreated(createdToken, projectId); onClose() }}
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Test Result Panel ────────────────────────────────────────────────────────

function TestPanel({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const test = useMutation({ mutationFn: () => vcApi.test(projectId) })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-dark-800 border border-dark-600 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-dark-600">
          <h3 className="font-game font-bold text-xs tracking-wider text-slate-200 flex items-center gap-2">
            <TestTube2 size={13} className="text-brand" /> TEST CONNECTION — {projectId}
          </h3>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-300"><X size={14} /></button>
        </div>
        <div className="p-4">
          {!test.data && !test.isPending && (
            <p className="text-xs text-slate-500 font-mono mb-4">
              # Click bên dưới để ping default endpoint với model đầu tiên
            </p>
          )}
          {test.isPending && (
            <div className="flex items-center gap-2 text-brand text-xs font-mono mb-4">
              <Loader2 size={12} className="animate-spin" /> Testing…
            </div>
          )}
          {test.data && (
            <div className="font-mono text-xs leading-6 mb-4">
              {test.data.ok ? (
                <>
                  <div className="text-neon-green">✓ endpoint: {test.data.endpoint}</div>
                  <div className="text-neon-green">✓ model: {test.data.model}</div>
                  <div className="text-neon-green">✓ latency: {test.data.latency_ms}ms</div>
                  <div className="text-neon-green">✓ sample: "{test.data.sample}"</div>
                </>
              ) : (
                <div className="text-neon-red">✗ {test.data.error}</div>
              )}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button className="btn-ghost text-xs px-3 py-1.5" onClick={onClose}>Close</button>
            <button
              className="btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5"
              onClick={() => test.mutate()}
              disabled={test.isPending}
            >
              {test.isPending ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
              Run Test
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── History Sidebar ──────────────────────────────────────────────────────────

function HistorySidebar({
  projectId,
  currentRev,
  onClose,
  onRolledBack,
}: {
  projectId: string
  currentRev: number
  onClose: () => void
  onRolledBack: () => void
}) {
  const qc = useQueryClient()
  const { data: history = [], isLoading } = useQuery({
    queryKey: ['vertex-history', projectId],
    queryFn: () => vcApi.history(projectId),
  })

  const rollback = useMutation({
    mutationFn: (rev: number) => vcApi.rollback(projectId, rev),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vertex-configs'] })
      qc.invalidateQueries({ queryKey: ['vertex-history', projectId] })
      onRolledBack()
      onClose()
    },
  })

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-80 bg-dark-800 border-l border-dark-600 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between p-4 border-b border-dark-600">
        <h3 className="font-game font-bold text-xs tracking-wider text-slate-200">REVISION HISTORY</h3>
        <button onClick={onClose} className="text-slate-600 hover:text-slate-300"><X size={14} /></button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-10">
            <Loader2 size={18} className="animate-spin text-brand" />
          </div>
        )}
        {history.map(h => (
          <div
            key={h.revision}
            className={`p-4 border-b border-dark-700 ${h.revision === currentRev ? 'bg-brand/5 border-l-2 border-l-brand' : ''}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${h.revision === currentRev ? 'bg-brand' : 'bg-slate-600'}`} />
                v{h.revision}
                {h.revision === currentRev && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand/15 border border-brand/30 text-brand">current</span>
                )}
              </span>
              <span className="text-[10px] text-slate-600 font-mono">{relativeTime(h.updated_at)}</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">{h.updated_by}</p>
            {h.revision !== currentRev && (
              <button
                className="mt-2 text-[11px] px-2 py-0.5 rounded border border-dark-500 text-slate-400 hover:border-brand/40 hover:text-brand transition-all flex items-center gap-1"
                onClick={() => rollback.mutate(h.revision)}
                disabled={rollback.isPending}
              >
                <RotateCcw size={10} /> Rollback to v{h.revision}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Project Editor ───────────────────────────────────────────────────────────

function ProjectEditor({
  doc,
  onBack,
  push,
}: {
  doc: VertexConfigDoc
  onBack: () => void
  push: (msg: string, type?: 'success' | 'error' | 'info') => void
}) {
  const qc = useQueryClient()
  const [showHistory, setShowHistory] = useState(false)
  const [showTest, setShowTest] = useState(false)

  // Local editable state
  const [endpoints, setEndpoints] = useState<Record<string, EndpointConfig>>({ ...doc.endpoints })
  const [models, setModels] = useState<Record<string, ModelEntry>>({ ...doc.models })
  const [envMap, setEnvMap] = useState<Record<string, string>>({ ...doc.env_map })
  const [webhook, setWebhook] = useState<ReloadWebhook>({ ...doc.reload_webhook })
  const [displayName, setDisplayName] = useState(doc.display_name)

  const dirty = JSON.stringify({ endpoints, models, envMap, webhook, displayName })
    !== JSON.stringify({ endpoints: doc.endpoints, models: doc.models, envMap: doc.env_map, webhook: doc.reload_webhook, displayName: doc.display_name })

  const update = useMutation({
    mutationFn: () => vcApi.update(doc.project_id, {
      display_name: displayName,
      endpoints,
      models,
      env_map: envMap,
      reload_webhook: webhook,
    } as VertexConfigUpdate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vertex-configs'] })
      push(`Saved · v${doc.revision + 1}`, 'success')
      onBack()
    },
    onError: (e: Error) => push(e.message, 'error'),
  })

  const reload = useMutation({
    mutationFn: () => vcApi.reload(doc.project_id),
    onSuccess: (r) => r.ok
      ? push('Reload webhook sent ✓', 'success')
      : push(`Reload failed: ${r.error}`, 'error'),
  })

  const endpointKeys = Object.keys(endpoints)

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-600">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1 font-mono">
            <button onClick={onBack} className="hover:text-slate-300 transition-colors">⚡ Vertex Config</button>
            <ChevronRight size={12} />
            <span className="text-slate-200 font-semibold">{doc.project_id}</span>
            <HealthBadge doc={doc} />
          </div>
          <input
            className="bg-transparent text-slate-100 font-game font-bold text-base tracking-wide outline-none border-b border-transparent focus:border-brand/50 transition-colors"
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5" onClick={onBack}>← Back</button>
          <button
            className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5"
            onClick={() => setShowHistory(true)}
          >
            <Clock size={12} /> History
          </button>
          <button
            className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5"
            onClick={() => setShowTest(true)}
          >
            <TestTube2 size={12} /> Test
          </button>
          <button
            className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5"
            disabled={reload.isPending}
            onClick={() => reload.mutate()}
          >
            <RefreshCw size={12} className={reload.isPending ? 'animate-spin' : ''} /> Reload
          </button>
          <button
            className="btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5 disabled:opacity-50"
            disabled={!dirty || update.isPending}
            onClick={() => update.mutate()}
          >
            {update.isPending ? <Loader2 size={11} className="animate-spin" /> : null}
            {dirty ? 'Save changes' : 'Saved'}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {dirty && (
          <div className="flex items-center gap-2 text-xs text-neon-amber font-medium px-3 py-2 rounded-lg bg-neon-amber/5 border border-neon-amber/20">
            <AlertTriangle size={12} /> Unsaved changes
          </div>
        )}

        {/* Endpoints */}
        <section className="card-section">
          <div className="section-header">
            <span>🌐 Endpoints</span>
            <button
              className="text-xs text-brand hover:text-brand/70 flex items-center gap-1 transition-colors"
              onClick={() => setEndpoints(p => ({ ...p, [`ep${Object.keys(p).length + 1}`]: { base_url: 'https://vertex-key.com/api/v1', api_key_ref: '' } }))}
            >
              <Plus size={11} /> Add endpoint
            </button>
          </div>
          <div className="section-body space-y-3">
            {endpointKeys.map(key => (
              <div key={key} className="bg-dark-900/60 border border-dark-500 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand/10 border border-brand/25 text-brand font-bold uppercase tracking-wider">
                    {key}
                  </span>
                  {endpointKeys.length > 1 && (
                    <button
                      className="ml-auto text-slate-600 hover:text-neon-red transition-colors"
                      onClick={() => setEndpoints(p => { const n = { ...p }; delete n[key]; return n })}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Base URL</label>
                    <input
                      className="input-field font-mono text-xs"
                      value={endpoints[key].base_url}
                      onChange={e => setEndpoints(p => ({ ...p, [key]: { ...p[key], base_url: e.target.value } }))}
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">API Key (Secret ref)</label>
                    <input
                      className="input-field font-mono text-xs"
                      value={endpoints[key].api_key_ref}
                      onChange={e => setEndpoints(p => ({ ...p, [key]: { ...p[key], api_key_ref: e.target.value } }))}
                      placeholder="MY_API_KEY"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Models */}
        <section className="card-section">
          <div className="section-header">
            <span>🤖 Models</span>
            <button
              className="text-xs text-brand hover:text-brand/70 flex items-center gap-1 transition-colors"
              onClick={() => setModels(p => ({ ...p, NEW_MODEL: { value: 'omega/claude-haiku-4-5-20251001', endpoint: 'default' } }))}
            >
              <Plus size={11} /> Add model
            </button>
          </div>
          <div className="section-body">
            {Object.keys(models).length === 0 && (
              <p className="text-xs text-slate-600">No models configured. Click + to add.</p>
            )}
            <div className="space-y-2">
              {Object.entries(models).map(([mkey, mval]) => (
                <div key={mkey} className="grid grid-cols-[1.2fr_1.8fr_0.8fr_20px] gap-2 items-center">
                  <input
                    className="input-field font-mono text-xs"
                    value={mkey}
                    onChange={e => {
                      const newKey = e.target.value
                      setModels(p => {
                        const n: Record<string, ModelEntry> = {}
                        for (const k in p) n[k === mkey ? newKey : k] = p[k]
                        return n
                      })
                    }}
                  />
                  <input
                    className="input-field font-mono text-xs"
                    value={mval.value}
                    onChange={e => setModels(p => ({ ...p, [mkey]: { ...p[mkey], value: e.target.value } }))}
                  />
                  <select
                    className="input-field text-xs bg-dark-700"
                    value={mval.endpoint}
                    onChange={e => setModels(p => ({ ...p, [mkey]: { ...p[mkey], endpoint: e.target.value } }))}
                  >
                    {endpointKeys.map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                  <button
                    className="text-slate-600 hover:text-neon-red transition-colors"
                    onClick={() => setModels(p => { const n = { ...p }; delete n[mkey]; return n })}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
            {Object.keys(models).length > 0 && (
              <div className="grid grid-cols-[1.2fr_1.8fr_0.8fr_20px] gap-2 mt-1 px-0.5">
                <p className="text-[10px] text-slate-600">ENV KEY</p>
                <p className="text-[10px] text-slate-600">MODEL STRING</p>
                <p className="text-[10px] text-slate-600">ENDPOINT</p>
                <div />
              </div>
            )}
          </div>
        </section>

        {/* Env Map */}
        <section className="card-section">
          <div className="section-header">
            <span>
              🗺 Env Map
              <span className="text-[10px] text-slate-600 font-normal ml-2">biến cũ trong code → hub field</span>
            </span>
            <button
              className="text-xs text-brand hover:text-brand/70 flex items-center gap-1 transition-colors"
              onClick={() => setEnvMap(p => ({ ...p, NEW_VAR: '' }))}
            >
              <Plus size={11} /> Add
            </button>
          </div>
          <div className="section-body">
            {Object.keys(envMap).length === 0 && (
              <p className="text-xs text-slate-600">No env mappings. SDK will use model keys directly.</p>
            )}
            <div className="space-y-2">
              {Object.entries(envMap).map(([varName, fieldPath]) => (
                <div key={varName} className="grid grid-cols-[1fr_16px_1fr_20px] gap-2 items-center">
                  <input
                    className="input-field font-mono text-xs"
                    value={varName}
                    onChange={e => {
                      const newVar = e.target.value
                      setEnvMap(p => {
                        const n: Record<string, string> = {}
                        for (const k in p) n[k === varName ? newVar : k] = p[k]
                        return n
                      })
                    }}
                  />
                  <span className="text-slate-600 text-center text-xs">→</span>
                  <input
                    className="input-field font-mono text-xs"
                    value={fieldPath}
                    onChange={e => setEnvMap(p => ({ ...p, [varName]: e.target.value }))}
                    placeholder="endpoints.default.base_url"
                  />
                  <button
                    className="text-slate-600 hover:text-neon-red transition-colors"
                    onClick={() => setEnvMap(p => { const n = { ...p }; delete n[varName]; return n })}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Reload Webhook */}
        <section className="card-section">
          <div className="section-header">
            <span>🔔 Reload Webhook</span>
            {webhook.url ? (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-neon-green/10 border border-neon-green/25 text-neon-green">Configured</span>
            ) : (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-dark-600 border border-dark-500 text-slate-600">Not set</span>
            )}
          </div>
          <div className="section-body">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Webhook URL</label>
                <input
                  className="input-field font-mono text-xs"
                  value={webhook.url}
                  onChange={e => setWebhook(p => ({ ...p, url: e.target.value }))}
                  placeholder="https://myservice.run.app/admin/reload-vertex-config"
                />
                <p className="text-[10px] text-slate-600">POST endpoint, auth by client_token</p>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Auth</label>
                <p className="text-[11px] text-slate-400 py-1">
                  Hub posts <code className="text-cyan-400">Authorization: Bearer &lt;client_token&gt;</code>.<br />
                  Consumer checks it against <code className="text-cyan-400">VERTEX_CONFIG_TOKEN</code> env var.
                </p>
              </div>
            </div>
          </div>
        </section>

        <div className="h-4" />
      </div>

      {showTest && <TestPanel projectId={doc.project_id} onClose={() => setShowTest(false)} />}
      {showHistory && (
        <HistorySidebar
          projectId={doc.project_id}
          currentRev={doc.revision}
          onClose={() => setShowHistory(false)}
          onRolledBack={() => push('Rolled back ✓', 'success')}
        />
      )}
    </>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function VertexConfigPage() {
  const qc = useQueryClient()
  const { toasts, push } = useToasts()
  const [editingDoc, setEditingDoc] = useState<VertexConfigDoc | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [testProjectId, setTestProjectId] = useState<string | null>(null)

  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['vertex-configs'],
    queryFn: vcApi.list,
    refetchInterval: 30_000,
  })

  const remove = useMutation({
    mutationFn: (id: string) => vcApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vertex-configs'] }); push('Project removed', 'info') },
    onError: (e: Error) => push(e.message, 'error'),
  })

  const reload = useMutation({
    mutationFn: (id: string) => vcApi.reload(id),
    onSuccess: (r, id) => r.ok ? push(`${id} reload sent ✓`) : push(`${id}: ${r.error}`, 'error'),
  })

  const healthy = configs.filter(c => {
    if (!c.updated_at) return false
    return (Date.now() - new Date(c.updated_at).getTime()) < 2 * 60 * 1000
  }).length

  // ── Editor view ──
  if (editingDoc) {
    return (
      <div className="flex flex-col h-full">
        <ProjectEditor
          doc={editingDoc}
          onBack={() => { setEditingDoc(null); qc.invalidateQueries({ queryKey: ['vertex-configs'] }) }}
          push={push}
        />
        <ToastContainer toasts={toasts} />
      </div>
    )
  }

  // ── List view ──
  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="px-6 py-5 border-b border-dark-600 flex items-start justify-between">
        <div>
          <h1 className="font-game font-bold text-lg text-slate-100 flex items-center gap-2">
            <Zap size={18} className="text-brand" /> VERTEX CONFIG HUB
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Một nơi cập nhật endpoint &amp; model. Consumer projects pull mới sau ≤ 60s.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5"
            onClick={() => qc.invalidateQueries({ queryKey: ['vertex-configs'] })}
          >
            <RefreshCw size={12} /> Refresh
          </button>
          <button
            className="btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5"
            onClick={() => setShowAdd(true)}
          >
            <Plus size={12} /> New Project
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="px-6 py-4 grid grid-cols-4 gap-4 border-b border-dark-700">
        {[
          { label: 'Projects', value: configs.length, color: 'text-slate-200' },
          { label: 'Healthy', value: healthy, color: 'text-neon-green' },
          { label: 'Stale / Other', value: configs.length - healthy, color: 'text-neon-amber' },
          { label: 'With Webhook', value: configs.filter(c => c.reload_webhook?.url).length, color: 'text-brand' },
        ].map(s => (
          <div key={s.label} className="bg-dark-800 border border-dark-600 rounded-xl p-4">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto px-6 py-5">
        <div className="bg-dark-800 border border-dark-600 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dark-600">
                {['Project', 'Revision', 'Endpoints / Models', 'Updated', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={5} className="px-4 py-10 text-center">
                  <Loader2 size={20} className="animate-spin text-brand mx-auto" />
                </td></tr>
              )}
              {!isLoading && configs.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-xs text-slate-600">
                  No projects yet. Click + New Project to register one.
                </td></tr>
              )}
              {configs.map(cfg => (
                <tr
                  key={cfg.project_id}
                  className="border-b border-dark-700 hover:bg-dark-700/40 transition-colors cursor-pointer"
                  onClick={() => setEditingDoc(cfg)}
                >
                  <td className="px-4 py-3.5">
                    <p className="font-semibold text-slate-100 text-sm">{cfg.project_id}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{cfg.display_name}</p>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <SyncDot doc={cfg} />
                      <span className="text-sm font-bold text-slate-200">v{cfg.revision}</span>
                    </div>
                    <HealthBadge doc={cfg} />
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-wrap gap-1 mb-1">
                      {Object.keys(cfg.endpoints).map(k => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded border border-dark-500 text-slate-500">
                          {k}
                        </span>
                      ))}
                    </div>
                    <p className="text-xs text-slate-600">
                      {Object.keys(cfg.models).length} model{Object.keys(cfg.models).length !== 1 ? 's' : ''}
                    </p>
                  </td>
                  <td className="px-4 py-3.5">
                    <p className="text-xs text-slate-300">{relativeTime(cfg.updated_at)}</p>
                    <p className="text-[10px] text-slate-600 mt-0.5 truncate max-w-[120px]">{cfg.updated_by}</p>
                  </td>
                  <td className="px-4 py-3.5" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-1">
                      <button
                        className="btn-ghost text-[11px] px-2 py-1 flex items-center gap-1"
                        onClick={() => setEditingDoc(cfg)}
                      >
                        <Pencil size={10} /> Edit
                      </button>
                      <button
                        className="btn-ghost text-[11px] px-2 py-1 flex items-center gap-1"
                        onClick={() => setTestProjectId(cfg.project_id)}
                      >
                        <TestTube2 size={10} /> Test
                      </button>
                      <button
                        className="btn-ghost text-[11px] px-2 py-1 flex items-center gap-1"
                        onClick={() => reload.mutate(cfg.project_id)}
                        disabled={reload.isPending}
                      >
                        <RefreshCw size={10} className={reload.isPending ? 'animate-spin' : ''} />
                      </button>
                      <button
                        className="btn-ghost text-[11px] px-2 py-1 text-slate-600 hover:text-neon-red"
                        onClick={() => {
                          if (confirm(`Delete ${cfg.project_id}?`)) remove.mutate(cfg.project_id)
                        }}
                      >
                        <Trash2 size={10} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* SDK Snippet */}
        <div className="mt-5 bg-dark-800 border border-dark-600 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
            <span className="text-xs font-semibold text-slate-300">📦 SDK — thêm project mới trong 3 bước</span>
          </div>
          <div className="px-4 py-4 font-mono text-[11px] leading-relaxed text-slate-400 bg-dark-900/40">
            <span className="text-slate-600"># 1. Copy vertex_config_client.py vào backend/</span><br/>
            <span className="text-slate-600"># 2. Trong main.py:</span><br/>
            <span className="text-brand">from</span> vertex_config_client <span className="text-brand">import</span> vertex_config<br/><br/>
            <span className="text-neon-green">@app.on_event</span>(<span className="text-neon-amber">"startup"</span>)<br/>
            <span className="text-brand">async def</span> <span className="text-neon-purple">startup</span>():<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;vertex_config.<span className="text-neon-purple">bootstrap</span>(<span className="text-neon-amber">"my-project"</span>)<br/><br/>
            <span className="text-slate-600"># 3. Thay os.getenv:</span><br/>
            base_url = vertex_config.<span className="text-neon-purple">get</span>(<span className="text-neon-amber">"OPENAI_BASE_URL"</span>)
          </div>
        </div>
      </div>

      {showAdd && <AddProjectModal onClose={() => setShowAdd(false)} onCreated={() => {}} />}
      {testProjectId && <TestPanel projectId={testProjectId} onClose={() => setTestProjectId(null)} />}
      <ToastContainer toasts={toasts} />
    </div>
  )
}
