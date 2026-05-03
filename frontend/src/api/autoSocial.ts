import { api } from './client'

export type PostStatus = 'pending' | 'uploading' | 'queued' | 'posted' | 'failed' | 'cancelled'

export interface AutoSocialPost {
  id: string
  account: string
  channel_id: string
  video_url: string
  thumbnail_url: string | null
  caption: string
  hashtags: string[]
  schedule_time: string
  status: PostStatus
  buffer_post_id: string | null
  posted_url: string | null
  posted_at: string | null
  attempts: number
  last_error: string | null
  created_by: string
  created_at: string
  updated_at: string
}

export interface AutoSocialPostCreate {
  account: string
  channel_id: string
  video_url: string
  thumbnail_url?: string | null
  caption: string
  hashtags: string[]
  schedule_time: string
}

export interface AutoSocialPostUpdate {
  caption?: string
  hashtags?: string[]
  schedule_time?: string
  status?: 'cancelled'
}

export interface AutoSocialChannel {
  id: string
  service: string
  name: string
  service_id: string
  timezone: string
  is_disconnected: boolean
  external_link: string | null
  last_synced_at: string
}

export interface AutoSocialStats {
  pending: number
  queued: number
  uploading: number
  posted: number
  failed: number
  cancelled: number
  total: number
  posted_last_7d: number
}

export interface ListPostsParams {
  status?: PostStatus
  account?: string
  schedule_from?: string
  schedule_to?: string
  descending?: boolean
  limit?: number
}

function qs(params: Record<string, unknown>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  if (!entries.length) return ''
  return '?' + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&')
}

export const listPosts = (p: ListPostsParams = {}) =>
  api.get<AutoSocialPost[]>(`/auto-social/posts${qs(p as Record<string, unknown>)}`)
export const getPost = (id: string) => api.get<AutoSocialPost>(`/auto-social/posts/${id}`)
export const createPost = (body: AutoSocialPostCreate) =>
  api.post<AutoSocialPost>('/auto-social/posts', body)
export const updatePost = (id: string, body: AutoSocialPostUpdate) =>
  api.put<AutoSocialPost>(`/auto-social/posts/${id}`, body)
export const deletePost = (id: string) =>
  api.delete<{ ok: boolean; buffer_deleted: boolean }>(`/auto-social/posts/${id}`)

export const listChannels = () => api.get<AutoSocialChannel[]>('/auto-social/channels')
export const syncChannels = () => api.post<AutoSocialChannel[]>('/auto-social/channels/sync')

export const getStats = () => api.get<AutoSocialStats>('/auto-social/stats')
