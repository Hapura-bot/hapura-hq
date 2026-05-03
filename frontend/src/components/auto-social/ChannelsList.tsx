import { RefreshCw, ExternalLink, AlertCircle } from 'lucide-react'
import { useAutoSocialChannels, useSyncChannels } from '../../hooks/useAutoSocial'

export function ChannelsList() {
  const { data: channels, isLoading } = useAutoSocialChannels()
  const sync = useSyncChannels()

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-game text-sm tracking-widest text-slate-400">CONNECTED CHANNELS</h3>
        <button
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
          className="flex items-center gap-1.5 px-3 py-1 text-xs font-mono uppercase tracking-wider text-brand border border-brand/30 rounded hover:bg-brand/10 disabled:opacity-50"
        >
          <RefreshCw size={12} className={sync.isPending ? 'animate-spin' : ''} />
          Sync from Buffer
        </button>
      </div>

      {sync.isError && (
        <div className="text-xs font-mono text-red-400 bg-red-900/20 border border-red-700/50 rounded px-3 py-2">
          {(sync.error as Error).message}
        </div>
      )}

      <div className="bg-dark-800 border border-dark-600 rounded">
        {isLoading && <div className="p-4 text-center text-slate-500">Loading...</div>}
        {!isLoading && (!channels || channels.length === 0) && (
          <div className="p-6 text-center">
            <p className="text-slate-500 text-sm">No channels yet.</p>
            <p className="text-slate-600 text-xs mt-1">Click "Sync from Buffer" to fetch.</p>
          </div>
        )}
        {channels?.map((c) => (
          <div
            key={c.id}
            className="border-t border-dark-700 first:border-t-0 px-4 py-3 flex items-center justify-between hover:bg-dark-900/30"
          >
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 bg-dark-900 px-2 py-0.5 rounded border border-dark-600">
                {c.service}
              </span>
              <span className="text-slate-200">{c.name}</span>
              {c.is_disconnected && (
                <span className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider text-red-400">
                  <AlertCircle size={11} /> disconnected
                </span>
              )}
            </div>
            {c.external_link && (
              <a
                href={c.external_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-brand"
              >
                <ExternalLink size={11} />
                Open
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
