# Phase 05 — Frontend: List + Create + Channels + Stats

## Context Links

- Phase 04 page skeleton: `frontend/src/pages/AutoSocialPage.tsx`
- API + hooks: `frontend/src/api/autoSocial.ts`, `hooks/useAutoSocial.ts`
- Existing modal pattern: parts of `frontend/src/pages/VertexConfigPage.tsx`
- Existing toast pattern: `useToasts` + `ToastContainer` in `VertexConfigPage.tsx`
- Existing styled badges: `frontend/src/components/shared/NeonBadge.tsx`, `MiniSparkBar.tsx`

## Overview

- **Priority:** P2
- **Status:** pending
- **Description:** Replace List/Channels/Stats placeholders with real components. Add `PostCreateModal` triggered from page header.

## Key Insights

- Use existing `NeonBadge` for status pills; map status → color: pending=slate, queued=cyan, uploading=amber, posted=green, failed=red, cancelled=slate.
- Modal style from `VertexConfigPage` — fixed overlay, centered card with `bg-dark-700 border border-dark-600 rounded-xl p-6 max-w-lg`. Reuse pattern, do not introduce a modal library.
- Toasts: lift `useToasts`/`ToastContainer` into a tiny shared module `components/shared/Toast.tsx` (refactor — DRY); then both `VertexConfigPage` and `AutoSocialPage` import. **Decision: KEEP duplicated for now (YAGNI); revisit only if a 3rd page needs toasts.** Document as tech debt in phase 08.
- Datetime input: native `<input type="datetime-local">` works in all modern browsers. Convert to UTC ISO before submit. Display saved values in ICT.
- Hashtag input: comma-separated string in UI; split on submit; preview as chips.
- Channels are read-mostly; add a "Sync from Buffer" button that calls `useSyncChannels()` mutation.

## Requirements

### Functional

- F05-1 `PostsList.tsx` — table with columns: Schedule (ICT), Account, Caption (truncate 60 chars), Status badge, Posted URL link (when posted), Actions (Edit, Delete, Cancel).
- F05-2 Filter row above list: Status select, Date-from, Date-to. State drives `useAutoSocialPosts(filters)`.
- F05-3 `PostCreateModal.tsx` — fields: Account dropdown (read from `/channels`), Channel auto-resolved by account, Video URL paste, optional Thumbnail URL paste, Caption textarea (max 2200 chars; counter), Hashtags input (comma-separated), Schedule time `<input type="datetime-local">` (assumed ICT). Submit calls `useCreatePost`.
- F05-4 Form validation client-side: video_url must start `http`, caption non-empty, schedule_time > now.
- F05-5 `ChannelsList.tsx` — table: Service icon (TikTok logo), Name, Service ID, Timezone, Connected badge, External link, Last synced. Sync button at top-right.
- F05-6 `StatsCards.tsx` — grid of 4 stat tiles: Pending+Queued (= "Scheduled"), Posted (last 7d), Failed (last 7d), Total. Polls `useStats()` every 30s.
- F05-7 Edit modal (reuse PostCreateModal in edit mode) — pre-fill, only allow editing fields if `status === 'pending'`. Status `queued`/`failed` → read-only.
- F05-8 Delete confirm — `confirm()` dialog before `useDeletePost`. Shows warning when `buffer_post_id` set: "This will delete the post in Buffer too."

### Non-Functional

- Optimistic updates not required v1 — invalidate-and-refetch is fine.
- All times displayed in ICT; sortable by raw `schedule_time` (UTC ISO).
- Build green; no TS `any`.
- File size cap: 200 lines per code-standards. Split if exceeded.

## Architecture

### Component Tree

```
AutoSocialPage (modified phase 04 shell)
├── Header
│   ├── Title
│   ├── Tab nav
│   └── + Schedule Post button → opens PostCreateModal (mode=create)
├── tab=list      → PostsList ──row click──▶ PostCreateModal (mode=edit)
├── tab=channels  → ChannelsList
├── tab=stats     → StatsCards
└── tab=calendar  → (phase 06)

PostCreateModal
├── Form fields
├── Live preview tile (caption + first hashtag wrap)
└── Submit / Cancel
```

