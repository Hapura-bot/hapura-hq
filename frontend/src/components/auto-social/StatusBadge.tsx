import type { PostStatus } from '../../api/autoSocial'

const STYLES: Record<PostStatus, string> = {
  pending: 'bg-slate-700 text-slate-300 border-slate-600',
  uploading: 'bg-yellow-900/40 text-yellow-300 border-yellow-700',
  queued: 'bg-blue-900/40 text-blue-300 border-blue-700',
  posted: 'bg-emerald-900/40 text-emerald-300 border-emerald-700',
  failed: 'bg-red-900/40 text-red-300 border-red-700',
  cancelled: 'bg-slate-800 text-slate-500 border-slate-700',
}

export function StatusBadge({ status }: { status: PostStatus }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded border ${STYLES[status]}`}
    >
      {status}
    </span>
  )
}
