import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2, Crown, TrendingUp, Code2, DollarSign,
  HeartHandshake, BarChart3, Server, Play, Loader2,
  Users, CheckCircle, AlertTriangle, Clock, Smartphone, Globe, Lock,
} from 'lucide-react'
import {
  useDepartments, useRunDepartment, useAvailableProducts,
} from '../hooks/useWorkspace'
import type { Department, WorkspaceConfig } from '../hooks/useWorkspace'

const ICON_MAP: Record<string, React.ElementType> = {
  Crown, TrendingUp, Code2, DollarSign,
  HeartHandshake, BarChart3, Server,
}

const COLOR_MAP: Record<string, { border: string; bg: string; text: string; glow: string }> = {
  'neon-cyan':   { border: 'border-brand/30',       bg: 'bg-brand/10',       text: 'text-brand',       glow: 'shadow-brand/20' },
  'neon-green':  { border: 'border-neon-green/30',  bg: 'bg-neon-green/10',  text: 'text-neon-green',  glow: 'shadow-neon-green/20' },
  'neon-purple': { border: 'border-neon-purple/30', bg: 'bg-neon-purple/10', text: 'text-neon-purple', glow: 'shadow-neon-purple/20' },
  'neon-amber':  { border: 'border-neon-amber/30',  bg: 'bg-neon-amber/10',  text: 'text-neon-amber',  glow: 'shadow-neon-amber/20' },
  'neon-red':    { border: 'border-neon-red/30',    bg: 'bg-neon-red/10',    text: 'text-neon-red',    glow: 'shadow-neon-red/20' },
  'brand':       { border: 'border-brand/30',       bg: 'bg-brand/10',       text: 'text-brand',       glow: 'shadow-brand/20' },
}

const PLATFORM_ICON: Record<string, React.ElementType> = {
  android: Smartphone,
  ios: Smartphone,
  web: Globe,
}

function HealthBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-neon-green' : score >= 40 ? 'bg-neon-amber' : 'bg-neon-red'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-dark-600 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-600 w-8 text-right">{score}%</span>
    </div>
  )
}

function AgentStatusDots({ agents }: { agents: Department['agents'] }) {
  return (
    <div className="flex items-center gap-1">
      {agents.map(a => (
        <div
          key={a.id}
          title={`${a.name}: ${a.status}`}
          className={`w-2 h-2 rounded-full ${
            a.status === 'done' ? 'bg-neon-green' :
            a.status === 'running' ? 'bg-neon-purple animate-pulse' :
            a.status === 'error' ? 'bg-neon-red' :
            'bg-dark-500'
          }`}
        />
      ))}
    </div>
  )
}

function DepartmentCard({ dept, disabled }: { dept: Department; disabled?: boolean }) {
  const { mutate: run, isPending } = useRunDepartment()
  const colors = COLOR_MAP[dept.color] ?? COLOR_MAP['brand']
  const Icon = ICON_MAP[dept.icon] ?? Building2

  if (disabled) {
    return (
      <div className="block bg-dark-800/40 border border-dark-700 rounded-lg p-5 opacity-40 relative">
        <div className="absolute top-2 right-2">
          <Lock size={10} className="text-slate-700" />
        </div>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border border-dark-600 bg-dark-700">
            <Icon size={18} className="text-slate-700" />
          </div>
          <div>
            <h3 className="font-game font-bold text-sm text-slate-600 tracking-wide">{dept.name_vi}</h3>
            <p className="text-xs text-slate-700 mt-0.5">Not enabled for this product</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <Link
      to={`/workplace/${dept.id}`}
      className={`block bg-dark-800 border ${colors.border} rounded-lg p-5 hover:shadow-lg hover:${colors.glow} transition-all group`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border ${colors.border} ${colors.bg}`}>
            <Icon size={18} className={colors.text} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-game font-bold text-sm text-slate-100 tracking-wide group-hover:text-white transition-colors">
              {dept.name_vi}
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">{dept.name}</p>
          </div>
        </div>

        <button
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            run(dept.id)
          }}
          disabled={isPending}
          className={`flex items-center gap-1 text-xs font-game font-bold tracking-wider px-2.5 py-1.5 rounded border transition-all disabled:opacity-50 ${colors.border} ${colors.bg} ${colors.text}`}
        >
          {isPending ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
          RUN
        </button>
      </div>

      <p className="text-xs text-slate-500 mt-3 line-clamp-1">{dept.description}</p>

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2">
          <Users size={11} className="text-slate-600" />
          <span className="text-xs font-mono text-slate-600">
            {dept.agents_implemented}/{dept.agents_total} agents
          </span>
        </div>
        <AgentStatusDots agents={dept.agents} />
      </div>

      <div className="mt-3">
        <HealthBar score={dept.health_score} />
      </div>

      {dept.last_summary && (
        <p className="text-xs text-slate-600 mt-3 font-mono line-clamp-2 border-t border-dark-600 pt-3">
          {dept.last_summary}
        </p>
      )}

      {dept.last_summary_at && (
        <p className="text-xs text-slate-700 mt-1 font-mono">
          <Clock size={10} className="inline mr-1" />
          {new Date(dept.last_summary_at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}
        </p>
      )}
    </Link>
  )
}

function ProductSwitcher({
  products,
  selected,
  onSelect,
}: {
  products: WorkspaceConfig[]
  selected: string
  onSelect: (id: string) => void
}) {
  return (
    <div className="flex items-center gap-1 bg-dark-800 border border-dark-600 rounded-lg p-1">
      {products.map(p => {
        const PlatformIcon = PLATFORM_ICON[p.platform] ?? Globe
        const isActive = selected === p.product_id
        return (
          <button
            key={p.product_id}
            onClick={() => onSelect(p.product_id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-game font-semibold tracking-wider transition-all ${
              isActive
                ? 'bg-brand/15 text-brand border border-brand/30'
                : 'text-slate-500 hover:text-slate-300 border border-transparent'
            }`}
          >
            <PlatformIcon size={11} />
            {p.product_name}
          </button>
        )
      })}
    </div>
  )
}

