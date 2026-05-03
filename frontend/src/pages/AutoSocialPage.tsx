import { useState } from 'react'
import { Plus, Calendar, List, Radio, BarChart3 } from 'lucide-react'
import { PostsList } from '../components/auto-social/PostsList'
import { PostsCalendar } from '../components/auto-social/PostsCalendar'
import { ChannelsList } from '../components/auto-social/ChannelsList'
import { StatsCards } from '../components/auto-social/StatsCards'
import { PostCreateModal } from '../components/auto-social/PostCreateModal'

type Tab = 'calendar' | 'list' | 'channels' | 'stats'

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'calendar', label: 'CALENDAR', icon: Calendar },
  { id: 'list',     label: 'LIST',     icon: List },
  { id: 'channels', label: 'CHANNELS', icon: Radio },
  { id: 'stats',    label: 'STATS',    icon: BarChart3 },
]

export default function AutoSocialPage() {
  const [tab, setTab] = useState<Tab>('calendar')
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-game text-2xl font-bold text-brand tracking-widest text-glow-brand">
            AUTO-SOCIAL
          </h1>
          <p className="text-xs font-mono text-slate-500 mt-1 tracking-wider">
            TIKTOK SCHEDULER · BUFFER GRAPHQL
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-mono uppercase tracking-wider bg-brand text-dark-900 rounded hover:bg-brand/90"
        >
          <Plus size={14} />
          Schedule Post
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-600 flex gap-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-mono uppercase tracking-wider border-b-2 transition ${
              tab === id
                ? 'text-brand border-brand'
                : 'text-slate-500 border-transparent hover:text-slate-300'
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div>
        {tab === 'calendar' && <PostsCalendar />}
        {tab === 'list' && <PostsList />}
        {tab === 'channels' && <ChannelsList />}
        {tab === 'stats' && (
          <div className="space-y-4">
            <StatsCards />
            <div className="bg-dark-800 border border-dark-600 rounded p-4">
              <p className="text-xs font-mono text-slate-500 tracking-wider">
                More analytics coming as data accumulates.
              </p>
            </div>
          </div>
        )}
      </div>

      <PostCreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
