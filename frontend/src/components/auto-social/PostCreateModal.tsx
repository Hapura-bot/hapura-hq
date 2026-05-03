import { useState } from 'react'
import { X } from 'lucide-react'
import { useAutoSocialChannels, useCreateAutoSocialPost } from '../../hooks/useAutoSocial'

interface Props {
  open: boolean
  onClose: () => void
}

function nowPlusHoursLocal(hours: number): string {
  const d = new Date(Date.now() + hours * 3600_000)
  // Format as YYYY-MM-DDTHH:mm in local TZ for <input type="datetime-local">
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function PostCreateModal({ open, onClose }: Props) {
  const { data: channels } = useAutoSocialChannels()
  const create = useCreateAutoSocialPost()

  const [videoUrl, setVideoUrl] = useState('')
  const [caption, setCaption] = useState('')
  const [hashtagsText, setHashtagsText] = useState('')
  const [scheduleLocal, setScheduleLocal] = useState(nowPlusHoursLocal(2))
  const [channelId, setChannelId] = useState<string>('')

  if (!open) return null

  const channelOptions = channels?.filter((c) => !c.is_disconnected) ?? []
  const selectedChannel = channelOptions.find((c) => c.id === channelId)

  function reset() {
    setVideoUrl('')
    setCaption('')
    setHashtagsText('')
    setScheduleLocal(nowPlusHoursLocal(2))
    setChannelId('')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!channelId || !selectedChannel) return
    const tags = hashtagsText
      .split(/[\s,]+/)
      .map((t) => t.trim())
      .filter(Boolean)
      .map((t) => (t.startsWith('#') ? t : `#${t}`))

    const localDate = new Date(scheduleLocal)
    const scheduleIsoUtc = localDate.toISOString()

    try {
      await create.mutateAsync({
        account: selectedChannel.name,
        channel_id: channelId,
        video_url: videoUrl.trim(),
        caption: caption.trim(),
        hashtags: tags,
        schedule_time: scheduleIsoUtc,
      })
      reset()
      onClose()
    } catch (err) {
      console.error('Create post failed', err)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-dark-900/80 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="bg-dark-800 border border-dark-600 rounded-lg max-w-xl w-full p-5 space-y-4"
      >
        <div className="flex items-center justify-between">
          <h2 className="font-game text-lg font-bold text-brand tracking-wider">SCHEDULE POST</h2>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X size={18} />
          </button>
        </div>

        <Field label="Channel">
          <select
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            className="w-full bg-dark-900 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200"
            required
          >
            <option value="">Select channel...</option>
            {channelOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.service.toUpperCase()} — {c.name}
              </option>
            ))}
          </select>
          {channelOptions.length === 0 && (
            <p className="text-xs text-slate-500 mt-1">
              No channels found. Sync channels from Channels tab.
            </p>
          )}
        </Field>

        <Field label="Video URL" hint="Public HTTPS URL Buffer can fetch (mp4)">
          <input
            type="url"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="https://..."
            className="w-full bg-dark-900 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 font-mono"
            required
          />
        </Field>

        <Field label="Caption" hint={`${caption.length}/2200 chars`}>
          <textarea
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            rows={3}
            maxLength={2200}
            className="w-full bg-dark-900 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 resize-y"
          />
        </Field>

        <Field label="Hashtags" hint="Space or comma separated, # optional">
          <input
            type="text"
            value={hashtagsText}
            onChange={(e) => setHashtagsText(e.target.value)}
            placeholder="fyp viral vn"
            className="w-full bg-dark-900 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 font-mono"
          />
        </Field>

        <Field label="Schedule (local time)">
          <input
            type="datetime-local"
            value={scheduleLocal}
            onChange={(e) => setScheduleLocal(e.target.value)}
            className="w-full bg-dark-900 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 font-mono"
            required
          />
        </Field>

        {create.isError && (
          <div className="text-xs font-mono text-red-400 bg-red-900/20 border border-red-700/50 rounded px-3 py-2">
            {(create.error as Error).message}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono uppercase tracking-wider text-slate-400 border border-dark-600 rounded hover:text-slate-200"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={create.isPending || !channelId || !videoUrl}
            className="px-4 py-2 text-xs font-mono uppercase tracking-wider bg-brand text-dark-900 rounded hover:bg-brand/90 disabled:opacity-50"
          >
            {create.isPending ? 'Scheduling...' : 'Schedule'}
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="flex items-baseline justify-between mb-1">
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">{label}</span>
        {hint && <span className="text-[10px] text-slate-600">{hint}</span>}
      </label>
      {children}
    </div>
  )
}
