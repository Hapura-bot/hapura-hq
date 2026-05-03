# Phase 01 — Backend Module Skeleton

## Context Links

- Buffer client to port: `C:\Users\Admin\auto-social\src\auto_social\notify\buffer_client.py` (verified Phase A live test 2026-05-02)
- Time utils to port: `C:\Users\Admin\auto-social\src\auto_social\utils\time_utils.py`
- Reconcile logic reference (re-write in service.py): `C:\Users\Admin\auto-social\src\auto_social\scheduler\reconcile_job.py`
- Existing config pattern: `C:\Users\Admin\hapura-command\backend\config.py`
- Existing route convention: `C:\Users\Admin\hapura-command\backend\api\routes\projects.py`, `vertex_config.py`
- Existing models pattern: `C:\Users\Admin\hapura-command\backend\models.py`

## Overview

- **Priority:** P1 (blocker for all later phases)
- **Status:** pending
- **Description:** Create `backend/auto_social/` package: Buffer client (port as-is), time utils (port as-is), Pydantic models, Firestore repository, service layer (post lifecycle).

## Key Insights

- BufferClient was verified end-to-end 2026-05-02 — port without rewrite. Only swap `from auto_social.config import get_settings` → `from config import get_settings` and read `settings.buffer_api_key` / `settings.buffer_graphql_url` (new fields in `Settings`).
- Reconcile logic must be rewritten: the source uses SQLAlchemy + Sheets — replace with Firestore queries.
- ICT timezone helpers (`time_utils.py`) port direct, no SQLite-specific bits remain after dropping `now_utc_naive` and `ict_to_naive` (kept for compatibility in case future code wants UTC-naive).
- Firestore prefers `firestore.SERVER_TIMESTAMP` for `created_at`/`updated_at` — match this codebase convention (see `tasks.py` uses `datetime.utcnow().isoformat()` strings; we follow same style for consistency).
- Status state machine: `pending → queued → uploading → posted` (terminal) | `failed` | `cancelled` (terminal).

## Requirements

### Functional

- F01-1 BufferClient class identical API (`get_account`, `list_channels`, `get_post`, `create_scheduled_post`, `delete_post`).
- F01-2 ICT helpers: `parse_ict`, `format_ict`, `now_ict`, `to_iso_utc`.
- F01-3 Pydantic models: `AutoSocialPost`, `AutoSocialPostCreate`, `AutoSocialPostUpdate`, `AutoSocialChannel`, `AutoSocialStats`.
- F01-4 Firestore repository: `posts_repo` with `create / get / list / update / delete`, `channels_repo` with `upsert / list`.
- F01-5 Post-lifecycle service:
  - `dispatch_pending(now_utc, batch_limit=10) → DispatchSummary` — picks pending posts whose `schedule_time ≤ now`, calls Buffer, transitions `pending → queued | failed`.
  - `reconcile_active(batch_limit=50) → ReconcileSummary` — fetches non-terminal posts with `buffer_post_id`, queries Buffer, mirrors status.
  - `sync_channels(buffer_client) → list[AutoSocialChannel]` — pulls Buffer channels, upserts Firestore.

### Non-Functional

- All Buffer calls wrapped with `try/except BufferError` — never crash; record `last_error`, increment `attempts`.
- Idempotent dispatch — concurrent runs must not double-create Buffer posts (use Firestore transaction guarding `status` flip).
- All times stored in Firestore as ISO 8601 UTC strings (`schedule_time`, `posted_at`, `created_at`, `updated_at`).
- Compile check: `python -c "from auto_social.service import dispatch_pending"` passes.

## Architecture

### Component Diagram

```
backend/
└── auto_social/
    ├── __init__.py              # exports public symbols
    ├── buffer_client.py         # ported, BufferClient + dataclasses
    ├── time_utils.py            # ICT helpers
    ├── models.py                # Pydantic
    ├── repo.py                  # Firestore CRUD (PostsRepo, ChannelsRepo)
    ├── service.py               # dispatch_pending, reconcile_active, sync_channels
    └── alerts.py                # Telegram wrapper for failed posts
```

### Data Flow (dispatch)

```
Cloud Scheduler 5min POST /cron/dispatch
   → routes/auto_social.py::cron_dispatch
       → service.dispatch_pending(now_utc)
           → repo.list_pending_due(now_utc, limit=10)
           → for each post:
               atomic_transition(id, from='pending', to='uploading')   # Firestore txn
               BufferClient.create_scheduled_post(...)
               on success: repo.update(id, status='queued', buffer_post_id, attempts+1)
               on BufferError: repo.update(id, status='failed', last_error, attempts+1)
                            + alerts.notify_failed(post)
```

### Data Flow (reconcile)

```
Cloud Scheduler 10min POST /cron/reconcile
   → routes/auto_social.py::cron_reconcile
       → service.reconcile_active(limit=50)
           → repo.list_non_terminal_with_buffer_id(limit=50)
           → for each post:
               BufferClient.get_post(buffer_post_id)
               map buffer.status → our status
               if changed → repo.update(id, status, posted_url, posted_at)
               if status==failed → alerts.notify_failed(post)
```

