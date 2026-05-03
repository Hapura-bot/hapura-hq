# Phase 04 — Frontend Page Skeleton

## Context Links

- Existing pages pattern: `C:\Users\Admin\hapura-command\frontend\src\pages\VertexConfigPage.tsx`, `SprintPage.tsx`
- Existing API client wrapper: `C:\Users\Admin\hapura-command\frontend\src\api\client.ts`
- Existing nav config: `C:\Users\Admin\hapura-command\frontend\src\components\layout\CommandNav.tsx`
- Existing route registration: `C:\Users\Admin\hapura-command\frontend\src\App.tsx`
- Tailwind theme tokens: `C:\Users\Admin\hapura-command\frontend\tailwind.config.js`
- TanStack hook pattern: `C:\Users\Admin\hapura-command\frontend\src\hooks\useTasks.ts`

## Overview

- **Priority:** P2 (depends on phase 02 routes online)
- **Status:** pending
- **Description:** Add `/auto-social` route + nav entry + base page layout with 4 tabs (Calendar, List, Channels, Stats). Wire TanStack Query hooks. No real content yet — just shells.

## Key Insights

- `App.tsx` already has `<QueryClientProvider>` — no extra setup.
- Auth is handled via `AuthContext` — `setTokenProvider` already wires Firebase token into `api.client.ts`. Page can just call `api.get<T>('/auto-social/...')` and auth flows through.
- Existing `client.ts` exports a generic `api = { get, post, put, patch, delete }` — extend with new section, do not create a new client.
- All existing pages use `dark-900/800/700/600/500` palette + `brand` (`#06b6d4`) accent + `Rajdhani` (`font-game`) headings + `Be Vietnam Pro` (`font-vn`) body. Match.
- Tab pattern: simple state-driven (`useState<'calendar'|'list'|'channels'|'stats'>`) — no tab library needed.
- Nav `NAV_LINKS` is a static array; append one entry. Use `Calendar` icon from `lucide-react`.

## Requirements

### Functional

- F04-1 New route `/auto-social` mounted in `App.tsx`.
- F04-2 New nav entry `AUTO-SOCIAL` (Calendar icon) — admin-only display (hidden if `user` not in admin uid list — for v1 just show always; auth still enforced server-side).
- F04-3 New page `AutoSocialPage.tsx` with 4 tab buttons in header bar; default tab `Calendar`.
- F04-4 Per-tab placeholders: each tab renders a "coming in phase 05/06" panel for now (filled by later phases).
- F04-5 New API module `frontend/src/api/autoSocial.ts` with TS interfaces + thin functions.
- F04-6 New hook module `frontend/src/hooks/useAutoSocial.ts` with TanStack queries/mutations.

### Non-Functional

- Page renders within 500ms on local dev (no blocking effects).
- TypeScript strict — no `any`.
- Build passes: `cd frontend && npm run build`.

## Architecture

### Component Tree

```
AutoSocialPage
├── PageHeader (title + tab nav)
├── Tab content (one of):
│   ├── PostsCalendar    (phase 06)
│   ├── PostsList        (phase 05)
│   ├── ChannelsList     (phase 05)
│   └── StatsCards       (phase 05)
└── PostCreateModal      (phase 05) — toggled from header "+ Schedule Post" btn
```

### Module Layout

```
frontend/src/
├── pages/AutoSocialPage.tsx                    (this phase: shell)
├── api/autoSocial.ts                           (this phase)
├── hooks/useAutoSocial.ts                      (this phase)
└── components/auto-social/                     (folder created; populated phase 05+)
    ├── PostsList.tsx                           (phase 05)
    ├── PostCreateModal.tsx                     (phase 05)
    ├── ChannelsList.tsx                        (phase 05)
    ├── StatsCards.tsx                          (phase 05)
    └── PostsCalendar.tsx                       (phase 06)
```

### Auth Flow

```
useAutoSocial.ts ──useQuery──▶ api.autoSocial.listPosts() ──▶ client.ts::api.get
                                                                     │
                                                              auth.currentUser
                                                                     │
                                                              Bearer ID token
                                                                     │
                                                                Backend
```

## Related Code Files

### Create