export default function WorkplacePage() {
  const { data: departments = [], isLoading } = useDepartments()
  const { data: products = [] } = useAvailableProducts()
  const [selectedProductId, setSelectedProductId] = useState<string>('clippack')

  const selectedProduct = products.find(p => p.product_id === selectedProductId)
  const enabledDepts = selectedProduct?.enabled_departments ?? departments.map(d => d.id)

  const executive = departments.find(d => d.id === 'executive')
  const others = departments.filter(d => d.id !== 'executive')

  // Stats for selected product's enabled departments
  const activeDepts = departments.filter(d => enabledDepts.includes(d.id))
  const healthyCount = activeDepts.filter(d => d.health_score >= 50).length
  const attentionCount = activeDepts.filter(d => d.health_score > 0 && d.health_score < 50).length
  const notStartedCount = activeDepts.filter(d => d.health_score === 0).length

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Building2 size={18} className="text-brand" />
          <h1 className="font-game font-bold text-xl text-slate-100 tracking-wide">AI WORKPLACE</h1>
          <span className="text-xs font-mono text-slate-600 ml-2">
            {departments.length} departments · {departments.reduce((s, d) => s + d.agents_total, 0)} agents
          </span>
        </div>

        {/* Product Switcher */}
        {products.length > 0 && (
          <ProductSwitcher
            products={products}
            selected={selectedProductId}
            onSelect={setSelectedProductId}
          />
        )}
      </div>

      {/* Product info bar */}
      {selectedProduct && (
        <div className="bg-dark-700 border border-dark-600 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <CheckCircle size={13} className="text-neon-green" />
                <span className="text-xs font-mono text-slate-400">{healthyCount} active</span>
              </div>
              <div className="flex items-center gap-1.5">
                <AlertTriangle size={13} className="text-neon-amber" />
                <span className="text-xs font-mono text-slate-400">{attentionCount} needs attention</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock size={13} className="text-slate-600" />
                <span className="text-xs font-mono text-slate-400">{notStartedCount} not started</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs font-mono text-slate-500">{selectedProduct.meta?.current_phase}</p>
              <p className="text-xs font-mono text-slate-700 mt-0.5">{selectedProduct.meta?.goal}</p>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 size={24} className="animate-spin text-brand" />
        </div>
      ) : (
        <>
          {/* Executive (full width) */}
          {executive && (
            <div className="mb-4">
              <DepartmentCard dept={executive} disabled={!enabledDepts.includes(executive.id)} />
            </div>
          )}

          {/* Departments grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {others.map(dept => (
              <DepartmentCard
                key={dept.id}
                dept={dept}
                disabled={!enabledDepts.includes(dept.id)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
