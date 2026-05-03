import { useState } from 'react'
import { ExternalLink, Trash2, RefreshCw } from 'lucide-react'
import { useAutoSocialPosts, useDeleteAutoSocialPost } from '../../hooks/useAutoSocial'
import type { PostStatus } from '../../api/autoSocial'
import { StatusBadge } from './StatusBadge'

const STATUS_FILTERS: ('all' | PostStatus)[] = [
  'all', 'pending', 'queued', 'uploading', 'posted', 'failed', 'cancelled',
]

function fmt(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function PostsList() {
  const [filter, setFilter] = useState<'all' | PostStatus>('all')
  const { data: posts, isLoading, refetch, isFetching } = useAutoSocialPosts(
    filter === 'all' ? { descending: true } : { status: filter, descending: true }
  )
  const del = useDeleteAutoSocialPost()

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-xs font-mono uppercase tracking-wider rounded border transition ${
              filter === f
                ? 'bg-brand/15 text-brand border-brand/30'
                : 'text-slate-500 border-dark-600 hover:text-slate-300'
            }`}
          >
            {f}
          </button>
        ))}
        <button
          onClick={() => refetch()}
          className="ml-auto flex items-center gap-1 px-2 py-1 text-xs font-mono text-slate-500 hover:text-slate-300"
          disabled={isFetching}
        >
          <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
          REFRESH
        </button>
      </div>

      <div className="bg-dark-800 border border-dark-600 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-dark-900 text-slate-500 text-[10px] uppercase tracking-wider font-mono">
            <tr>
              <th className="px-3 py-2 text-left">Schedule</th>
              <th className="px-3 py-2 text-left">Account</th>
              <th className="px-3 py-2 text-left">Caption</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">URL</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>
            )}
            {!isLoading && (!posts || posts.length === 0) && (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-slate-500">No posts</td></tr>
            )}
            {posts?.map((p) => (
              <tr key={p.id} className="border-t border-dark-700 hover:bg-dark-900/50">
                <td className="px-3 py-2 font-mono text-xs text-slate-400">{fmt(p.schedule_time)}</td>
                <td className="px-3 py-2 text-slate-300">{p.account}</td>
                <td className="px-3 py-2 text-slate-300 max-w-md truncate" title={p.caption}>
                  {p.caption || <span className="text-slate-600">(no caption)</span>}
                </td>
                <td className="px-3 py-2"><StatusBadge status={p.status} /></td>
                <td className="px-3 py-2">
                  {p.posted_url ? (
                    <a
                      href={p.posted_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-brand hover:underline text-xs"
                    >
                      <ExternalLink size={11} />
                      View
                    </a>
                  ) : (
                    <span className="text-slate-600 text-xs">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => {
                      if (confirm(`Delete post for ${p.account}?`)) del.mutate(p.id)
                    }}
                    className="text-slate-500 hover:text-red-400 transition"
                    title="Delete"
                    disabled={del.isPending}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {posts && posts.length > 0 && (
        <div className="text-xs font-mono text-slate-600 tracking-wider">
          {posts.length} POST{posts.length === 1 ? '' : 'S'}
        </div>
      )}
    </div>
  )
}
