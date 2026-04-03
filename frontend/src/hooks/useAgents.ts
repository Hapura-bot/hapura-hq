import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAgents, getAgentRuns, getLatestAgentRun, triggerAgent } from '../api/client'

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: getAgents,
    staleTime: 30_000,
    refetchInterval: 10_000, // poll for status updates
  })
}

export function useAgentRuns(agentId: string) {
  return useQuery({
    queryKey: ['agent-runs', agentId],
    queryFn: () => getAgentRuns(agentId),
    staleTime: 15_000,
  })
}

export function useLatestAgentRun(agentId: string, enabled = true) {
  return useQuery({
    queryKey: ['agent-run-latest', agentId],
    queryFn: () => getLatestAgentRun(agentId),
    staleTime: 5_000,
    refetchInterval: (query) => {
      // Poll every 3s while running
      const data = query.state.data as { status?: string } | undefined
      return data?.status === 'running' ? 3_000 : false
    },
    enabled,
    retry: false,
  })
}

export function useTriggerAgent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => triggerAgent(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agents'] })
      qc.invalidateQueries({ queryKey: ['agent-run-latest'] })
    },
  })
}