- `C:\Users\Admin\hapura-command\frontend\src\api\autoSocial.ts`
- `C:\Users\Admin\hapura-command\frontend\src\hooks\useAutoSocial.ts`
- `C:\Users\Admin\hapura-command\frontend\src\pages\AutoSocialPage.tsx`
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\.gitkeep` (folder marker)

### Modify

- `C:\Users\Admin\hapura-command\frontend\src\App.tsx` — import + add `<Route path="/auto-social" element={<AutoSocialPage />} />`
- `C:\Users\Admin\hapura-command\frontend\src\components\layout\CommandNav.tsx` — append `{ to: '/auto-social', icon: Calendar, label: 'AUTO-SOCIAL' }` to `NAV_LINKS`. Import `Calendar` from `lucide-react`.

### Delete

- None.

## Implementation Steps

1. **Create `frontend/src/api/autoSocial.ts`**:
   ```typescript
   import { api } from './client'

   export type PostStatus = 'pending'|'uploading'|'queued'|'posted'|'failed'|'cancelled'

   export interface AutoSocialPost {
     id: string
     account: string
     channel_id: string
     video_url: string
     thumbnail_url: string | null
     caption: string
     hashtags: string[]
     schedule_time: string  // ISO UTC
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
   export interface PostCreate { account: string; channel_id: string; video_url: string; thumbnail_url?: string; caption: string; hashtags: string[]; schedule_time: string }
   export interface PostUpdate { caption?: string; hashtags?: string[]; schedule_time?: string; status?: 'cancelled' }

   export interface AutoSocialChannel {
     id: string; service: string; name: string; service_id: string
     timezone: string; is_disconnected: boolean; external_link: string | null; last_synced_at: string
   }

   export interface AutoSocialStats {
     pending: number; queued: number; uploading: number
     posted: number; failed: number; cancelled: number
     total: number; posted_last_7d: number
   }

   export const listPosts   = (filters?: { status?: PostStatus; from?: string; to?: string }) => {
     const q = new URLSearchParams()
     if (filters?.status) q.set('status', filters.status)
     if (filters?.from)   q.set('from', filters.from)
     if (filters?.to)     q.set('to', filters.to)
     const s = q.toString()
     return api.get<AutoSocialPost[]>(`/auto-social/posts${s ? '?'+s : ''}`)
   }
   export const getPost     = (id: string) => api.get<AutoSocialPost>(`/auto-social/posts/${id}`)
   export const createPost  = (body: PostCreate) => api.post<AutoSocialPost>('/auto-social/posts', body)
   export const updatePost  = (id: string, body: PostUpdate) => api.put<AutoSocialPost>(`/auto-social/posts/${id}`, body)
   export const deletePost  = (id: string) => api.delete<void>(`/auto-social/posts/${id}`)

   export const listChannels = () => api.get<AutoSocialChannel[]>('/auto-social/channels')
   export const syncChannels = () => api.post<AutoSocialChannel[]>('/auto-social/channels/sync')

   export const getStats = () => api.get<AutoSocialStats>('/auto-social/stats')
   ```

2. **Create `frontend/src/hooks/useAutoSocial.ts`** mirroring `useTasks.ts` style:
   - `useAutoSocialPosts(filters)`
   - `usePost(id)`
   - `useCreatePost()` (mutation, invalidates `['auto-social','posts']` + `['auto-social','stats']`)
   - `useUpdatePost()`
   - `useDeletePost()`
   - `useChannels()` ; `useSyncChannels()`
   - `useStats()`
   - Stale times: posts 30s, channels 5min, stats 30s.

3. **Create `frontend/src/pages/AutoSocialPage.tsx`** shell:
   - Header bar: title `AUTO-SOCIAL` (`font-game text-2xl text-brand`), tab buttons row.
   - State `tab: 'calendar'|'list'|'channels'|'stats'` (default `'calendar'`).
   - Right side: `+ Schedule Post` button (disabled in this phase; opens modal in phase 05).
   - Below header: switch on `tab` → render placeholders:
     - calendar → `<div className="text-slate-500 text-sm font-mono">Calendar — phase 06</div>`
     - list → `<div>List — phase 05</div>`
     - channels → `<div>Channels — phase 05</div>`
     - stats → `<div>Stats — phase 05</div>`
   - Wrap content in `max-w-7xl mx-auto px-4 py-6`.

4. **Modify `App.tsx`**:
   - Add import `import AutoSocialPage from './pages/AutoSocialPage'`.
   - Add `<Route path="/auto-social" element={<AutoSocialPage />} />` to the `<Routes>` block.

5. **Modify `CommandNav.tsx`**:
   - Import `Calendar` from `lucide-react`.
   - Append to `NAV_LINKS`:
     ```typescript
     { to: '/auto-social', icon: Calendar, label: 'AUTO-SOCIAL' },
     ```

6. **Compile + visual smoke**:
   - `cd frontend && npm run build` — must succeed.
   - `npm run dev` — visit http://localhost:5199/auto-social, click each tab.

## Todo List

- [ ] Create `api/autoSocial.ts` with types + functions
- [ ] Create `hooks/useAutoSocial.ts` with TanStack hooks
- [ ] Create `pages/AutoSocialPage.tsx` shell with 4 tabs
- [ ] Add nav entry to `CommandNav.tsx`
- [ ] Add route to `App.tsx`
- [ ] Create `components/auto-social/` folder marker
- [ ] `npm run build` succeeds
- [ ] Visual smoke check at /auto-social

## Success Criteria

- Visiting `/auto-social` renders page header, tab buttons, and active-tab placeholder.
- Tab buttons toggle visible state.
- Build green; TypeScript no errors.
- Nav entry visible and active highlight works (matches existing pattern in `CommandNav.tsx`).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Path collision with existing route | None | — | `/auto-social` is new |
| Hook keys collision with existing query keys | Low | Low | Namespace keys with `['auto-social', …]` prefix |
| Forgetting to add `auto-social` folder breaks phase 05 imports | Low | Low | Add `.gitkeep` in this phase |
| TS strict mode rejects `URLSearchParams` quirk | Low | Low | Standard pattern; tested in build step |

## Security Considerations

- Frontend admin gating — render hidden for non-admins. v1: show nav for all logged-in users; backend rejects with 403 (defense in depth). Future: filter `NAV_LINKS` by uid claim.
- ID token already set up via `AuthContext`; no per-page work.

## Next Steps

- Phase 05: implement List, Create, Channels, Stats components.
- Phase 06: implement Calendar component.
- Open question: should we expose `/auto-social` route only for admin uids client-side too (early redirect)? Decision: render `<AccessDenied/>` if `user.uid` not in admin list — but admin list is server-side only. Workaround v1: rely on backend 403; UI shows error toast on failed list call. Acceptable.
