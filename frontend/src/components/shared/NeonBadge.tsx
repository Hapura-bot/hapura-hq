interface NeonBadgeProps {
  label: string
  color?: 'green' | 'amber' | 'red' | 'purple' | 'cyan'
  pulse?: boolean
  className?: string
}

const COLOR_MAP = {
  green:  'bg-neon-green/10  text-neon-green  border-neon-green/30',
  amber:  'bg-neon-amber/10  text-neon-amber  border-neon-amber/30',
  red:    'bg-neon-red/10    text-neon-red    border-neon-red/30',
  purple: 'bg-neon-purple/10 text-neon-purple border-neon-purple/30',
  cyan:   'bg-brand/10       text-brand       border-brand/30',
}

export function NeonBadge({ label, color = 'cyan', pulse = false, className = '' }: NeonBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono border ${COLOR_MAP[color]} ${className}`}>
      {pulse && <span className={`w-1.5 h-1.5 rounded-full bg-current animate-pulse-slow`} />}
      {label}
    </span>
  )
}
