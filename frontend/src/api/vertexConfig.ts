import { api } from './client'

// ─── Types ─────────────────────────────────────────────────────────────────

export interface EndpointConfig {
  base_url: string
  api_key_ref: string
}

export interface ModelEntry {
  value: string
  endpoint: string
}

export interface ReloadWebhook {
  url: string
  // Auth uses client_token (same token the SDK uses to poll the hub).
  // Rotate via /projects/{id}/regenerate-token.
}

export interface VertexConfigDoc {
  project_id: string
  display_name: string
  endpoints: Record<string, EndpointConfig>
  models: Record<string, ModelEntry>
  env_map: Record<string, string>
  reload_webhook: ReloadWebhook
  revision: number
  updated_at: string
  updated_by: string
  client_token: string
}

export interface VertexConfigCreate {
  project_id: string
  display_name: string
  endpoints?: Record<string, EndpointConfig>
  models?: Record<string, ModelEntry>
  env_map?: Record<string, string>
  reload_webhook?: ReloadWebhook
}

export interface VertexConfigUpdate {
  display_name?: string
  endpoints?: Record<string, EndpointConfig>
  models?: Record<string, ModelEntry>
  env_map?: Record<string, string>
  reload_webhook?: ReloadWebhook
}

export interface TestResult {
  ok: boolean
  latency_ms: number | null
  model: string
  endpoint: string
  sample: string
  error: string
}

export interface ReloadResult {
  ok: boolean
  status_code: number | null
  error: string
}

// ─── API functions ─────────────────────────────────────────────────────────

export const vcApi = {
  list: () => api.get<VertexConfigDoc[]>('/vertex-config/projects'),
  get:  (id: string) => api.get<VertexConfigDoc>(`/vertex-config/projects/${id}`),
  create: (body: VertexConfigCreate) =>
    api.post<VertexConfigDoc & { client_token: string }>('/vertex-config/projects', body),
  update: (id: string, body: VertexConfigUpdate) =>
    api.put<VertexConfigDoc>(`/vertex-config/projects/${id}`, body),
  delete: (id: string) => api.delete<void>(`/vertex-config/projects/${id}`),
  history: (id: string) => api.get<VertexConfigDoc[]>(`/vertex-config/projects/${id}/history`),
  rollback: (id: string, rev: number) =>
    api.post<VertexConfigDoc>(`/vertex-config/projects/${id}/rollback/${rev}`),
  test: (id: string) =>
    api.post<TestResult>(`/vertex-config/projects/${id}/test`),
  reload: (id: string) =>
    api.post<ReloadResult>(`/vertex-config/projects/${id}/reload`),
  regenerateToken: (id: string) =>
    api.post<{ client_token: string; note: string }>(
      `/vertex-config/projects/${id}/regenerate-token`
    ),
}

// ─── Defaults ─────────────────────────────────────────────────────────────

export const DEFAULT_WEBHOOK: ReloadWebhook = { url: '' }
