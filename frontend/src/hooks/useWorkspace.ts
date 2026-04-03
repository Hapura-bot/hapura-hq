import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

// ─── Types ──────────────────────────────────────────────────────────────────

export interface DepartmentAgent {
  id: string
  name: string
  status: 'running' | 'done' | 'error' | 'never'
  last_run_at: string | null
  is_implemented: boolean
}

export interface Department {
  id: string
  name: string
  name_vi: string
  description: string
  icon: string
  color: string
  agent_ids: string[]
  lead_agent_id: string | null
  health_score: number
  last_summary_at: string | null
  last_summary: string
  agents: DepartmentAgent[]
  agents_implemented: number
  agents_total: number
}

export interface AgentDetail {
  id: string
  name: string
  role: string
  schedule: string
  color: string
  runs: Array<{
    id: string
    agent_id: string
    status: string
    triggered_by: string
    started_at: string
    finished_at: string | null
    report_markdown: string
    summary: string
  }>
}

export interface DepartmentDetail extends Department {
  agents_detail: AgentDetail[]
  reports: Array<{
    id: string
    department_id: string
    period: string
    report_markdown: string
    summary: string
    generated_at: string
  }>
  messages_incoming: Array<AgentMessage>
  messages_outgoing: Array<AgentMessage>
}

export interface AgentMessage {
  id: string
  from_agent_id: string
  from_department: string
  to_department: string
  message_type: string
  payload: Record<string, unknown>
  priority: string
  created_at: string
  acknowledged: boolean
}

export interface WorkspaceConfig {
  id: string
  product_id: string
  product_name: string
  platform: string
  enabled_departments: string[]
  enabled_agents: Record<string, string[]>
  data_sources: Record<string, unknown>
  meta: { description: string; goal: string; current_phase: string }
}

export interface Directive {
  id: string
  period: string
  directive_type: string
  directive_markdown: string
  priorities: string[]
  department_actions: Record<string, string[]>
  generated_at: string
  approved_by: string | null
  approved_at: string | null
  status: 'draft' | 'approved' | 'active' | 'archived'
}

// ─── API Functions ──────────────────────────────────────────────────────────

const getWorkspaceConfigs = () => api.get<WorkspaceConfig[]>('/workspace/configs')
const getWorkspaceConfig = (id: string) => api.get<WorkspaceConfig>(`/workspace/config/${id}`)
const getDepartments = () => api.get<Department[]>('/workspace/departments')
const getDepartment = (id: string) => api.get<DepartmentDetail>(`/workspace/departments/${id}`)
const runDepartment = (id: string) => api.post<{ department_id: string; status: string }>(`/workspace/departments/${id}/run`)
const getDirectives = () => api.get<Directive[]>('/workspace/directives')
const approveDirective = (id: string) => api.post<{ id: string; status: string }>(`/workspace/directives/${id}/approve`)
const getMessages = (dept?: string) => api.get<AgentMessage[]>(`/workspace/messages${dept ? `?department=${dept}` : ''}`)

// ─── Hooks ──────────────────────────────────────────────────────────────────

export function useAvailableProducts() {
  return useQuery({
    queryKey: ['workspace-configs'],
    queryFn: getWorkspaceConfigs,
    staleTime: 300_000,
  })
}

export function useWorkspaceConfig(productId: string) {
  return useQuery({
    queryKey: ['workspace-config', productId],
    queryFn: () => getWorkspaceConfig(productId),
    staleTime: 300_000,
    enabled: !!productId,
  })
}

export function useDepartments() {
  return useQuery({
    queryKey: ['departments'],
    queryFn: getDepartments,
    staleTime: 30_000,
    refetchInterval: 15_000,
  })
}

export function useDepartment(id: string) {
  return useQuery({
    queryKey: ['department', id],
    queryFn: () => getDepartment(id),
    staleTime: 15_000,
    refetchInterval: 10_000,
    enabled: !!id,
  })
}

export function useRunDepartment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => runDepartment(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['departments'] })
      qc.invalidateQueries({ queryKey: ['department'] })
    },
  })
}

export function useDirectives() {
  return useQuery({
    queryKey: ['directives'],
    queryFn: getDirectives,
    staleTime: 60_000,
  })
}

export function useApproveDirective() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => approveDirective(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['directives'] })
    },
  })
}

export function useAgentMessages(department?: string) {
  return useQuery({
    queryKey: ['agent-messages', department],
    queryFn: () => getMessages(department),
    staleTime: 30_000,
    refetchInterval: 15_000,
  })
}