### State Machine

```
pending  ──schedule≤now──▶  uploading  ──Buffer createPost ok──▶  queued
                              │                                       │
                              └──Buffer error──▶ failed                ├─ Buffer status=sent ─▶ posted (terminal)
                                                                      └─ Buffer status=failed ─▶ failed
cancelled (manual via DELETE)
```

## Related Code Files

### Create

- `C:\Users\Admin\hapura-command\backend\auto_social\__init__.py`
- `C:\Users\Admin\hapura-command\backend\auto_social\buffer_client.py`
- `C:\Users\Admin\hapura-command\backend\auto_social\time_utils.py`
- `C:\Users\Admin\hapura-command\backend\auto_social\models.py`
- `C:\Users\Admin\hapura-command\backend\auto_social\repo.py`
- `C:\Users\Admin\hapura-command\backend\auto_social\service.py`
- `C:\Users\Admin\hapura-command\backend\auto_social\alerts.py`

### Modify

- `C:\Users\Admin\hapura-command\backend\config.py` — add fields:
  - `buffer_api_key: str = ""`
  - `buffer_graphql_url: str = "https://api.buffer.com"`
  - `auto_social_admin_uids: str = ""` (comma-separated Firebase uids)
  - `auto_social_default_channel_id: str = "69f5bb6f5c4c051afa015f6d"` (xuantuanh8 TikTok)
  - `gcs_assets_bucket: str = "hapura-hq-tiktok-assets"`
- `C:\Users\Admin\hapura-command\backend\.env.example` — append new vars

### Delete

- None.

## Implementation Steps

1. **Create package skeleton**
   - `mkdir backend/auto_social && touch backend/auto_social/__init__.py`

2. **Port BufferClient (1:1 except imports)**
   - Copy `auto_social/notify/buffer_client.py` → `backend/auto_social/buffer_client.py`
   - Replace `from auto_social.config import get_settings` → `from config import get_settings`
   - Verify `settings.buffer_api_key`, `settings.buffer_graphql_url` are read.
   - Keep `BufferAccount`, `BufferChannel`, `BufferPost`, `BufferError`, `BufferAuthError`, `BufferRateLimitError` exports.

3. **Port time_utils (drop SQLite-specific helpers)**
   - Copy `auto_social/utils/time_utils.py` → `backend/auto_social/time_utils.py`
   - Keep: `ICT`, `now_ict`, `parse_schedule_time`, `format_schedule_time`, `to_iso`.
   - Drop: `now_utc_naive`, `ict_to_naive` (not needed with Firestore).
   - Add: `parse_iso_utc(s) → datetime` for parsing Firestore strings.

4. **Define Pydantic models** in `models.py`:
   - `PostStatus = Literal["pending","uploading","queued","posted","failed","cancelled"]`
   - `AutoSocialPost(BaseModel)` fields: id (Optional[str]), account (str = "xuantuanh8"), channel_id (str), video_url (str), thumbnail_url (Optional[str]), caption (str), hashtags (list[str] = []), schedule_time (str — ISO UTC), status (PostStatus = "pending"), buffer_post_id (Optional[str]), posted_url (Optional[str]), posted_at (Optional[str]), attempts (int = 0), last_error (Optional[str]), created_by (str), created_at (str), updated_at (str)
   - `AutoSocialPostCreate(BaseModel)`: account, channel_id, video_url, thumbnail_url?, caption, hashtags, schedule_time (ISO ICT or UTC string)
   - `AutoSocialPostUpdate(BaseModel)`: caption?, hashtags?, schedule_time?, status? (only `cancelled` allowed via this path)
   - `AutoSocialChannel(BaseModel)`: id (= buffer_channel_id), service, name, service_id, timezone, is_disconnected, external_link, last_synced_at
   - `AutoSocialStats(BaseModel)`: pending, queued, uploading, posted, failed, cancelled, total, posted_last_7d
   - `DispatchSummary(BaseModel)`: checked, dispatched, failed
   - `ReconcileSummary(BaseModel)`: checked, updated, posted, failed

5. **Build Firestore repo** (`repo.py`):
   - Collections: `auto_social_posts`, `auto_social_channels`.
   - `_db()` helper mirrors existing pattern (`from firebase_admin import firestore; firestore.client()`).
   - `class PostsRepo`:
     - `create(create: AutoSocialPostCreate, created_by: str) → AutoSocialPost` — generate id via `db.collection().document()`, set timestamps, default status `pending`.
     - `get(id) → AutoSocialPost | None`.
     - `list(filters: dict = None, limit: int = 200, order_by="schedule_time") → list[AutoSocialPost]` — supports `status` and date range filters.
     - `update(id, patch: dict) → AutoSocialPost` — set `updated_at`.
     - `delete(id) → None`.
     - `list_pending_due(now_iso_utc: str, limit: int) → list[AutoSocialPost]` — `where status == "pending"` AND `where schedule_time <= now_iso_utc`, ordered ascending.
     - `list_non_terminal_with_buffer_id(limit: int) → list[AutoSocialPost]` — `where status not-in ["posted","failed","cancelled"]` AND `where buffer_post_id != null`.
     - `transition(id, expected_from: str, to: str) → bool` — uses Firestore transaction; returns False if current status != expected_from.
   - `class ChannelsRepo`:
     - `upsert(channel: AutoSocialChannel)` — use `set(merge=True)` keyed on buffer channel id.
     - `list() → list[AutoSocialChannel]`.

