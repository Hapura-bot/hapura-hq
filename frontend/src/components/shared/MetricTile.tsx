interface MetricTileProps {
  label: string
  value: string
  sub?: string
  color?: 'green' | 'amber' | 'purple' | 'cyan' | 'default'
}

const COLOR_MAP = {
  green:   'text-neon-green',
  amber:   'text-neon-amber',
  purple:  'text-neon-purple',
  cyan:    'text-brand',
  default: 'text-slate-200',
}

export function MetricTile({ label, value, sub, color = 'default' }: MetricTileProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-slate-500 font-mono uppercase tracking-wider">{label}</span>
      <span className={`text-lg font-mono font-bold ${COLOR_MAP[color]}`}>{value}</span>
      {sub && <span className="text-xs text-slate-600">{sub}</span>}
    </div>
  )
}
