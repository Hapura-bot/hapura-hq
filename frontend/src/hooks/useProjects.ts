import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query'
import {
  getProjects, getMetrics, getGPScore, createMetric, declareWinner,
  type MetricEntry, type GPScore, type WinnerDeclaration,
} from '../api/client'

const PROJECT_IDS = ['clippack', 'trendkr', 'hapu-studio', 'douyin-vi-dubber']

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
    staleTime: 30_000,
  })
}

export function useMetrics() {
  return useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
    staleTime: 60_000,
  })
}

export function useGPScore(projectId: string) {
  return useQuery({
    queryKey: ['gp', projectId],
    queryFn: () => getGPScore(projectId),
    staleTime: 60_000,
  })
}

export function useAllGPScores(): GPScore[] {
  const results = useQueries({
    queries: PROJECT_IDS.map(id => ({
      queryKey: ['gp', id],
      queryFn: () => getGPScore(id),
      staleTime: 60_000,
    })),
  })
  return results.map(r => r.data).filter((d): d is GPScore => !!d)
}

export function useCreateMetric() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Omit<MetricEntry, 'id' | 'recorded_at'>) =>
      createMetric({
        project_id:   body.project_id,
        period:       body.period,
        revenue_vnd:  body.revenue_vnd,
        active_users: body.active_users,
        new_signups:  body.new_signups,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['metrics'] })
      qc.invalidateQueries({ queryKey: ['gp'] })
    },
  })
}

export function useDeclareWinner() {
  const qc = useQueryClient()
  return useMutation<WinnerDeclaration, Error, void>({
    mutationFn: () => declareWinner(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gp'] })
    },
  })
}