6. **Build service layer** (`service.py`):
   - `dispatch_pending(batch_limit=10) → DispatchSummary`:
     - `now_utc_iso = datetime.now(timezone.utc).isoformat()`
     - For each due post: `if not transition(id, 'pending', 'uploading'): continue` (someone else picked it up)
     - `client = BufferClient()`; call `create_scheduled_post(channel_id, text=caption + hashtags, due_at=parse_iso_utc(schedule_time), video_url, thumbnail_url, video_title=caption[:80])`
     - On success: `update(id, status='queued', buffer_post_id=p.id, attempts+1)`
     - On `BufferError`: `update(id, status='failed', last_error=str(e)[:500], attempts+1)`; `alerts.notify_failed(post)`
   - `reconcile_active(batch_limit=50) → ReconcileSummary`:
     - Iterate `list_non_terminal_with_buffer_id`, call `client.get_post(buffer_post_id)`, map status.
     - Status mapping table identical to `auto_social/scheduler/reconcile_job.py:_BUFFER_TO_STATUS`.
     - On `failed` transition (not previously failed): `alerts.notify_failed(post)`.
   - `sync_channels(client: BufferClient) → list[AutoSocialChannel]`:
     - `account = client.get_account()`; `channels = client.list_channels(account.organization_id)`
     - For each: upsert to repo; return list.

7. **Build Telegram alerts** (`alerts.py`):
   - `notify_failed(post: AutoSocialPost) → None` — composes Markdown message; calls `from agents.telegram import send_telegram_sync`; reads `settings.telegram_bot_token`, `settings.telegram_chat_id`. Non-fatal on failure.
   - Format: `🚨 *AUTO-SOCIAL FAIL*\n*{account}* | sched {schedule_time}\nCaption: {caption[:80]}…\nError: {last_error}`

8. **Update `config.py`** (see Modify list above).

9. **Update `.env.example`** with:
   ```
   BUFFER_API_KEY=
   AUTO_SOCIAL_ADMIN_UIDS=
   AUTO_SOCIAL_DEFAULT_CHANNEL_ID=69f5bb6f5c4c051afa015f6d
   GCS_ASSETS_BUCKET=hapura-hq-tiktok-assets
   ```

10. **Compile check**:
    - `cd backend && python -c "from auto_social import service, repo, models, buffer_client, time_utils, alerts; print('ok')"`
    - Run `python -c "from config import get_settings; s=get_settings(); print(s.buffer_graphql_url, s.gcs_assets_bucket)"` — expect new fields visible.

## Todo List

- [ ] Create `backend/auto_social/__init__.py`
- [ ] Port `buffer_client.py` (replace import line only)
- [ ] Port `time_utils.py` (drop UTC-naive helpers, add `parse_iso_utc`)
- [ ] Create `models.py` with Pydantic schemas + status literal
- [ ] Create `repo.py` with `PostsRepo`, `ChannelsRepo`, atomic `transition`
- [ ] Create `service.py` with `dispatch_pending`, `reconcile_active`, `sync_channels`
- [ ] Create `alerts.py` with `notify_failed`
- [ ] Add new fields to `config.py`
- [ ] Update `.env.example`
- [ ] Run compile check

## Success Criteria

- All 7 files compile without import errors.
- `from auto_social.service import dispatch_pending` works from `backend/`.
- BufferClient initialises with `BUFFER_API_KEY` env var (no hard-coded fallback).
- `PostsRepo.transition()` uses Firestore transaction (verifiable in source).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Settings mutation breaks Vertex Config Hub by reordering env load order | Low | Medium | Add fields at bottom of `Settings` class only |
| Firestore transaction race on `transition` mis-implemented | Medium | High | Use `firestore.transactional` decorator; unit-test in phase 02 |
| ICT vs UTC confusion in `schedule_time` storage | Medium | High | Always store as UTC ISO; only convert to ICT in UI |
| Buffer rate limit hit during init `sync_channels` | Low | Low | Channels are 1-shot per call, called manually only |

## Security Considerations

- `BUFFER_API_KEY` never logged; passed only via env.
- BufferClient request method already strips body in errors to 200 chars — preserves; do not log full GraphQL responses.
- `AutoSocialPost.created_by` always set from authenticated `uid` — never client-provided.

## Next Steps

- Phase 02: build CRUD routes that use this service layer.
- Open question: do we want a `cancel` semantic that also calls Buffer `delete_post`? Current plan: `DELETE /posts/{id}` calls `BufferClient.delete_post` if `buffer_post_id` set, then deletes Firestore doc. If too aggressive, fallback to `status=cancelled`. Decision: implement BOTH — `DELETE` removes; `PATCH status=cancelled` keeps record for audit.
