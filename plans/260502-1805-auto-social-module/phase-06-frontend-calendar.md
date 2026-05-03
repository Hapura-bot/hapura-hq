# Phase 06 — Frontend Calendar View

## Context Links

- Phase 05 components: `frontend/src/components/auto-social/*`
- Hook + API: `frontend/src/hooks/useAutoSocial.ts`, `api/autoSocial.ts`
- Time utils: `frontend/src/components/auto-social/timeFormat.ts`
- Existing animation tokens: `frontend/tailwind.config.js` (`fade-in-up`)

## Overview

- **Priority:** P3 (nice-to-have; List is functional baseline)
- **Status:** pending
- **Description:** Build month-grid calendar with clickable cells showing scheduled posts. Same-day clusters show count badge; clicking opens day detail panel.

## Key Insights

- Build vanilla — no calendar library. Month grid is 7×6 cells; logic <150 LOC.
- Reuse `StatusBadge` for per-post chips.
- Filters: month picker (prev/next arrow + label). State persists via URL query `?month=2026-05`.
- Default tab is calendar — must perform well: query 1 month range only (not all posts).

## Requirements

### Functional

- F06-1 Calendar grid: weekdays header (Mon–Sun, ICT week start = Monday), 6 rows × 7 cells = current month + leading/trailing days greyed.
- F06-2 Each cell shows: day number top-left; up to 3 post chips (status colour bar + first 14 chars of caption); "+N more" if overflow.
- F06-3 Click a cell → side drawer (or below-grid panel) lists all posts for that day with action menus (re-uses StatusBadge + delete).
- F06-4 Click a post chip → opens edit modal (reuse `PostCreateModal` from phase 05).
- F06-5 Top bar: month label `Tháng 5/2026`, prev/next arrows, "Today" button.
- F06-6 New post on empty cell: small `+` button visible on hover → opens `PostCreateModal` with pre-filled date.

### Non-Functional

- Calendar mounts ≤150ms after data lands.
- Single query per month change (refetched via TanStack on month state change).
- Animations subtle: `fade-in-up` for chips on month change.

## Architecture

### Component Tree

```
PostsCalendar
├── CalendarHeader (prev/next, month label, today btn)
├── WeekdayRow (Mon..Sun)
└── MonthGrid
    ├── DayCell × 42
    │   ├── DayNumber
    │   ├── PostChip × ≤3
    │   └── "+N more" link
    └── DayDetailDrawer (mounted on cell click)
```

### Data Fetching

```
calendarMonth state (e.g. "2026-05")
   │
   ├── from = first-of-month ICT → UTC ISO
   ├── to   = last-of-month  ICT → UTC ISO
   │
   ▼
useAutoSocialPosts({ from, to, limit: 500 })
   │
   ▼
group posts by ICT date string (YYYY-MM-DD) → Record<string, Post[]>
```

## Related Code Files

### Create

- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\PostsCalendar.tsx` (~180 lines)
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\DayDetailDrawer.tsx` (~110 lines)
- `C:\Users\Admin\hapura-command\frontend\src\components\auto-social\calendarUtils.ts` (~80 lines) — date math helpers (month grid, ICT day-key, etc.)

### Modify

- `C:\Users\Admin\hapura-command\frontend\src\pages\AutoSocialPage.tsx` — replace calendar placeholder with `<PostsCalendar onEditPost={openEdit} onCreatePost={openCreateForDate} />`.

### Delete

- None.

## Implementation Steps

1. **Create `calendarUtils.ts`**:
   - `monthCells(year: number, month1to12: number): { date: Date; isCurrentMonth: boolean }[]` — returns 42 cells, week-start Monday.
   - `dayKeyICT(iso: string): string` — `YYYY-MM-DD` of post in ICT.
   - `monthRangeICTtoUTC(year, month) → { from: string; to: string }` — boundaries as UTC ISO.
   - `prevMonth`, `nextMonth`, `todayMonth` helpers.

