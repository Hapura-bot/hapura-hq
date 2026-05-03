import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useAutoSocialPosts } from '../../hooks/useAutoSocial'
import type { AutoSocialPost, PostStatus } from '../../api/autoSocial'
import { StatusBadge } from './StatusBadge'

const DOT_COLORS: Record<PostStatus, string> = {
  pending: 'bg-slate-500',
  uploading: 'bg-yellow-400',
  queued: 'bg-blue-400',
  posted: 'bg-emerald-400',
  failed: 'bg-red-400',
  cancelled: 'bg-slate-700',
}

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1)
}

function dayKey(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function postDayKey(p: AutoSocialPost): string {
  // Convert UTC ISO to local date in ICT — simplified: use Asia/Ho_Chi_Minh
  const d = new Date(p.schedule_time)
  // Use Intl to format in ICT and extract YYYY-MM-DD
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric', month: '2-digit', day: '2-digit',
  })
  return fmt.format(d)
}

export function PostsCalendar() {
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()))

  const monthStart = startOfMonth(cursor)
  const monthEnd = addMonths(monthStart, 1)
  // Pad to start of week (Mon=1) — show Sun-Sat columns; align with Sun=0
  const gridStart = new Date(monthStart)
  gridStart.setDate(monthStart.getDate() - monthStart.getDay())
  const days: Date[] = []
  for (let i = 0; i < 42; i++) {
    days.push(new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i))
  }

  const { data: posts } = useAutoSocialPosts({
    schedule_from: monthStart.toISOString(),
    schedule_to: monthEnd.toISOString(),
    descending: false,
  })

  const byDay = useMemo(() => {
    const map = new Map<string, AutoSocialPost[]>()
    for (const p of posts ?? []) {
      const k = postDayKey(p)
      if (!map.has(k)) map.set(k, [])
      map.get(k)!.push(p)
    }
    return map
  }, [posts])

  const [selected, setSelected] = useState<string | null>(null)
  const selectedPosts = selected ? byDay.get(selected) ?? [] : []

  const monthLabel = cursor.toLocaleString('vi-VN', { month: 'long', year: 'numeric' })

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-game text-sm tracking-widest text-slate-400">{monthLabel.toUpperCase()}</h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCursor(addMonths(cursor, -1))}
            className="p-1 text-slate-500 hover:text-slate-200 border border-dark-600 rounded"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={() => setCursor(startOfMonth(new Date()))}
            className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-slate-500 hover:text-slate-200 border border-dark-600 rounded"
          >
            Today
          </button>
          <button
            onClick={() => setCursor(addMonths(cursor, 1))}
            className="p-1 text-slate-500 hover:text-slate-200 border border-dark-600 rounded"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 text-[10px] font-mono uppercase tracking-widest text-slate-600">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <div key={d} className="px-1 py-1">{d}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {days.map((d) => {
          const k = dayKey(d)
          const inMonth = d.getMonth() === cursor.getMonth()
          const dayPosts = byDay.get(k) ?? []
          const isSelected = selected === k
          return (
            <button
              key={k}
              onClick={() => setSelected(isSelected ? null : k)}
              className={`aspect-square p-1.5 text-left border rounded transition relative ${
                isSelected
                  ? 'bg-brand/15 border-brand'
                  : inMonth
                  ? 'bg-dark-800 border-dark-700 hover:border-dark-500'
                  : 'bg-dark-900/50 border-dark-800 text-slate-700'
              }`}
            >
              <span className={`text-xs font-mono ${inMonth ? 'text-slate-300' : 'text-slate-700'}`}>
                {d.getDate()}
              </span>
              {dayPosts.length > 0 && (
                <div className="absolute bottom-1 left-1.5 right-1.5 flex flex-wrap gap-0.5">
                  {dayPosts.slice(0, 6).map((p) => (
                    <span
                      key={p.id}
                      className={`w-1.5 h-1.5 rounded-full ${DOT_COLORS[p.status]}`}
                      title={`${p.account}: ${p.caption.slice(0, 40)}`}
                    />
                  ))}
                  {dayPosts.length > 6 && (
                    <span className="text-[9px] font-mono text-slate-500">+{dayPosts.length - 6}</span>
                  )}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {selected && (
        <div className="bg-dark-800 border border-dark-600 rounded p-3 space-y-2">
          <h4 className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
            {selected} — {selectedPosts.length} POST{selectedPosts.length === 1 ? '' : 'S'}
          </h4>
          {selectedPosts.length === 0 && (
            <p className="text-xs text-slate-500">No posts on this day.</p>
          )}
          {selectedPosts.map((p) => (
            <div key={p.id} className="flex items-center gap-3 text-sm border-t border-dark-700 pt-2 first:border-t-0 first:pt-0">
              <span className="text-xs font-mono text-slate-500">
                {new Date(p.schedule_time).toLocaleTimeString('vi-VN', {
                  timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit',
                })}
              </span>
              <span className="text-slate-300">{p.account}</span>
              <span className="text-slate-400 truncate flex-1">{p.caption || '(no caption)'}</span>
              <StatusBadge status={p.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
