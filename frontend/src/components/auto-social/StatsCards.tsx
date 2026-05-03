import { useAutoSocialStats } from '../../hooks/useAutoSocial'

function Card({ label, value, accent }: { label: string; value: number | string; accent?: string }) {
  return (
    <div className="bg-dark-800 border border-dark-600 rounded p-4">
      <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${accent ?? 'text-slate-200'}`}>{value}</div>
    </div>
  )
}

export function StatsCards() {
  const { data, isLoading } = useAutoSocialStats()
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-dark-800 border border-dark-600 rounded p-4 animate-pulse h-20" />
        ))}
      </div>
    )
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card label="Pending" value={data.pending} accent="text-slate-300" />
      <Card label="Queued" value={data.queued} accent="text-blue-300" />
      <Card label="Posted (7d)" value={data.posted_last_7d} accent="text-emerald-300" />
      <Card label="Failed" value={data.failed} accent="text-red-300" />
    </div>
  )
}
