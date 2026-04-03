const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8099/api/v1'

let _getToken: (() => Promise<string>) | null = null
export function setTokenProvider(fn: () => Promise<string>) { _getToken = fn }
export function clearTokenProvider() { _getToken = null }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (_getToken) {
    try { headers['Authorization'] = `Bearer ${await _getToken()}` } catch { /* skip */ }
  }
  const res = await fetch(`${BASE}${path}`, {
    headers: { ...headers, ...(init?.headers as Record<string, string> ?? {}) },
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}

export const api = {
  get:    <T>(path: string)                  => request<T>(path),
  post:   <T>(path: string, body?: unknown)  => request<T>(path, { method: 'POST',   body: JSON.stringify(body ?? {}) }),
  put:    <T>(path: string, body?: unknown)  => request<T>(path, { method: 'PUT',    body: JSON.stringify(body ?? {}) }),
  patch:  <T>(path: string, body?: unknown)  => request<T>(path, { method: 'PATCH',  body: JSON.stringify(body ?? {}) }),
  delete: <T>(path: string)                  => request<T>(path, { method: 'DELETE' }),
}

// ─── Types ────────────────────────────────────────────────────────────────────

export type ProjectStatus = 'deployed' | 'dev' | 'planned'
export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type Priority = 'high' | 'medium' | 'low'

export interface ProjectRoom {
  id: string
  name: string
  tagline: string
  platform: 'android' | 'web'
  status: ProjectStatus
  tech_stack: string[]
  cloud_run_service_id: string
  github_repo: string
  frontend_url: string
  color_accent: string
  port_backend: number | null
  port_frontend: number | null
  phase_current: number
  phase_total: number
  phase_label: string
}

export interface MetricEntry {
  id?: string
  project_id: string
  period: string
  revenue_vnd: number
  active_users: number
  new_signups: number
  recorded_at?: string
}

export interface Task {
  id?: string
  project_id: string
  title: string
  description: string
  status: TaskStatus
  priority: Priority
  tags: string[]
  created_at?: string
  updated_at?: string
}

export type HealthStatus = 'healthy' | 'degraded' | 'timeout' | 'offline' | 'unknown'

export interface IntegrationCache {
  project_id: string
  github_repo: string
  github_commits_7d: number
  github_commits_4w: number[]
  github_open_issues: number
  github_open_prs: number
  github_last_commit_at: string | null
  cloudrun_status: HealthStatus
  cloudrun_latency_ms: number | null
  fetched_at: string
}

export interface GPScore {
  project_id: string
  gp_total: number
  gp_revenue: number
  gp_users: number
  gp_velocity: number
  gp_uptime: number
  investment_multiplier: number
  is_focus: boolean
}

// ─── API functions ─────────────────────────────────────────────────────────────

export const getProjects = () => api.get<ProjectRoom[]>('/projects')
export const getProject  = (id: string) => api.get<ProjectRoom>(`/projects/${id}`)
export const updateProject = (id: string, body: Partial<ProjectRoom>) => api.put<ProjectRoom>(`/projects/${id}`, body)
export const getGPScore  = (id: string) => api.get<GPScore>(`/projects/${id}/gp`)

export const getMetrics         = () => api.get<MetricEntry[]>('/metrics')
export const getMetricHistory   = (projectId: string) => api.get<MetricEntry[]>(`/metrics/${projectId}`)
export const createMetric = (body: {
  project_id: string; period: string
  revenue_vnd: number; active_users: number; new_signups: number
}) => api.post<MetricEntry>('/metrics', body)

// ─── Agents ──────────────────────────────────────────────────────────────────

export interface AgentRun {
  id: string
  agent_id: string
  status: 'running' | 'done' | 'error' | 'never'
  triggered_by: string
  started_at: string
  finished_at: string | null
  report_markdown: string
  summary: string
}

export interface AgentMeta {
  id: string
  name: string
  role: string
  schedule: string
  color: string
  last_run_at: string | null
  last_run_status: string
  last_run_summary: string
  last_run_id: string | null
}

export const getAgents         = () => api.get<AgentMeta[]>('/agents')
export const getAgentRuns      = (id: string) => api.get<AgentRun[]>(`/agents/${id}/runs`)
export const getLatestAgentRun = (id: string) => api.get<AgentRun>(`/agents/${id}/runs/latest`)
export const triggerAgent      = (id: string) => api.post<{ run_id: string; status: string }>(`/agents/${id}/trigger`)

export interface WinnerDeclaration {
  winner_id: string
  winner_name: string
  gp_total: number
  period: string
  message: string
  telegram_sent: boolean
}

export const declareWinner = () => api.post<WinnerDeclaration>('/projects/winner/declare')

export const getAllIntegrations = () => api.get<IntegrationCache[]>('/integrations')
export const getIntegration    = (id: string) => api.get<IntegrationCache>(`/integrations/${id}`)
export const refreshIntegration = (id: string) => api.post<IntegrationCache>(`/integrations/${id}/refresh`)

export const getTasks     = (projectId?: string) => api.get<Task[]>(`/tasks${projectId ? `?project_id=${projectId}` : ''}`)
export const createTask   = (body: Omit<Task, 'id' | 'status' | 'created_at' | 'updated_at'>) => api.post<Task>('/tasks', body)
export const updateTaskStatus = (id: string, status: TaskStatus) => api.patch<Task>(`/tasks/${id}/status`, { status })
export const deleteTask   = (id: string) => api.delete<void>(`/tasks/${id}`)

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function formatVND(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000)     return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)         return `${(n / 1_000).toFixed(0)}k`
  return n.toString()
}

export function formatCount(n: number | null): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

export function currentPeriod(): string {
  return new Date().toISOString().slice(0, 7) // "2026-04"
}