2. **Create `DayDetailDrawer.tsx`**:
   - Props: `dayKey: string`, `posts: AutoSocialPost[]`, `onClose()`, `onEdit(post)`, `onCreate()`.
   - Slide-in from right (`fixed right-0 top-14 bottom-0 w-96 bg-dark-800 border-l border-dark-600`); overlay click closes.
   - Lists posts vertically with StatusBadge + caption + edit/delete buttons.
   - Footer: `+ New for {dayKey}` btn → `onCreate()`.

3. **Create `PostsCalendar.tsx`**:
   - Props: `onEditPost(post)`, `onCreatePost(dateISO?)`.
   - State `[year,month]` initialised from URL `?month=YYYY-MM` (fallback today).
   - On change, write `?month=` via `useSearchParams` from react-router.
   - Compute `cells = monthCells(year,month)` and `range = monthRangeICTtoUTC(year,month)`.
   - `useAutoSocialPosts(range, limit:500)` (note: extend hook to support `limit` if not yet).
   - Group posts via `dayKeyICT`; pass into rendered cells.
   - Cell layout: `bg-dark-800 border border-dark-600 rounded p-1.5 min-h-24 hover:border-brand/50 transition-colors`. Greyed cells: `opacity-40`.
   - PostChip inside cell: `flex items-center gap-1 text-xs truncate` with status border-left coloured 2px.
   - On cell click → set `selectedDay`; open `DayDetailDrawer`.
   - On chip click (event.stopPropagation) → `onEditPost(post)`.

4. **Modify `AutoSocialPage.tsx`** to mount `PostsCalendar`:
   - Pass `onEditPost` (sets modal `mode=edit`) and `onCreatePost(date?)` (opens create modal with `schedule_time` pre-set to `09:00 ICT` of the chosen date).

5. **Extend `useAutoSocial.ts`** if needed:
   - `useAutoSocialPosts(filters?: {status?,from?,to?,limit?})` — accept optional `limit`. Pass through to API.

6. **Test states**:
   - Empty month (no posts) → empty cells.
   - Month with 5+ posts on one day → "+2 more" link opens drawer.
   - Click chip → opens edit modal.
   - Click empty cell → drawer; click `+ New for…` → create modal pre-filled.
   - Prev/next/today arrows update query param + refetch.

## Todo List

- [ ] Create `calendarUtils.ts` with month-grid + day-key helpers
- [ ] Create `DayDetailDrawer.tsx`
- [ ] Create `PostsCalendar.tsx`
- [ ] Wire calendar into `AutoSocialPage.tsx` tab
- [ ] Add URL query param sync via `useSearchParams`
- [ ] Build green
- [ ] Manual: prev/next month, click cell + chip flows

## Success Criteria

- Calendar renders 6×7 grid for current month with ICT-aligned day numbers.
- Posts grouped correctly by ICT day (verify around midnight UTC ↔ 07:00 ICT boundary).
- Drawer opens/closes; chip click bypasses drawer and opens edit modal.
- URL query param round-trips on share.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ICT vs UTC date drift mis-buckets posts at midnight | High | Medium | `dayKeyICT` derived from `Intl.DateTimeFormat` with `Asia/Ho_Chi_Minh` timezone; unit test boundary cases |
| Performance with 500+ posts | Low (v1) | Low | Limit 500/month; pagination future |
| Calendar layout breaks at sm width | Medium | Low | `min-w` + horizontal scroll on `<md`; fallback: list view always available |

## Security Considerations

- No new endpoints — read-only consumer.
- All actions go through phase 05 modal (already authenticated).

## Next Steps

- Phase 07: GCS bucket + e2e test.
- Future: drag-drop to reschedule (out of v1).
- Open question: should drawer support inline editing? Decision: NO — always open `PostCreateModal` for edits to avoid duplicate code paths.