### Form State Machine

```
idle ──open──▶ editing ──submit──▶ submitting ──success──▶ closed (toast green)
                                              ──error─────▶ editing (toast red, error inline)
                              ──cancel───────▶ closed
```

## Related Code Files

### Create

- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\PostsList.tsx` (~180 lines)
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\PostCreateModal.tsx` (~190 lines)
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\ChannelsList.tsx` (~120 lines)
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\StatsCards.tsx` (~80 lines)
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\StatusBadge.tsx` (~40 lines) — small helper
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\timeFormat.ts` (~30 lines) — ICT formatter

### Modify

- `C:\Users\Admin\hapura-command\frontend\src\pages\AutoSocialPage.tsx` — wire components into tabs, add state for modal open/edit.

### Delete

- None.

## Implementation Steps

1. **Create `timeFormat.ts`**:
   ```typescript
   const ICT_TZ = 'Asia/Ho_Chi_Minh'
   export function formatICT(iso: string): string {
     try {
       return new Intl.DateTimeFormat('en-GB', {
         timeZone: ICT_TZ, year:'numeric', month:'2-digit', day:'2-digit',
         hour:'2-digit', minute:'2-digit', hour12:false,
       }).format(new Date(iso)).replace(',', '')
     } catch { return iso }
   }
   export function localInputToUTCISO(local: string): string {
     // local from <input type=datetime-local>, e.g. "2026-05-03T08:30"
     // Treat as ICT time → convert to UTC ISO
     const ictDate = new Date(local + ':00+07:00')
     return ictDate.toISOString()
   }
   export function utcISOToLocalInput(iso: string): string {
     const d = new Date(iso)
     // format yyyy-MM-ddTHH:mm in ICT
     const fmt = new Intl.DateTimeFormat('en-CA', {
       timeZone: ICT_TZ, year:'numeric', month:'2-digit', day:'2-digit',
       hour:'2-digit', minute:'2-digit', hour12:false,
     }).formatToParts(d)
     const get = (t: string) => fmt.find(p => p.type === t)?.value ?? ''
     return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`
   }
   ```

2. **Create `StatusBadge.tsx`**:
   ```typescript
   const COLORS: Record<PostStatus, string> = {
     pending:   'bg-slate-700/40 border-dark-500 text-slate-400',
     uploading: 'bg-neon-amber/10 border-neon-amber/30 text-neon-amber',
     queued:    'bg-neon-cyan/10 border-neon-cyan/30 text-neon-cyan',
     posted:    'bg-neon-green/10 border-neon-green/30 text-neon-green',
     failed:    'bg-neon-red/10 border-neon-red/30 text-neon-red',
     cancelled: 'bg-slate-800/40 border-dark-600 text-slate-600',
   }
   export function StatusBadge({ status }: { status: PostStatus }) { … }
   ```

3. **Create `StatsCards.tsx`** — fetch via `useStats`. 4 tiles in `grid grid-cols-1 md:grid-cols-4 gap-4`. Each tile: `bg-dark-700 border border-dark-600 rounded-xl p-4` + label (mono uppercase tracking-wider) + big number (`font-game text-3xl`).

4. **Create `ChannelsList.tsx`**:
   - Table: Service, Name, Service ID, Timezone, Connected, Link, Last Synced.
   - Top-right: `Sync from Buffer` button → `useSyncChannels.mutate()`. Show spinner during pending. Toast on success/error.
   - Empty state: "No channels yet. Click Sync to import from Buffer."

5. **Create `PostsList.tsx`**:
   - Filter row: status `<select>`, from `<input type=date>`, to `<input type=date>`.
   - Use `useAutoSocialPosts({status, from, to})`.
   - Table rows: clickable → opens edit modal (pass row data up via callback prop).
   - Actions cell: Edit (pencil), Delete (trash). Delete confirms with warning if `buffer_post_id` set.
   - Show `last_error` truncated under failed rows in `text-neon-red text-xs`.
   - Empty state: "No scheduled posts yet."

6. **Create `PostCreateModal.tsx`**:
   - Props: `open: boolean`, `mode: 'create'|'edit'`, `post?: AutoSocialPost`, `onClose()`.
   - Fields:
     - Account `<select>` populated from `useChannels()` data — show `name (service)`. Channel ID auto-set on selection.
     - Video URL `<input type=url>` (validate starts http).
     - Thumbnail URL `<input type=url>` (optional).
     - Caption `<textarea rows=4>` + counter `{caption.length}/2200`.
     - Hashtags `<input>` placeholder `#tiktok, #viral`.
     - Schedule time `<input type="datetime-local">` (ICT).
   - Submit:
     - Validate (video_url, caption non-empty, time > now).
     - `localInputToUTCISO(scheduleInput)` → submit body.
     - On create: `useCreatePost.mutate(body)` ; on edit: `useUpdatePost.mutate({id, body})`.
     - Handle errors → show inline + toast.
   - Edit mode locking: if `post.status !== 'pending'`, disable all fields except a "Cancel post" button (calls `useUpdatePost({status:'cancelled'})` or `useDeletePost`).

