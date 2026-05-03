import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPost, deletePost, getPost, getStats,
  listChannels, listPosts, syncChannels, updatePost,
  type AutoSocialPostCreate, type AutoSocialPostUpdate, type ListPostsParams,
} from '../api/autoSocial'

export function useAutoSocialPosts(params: ListPostsParams = {}) {
  return useQuery({
    queryKey: ['auto-social', 'posts', params],
    queryFn: () => listPosts(params),
    staleTime: 15_000,
  })
}

export function useAutoSocialPost(id: string | null) {
  return useQuery({
    queryKey: ['auto-social', 'posts', id],
    queryFn: () => getPost(id!),
    enabled: !!id,
    staleTime: 15_000,
  })
}

export function useCreateAutoSocialPost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AutoSocialPostCreate) => createPost(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auto-social', 'posts'] })
      qc.invalidateQueries({ queryKey: ['auto-social', 'stats'] })
    },
  })
}

export function useUpdateAutoSocialPost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: AutoSocialPostUpdate }) =>
      updatePost(id, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auto-social', 'posts'] })
    },
  })
}

export function useDeleteAutoSocialPost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deletePost(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auto-social', 'posts'] })
      qc.invalidateQueries({ queryKey: ['auto-social', 'stats'] })
    },
  })
}

export function useAutoSocialChannels() {
  return useQuery({
    queryKey: ['auto-social', 'channels'],
    queryFn: listChannels,
    staleTime: 5 * 60_000,
  })
}

export function useSyncChannels() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: syncChannels,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auto-social', 'channels'] })
    },
  })
}

export function useAutoSocialStats() {
  return useQuery({
    queryKey: ['auto-social', 'stats'],
    queryFn: getStats,
    staleTime: 30_000,
  })
}
