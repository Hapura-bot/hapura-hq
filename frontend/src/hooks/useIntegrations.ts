import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAllIntegrations, refreshIntegration, type IntegrationCache } from '../api/client'

export function useIntegrations() {
  return useQuery({
    queryKey: ['integrations'],
    queryFn: getAllIntegrations,
    staleTime: 5 * 60 * 1000,   // 5 min — matches backend TTL
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useRefreshIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => refreshIntegration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations'] }),
  })
}

export function useIntegrationMap(integrations: IntegrationCache[] | undefined) {
  if (!integrations) return {}
  return Object.fromEntries(integrations.map(i => [i.project_id, i]))
}