7. **Modify `AutoSocialPage.tsx`**:
   - Replace placeholders with components.
   - Add modal state `{open, mode, post}`.
   - Header `+ Schedule Post` button → `setModal({open:true,mode:'create'})`.
   - PostsList row-click callback → `setModal({open:true,mode:'edit',post:row})`.
   - Render `<PostCreateModal {...modal} onClose={()=>setModal({open:false})}/>`.

8. **Build + smoke**:
   - `npm run build` green.
   - Local backend running (phase 02): create a post, see it in list, edit it, delete it. Toast on each.
   - Sync channels → see TikTok `xuantuanh8` row.

## Todo List

- [ ] Create `timeFormat.ts` with ICT helpers
- [ ] Create `StatusBadge.tsx`
- [ ] Create `StatsCards.tsx`
- [ ] Create `ChannelsList.tsx` with sync button
- [ ] Create `PostsList.tsx` with filters + actions
- [ ] Create `PostCreateModal.tsx` (create + edit modes)
- [ ] Wire components into `AutoSocialPage.tsx`
- [ ] Build green
- [ ] Manual smoke test (create + edit + delete + sync channels)

## Success Criteria

- All 4 tabs render real content (calendar still placeholder, expected).
- Create-post flow lands in Firestore (verified by listing endpoint or Firebase Console).
- Status badge colours correct for all 6 states.
- Times displayed in ICT consistently across list, modal, and stats.
- File-size guideline observed (≤200 lines/file; split otherwise).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `datetime-local` browser timezone confusion | High | High | All conversion goes through `localInputToUTCISO` / `utcISOToLocalInput`; assume ICT input strictly; test with browser TZ != ICT |
| Modal accidentally remains open after submit | Medium | Low | Mutation `onSuccess` calls `onClose` |
| Filter date input excludes events same-day | Medium | Medium | `from` translated to `00:00 ICT`, `to` to `23:59 ICT` before query |
| `useChannels` empty on first render → modal disabled | High | Low | Show "Sync channels first" CTA in modal account select if empty |
| Hashtag string parsing edge cases (extra spaces, `#` prefix) | Medium | Low | Normalize: split on `,`, trim, drop empties, ensure leading `#` |

## Security Considerations

- All API calls go through authenticated `client.ts` — no manual fetch.
- React escapes caption content by default — safe for display.
- Video URL validation client-side is UX only; server still validates and Buffer validates fetchability.

## Next Steps

- Phase 06: build calendar view reusing same fetch + status badge.
- Phase 07: GCS bucket — once available, add an "Upload" button next to "Paste URL" (out of v1 scope; future).
- Open question: how to handle very long captions in list table? Decision: truncate to 60 chars + `…`; show full on row-click.
