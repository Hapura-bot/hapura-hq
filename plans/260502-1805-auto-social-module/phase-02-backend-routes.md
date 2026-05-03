# Phase 02 — Backend Routes (CRUD + Channels + Stats)

## Context Links

- Existing route patterns: `C:\Users\Admin\hapura-command\backend\api\routes\projects.py`, `tasks.py`, `vertex_config.py`
- Existing auth dependency: `C:\Users\Admin\hapura-command\backend\api\deps.py` (`get_current_user`, `ALLOWED_EMAILS`)
- Phase 01 service/repo: `backend/auto_social/service.py`, `repo.py`
- **Maintenance middleware** (CRITICAL): `C:\Users\Admin\hapura-command\backend\main.py:42-52`

## Overview

- **Priority:** P1 (blocker for frontend & cron)
- **Status:** pending
- **Description:** Add `/api/v1/auto-social/*` REST routes — posts CRUD, channels list/sync, stats. Wire admin-only dependency. **Extend maintenance allow-list to permit the new prefix.**

## Key Insights

- Router registration is centralised in `main.py:54-62` — append one `app.include_router(auto_social_router, prefix="/api/v1")`.
- Maintenance middleware blocks ALL paths except `/api/v1/vertex-config` and `/health`. Must extend `_ALLOWED_PREFIXES` to include `/api/v1/auto-social` else module is inaccessible in production.
- Existing auth uses `get_current_user` returning Firebase uid — but it whitelists by `email`. New module needs uid whitelisting (per requirements). Add a sibling dependency `get_admin_uid` that wraps `get_current_user` and additionally checks `uid in settings.auto_social_admin_uids.split(",")`.
- Dev mode shortcut: `get_current_user` returns `"dev"` when `app_env == "development"` and no auth header. Match this — `get_admin_uid` returns `"dev"` in dev mode (so localhost dev works without configuring admin uids).
- All Pydantic body validation goes through models from phase 01.
- Use `BackgroundTasks` for `channels/sync` (Buffer call may block 1–3s). Pattern matches `agents.py::_run_agent`.

## Requirements

### Functional

- F02-1 `POST /auto-social/posts` — body `AutoSocialPostCreate`, returns full post.
- F02-2 `GET /auto-social/posts` — query params: `status?`, `from?` (ISO date), `to?` (ISO date), `limit?` (default 200). Returns list ordered by `schedule_time` ascending.
- F02-3 `GET /auto-social/posts/{id}` — single post.
- F02-4 `PUT /auto-social/posts/{id}` — body `AutoSocialPostUpdate`. Allowed only if status in `{pending, queued, failed, cancelled}` (not `uploading`/`posted`).
- F02-5 `DELETE /auto-social/posts/{id}` — if `buffer_post_id` set AND status ∈ `{queued, uploading}`, call `BufferClient.delete_post` first; ignore Buffer 404; then delete Firestore doc.
- F02-6 `GET /auto-social/channels` — returns cached channel list from Firestore.
- F02-7 `POST /auto-social/channels/sync` — synchronous; calls `service.sync_channels`; returns updated list.
- F02-8 `GET /auto-social/stats` — aggregates Firestore counts by status + posted_last_7d.

### Non-Functional

- All endpoints `@router.dependencies = [Depends(get_admin_uid)]` (admin-only).
- Time inputs accepted as ISO 8601 (with TZ) OR ICT-style `DD/MM/YYYY HH:MM`. Service helper coerces to UTC ISO before persisting.
- Response models declared on all GET endpoints for OpenAPI clarity.
- Request validation 422 → not 500.

## Architecture

### Route Map

```
POST   /api/v1/auto-social/posts                  → create post
GET    /api/v1/auto-social/posts                  → list (filters)
GET    /api/v1/auto-social/posts/{id}             → get one
PUT    /api/v1/auto-social/posts/{id}             → update editable fields
DELETE /api/v1/auto-social/posts/{id}             → delete (cancel buffer + remove)

GET    /api/v1/auto-social/channels               → list cached
POST   /api/v1/auto-social/channels/sync          → pull from Buffer + upsert

GET    /api/v1/auto-social/stats                  → counts dict
```

Cron endpoints (`/cron/dispatch`, `/cron/reconcile`) are in phase 03 file but live in same router.

### Auth Layer

```
api/deps.py
  get_current_user (existing) ── authenticate
        └── get_admin_uid (new) ── authorize against AUTO_SOCIAL_ADMIN_UIDS
              └── used by all /auto-social/* except /cron/*
```

Cron endpoints use `X-Hapura-Scheduler-Secret` (matches existing scheduler routes pattern in `routes/scheduler.py`). Decision: rename to match existing convention — header is `X-Scheduler-Secret`. (User spec says `X-Hapura-Scheduler-Secret`; existing code uses `X-Scheduler-Secret`. **Use existing `X-Scheduler-Secret`** to keep one secret-header convention. Document the rename in `plan.md`.)

## Related Code Files

### Create

- `C:\Users\Admin\hapura-command\backend\api\routes\auto_social.py` (~350 lines; split if > 200 per code-standards)

### Modify

- `C:\Users\Admin\hapura-command\backend\main.py`:
  - Line 14 area: `from api.routes.auto_social import router as auto_social_router`
  - Line 42 area: extend `_ALLOWED_PREFIXES` tuple to include `"/api/v1/auto-social"`
  - Line 62 area: `app.include_router(auto_social_router, prefix="/api/v1")`
- `C:\Users\Admin\hapura-command\backend\api\deps.py`: add `get_admin_uid` dependency.

### Delete

- None.

## Implementation Steps

1. **Add `get_admin_uid` dependency** in `backend/api/deps.py`:
   ```python
   async def get_admin_uid(uid: str = Depends(get_current_user)) -> str:
       settings = get_settings()
       if settings.app_env == "development":
           return uid
       allowed = {u.strip() for u in settings.auto_social_admin_uids.split(",") if u.strip()}
       if not allowed:
           raise HTTPException(status_code=503, detail="auto-social admin allow-list not configured")
       if uid not in allowed:
           raise HTTPException(status_code=403, detail="Admin access required for auto-social")
       return uid
   ```
   - Import `get_settings` at top.

2. **Create `backend/api/routes/auto_social.py`** with sections:

   ### a. Header & helpers
   - `from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Query`
   - `from auto_social import service, repo` ; `from auto_social.buffer_client import BufferClient, BufferError`
   - `from auto_social.models import AutoSocialPostCreate, AutoSocialPostUpdate, ...`
   - `from api.deps import get_admin_uid`
   - `from config import get_settings`
   - `router = APIRouter(prefix="/auto-social", tags=["auto-social"])`
   - `def _coerce_schedule_time(s: str) -> str:` — parse either ISO or `DD/MM/YYYY HH:MM` (using `time_utils.parse_schedule_time`); return UTC ISO string.

   ### b. Posts CRUD
   ```
   @router.post("/posts", response_model=AutoSocialPost, status_code=201)
   async def create_post(body: AutoSocialPostCreate, uid: str = Depends(get_admin_uid)):
       body.schedule_time = _coerce_schedule_time(body.schedule_time)
       posts = repo.PostsRepo()
       return posts.create(body, created_by=uid)
   ```
   - Validate `schedule_time > now`; reject 400 if past.
   - Validate `caption + hashtags` text length ≤ 2200 chars (TikTok limit).

   ### c. List & filters
   ```
   @router.get("/posts", response_model=list[AutoSocialPost])
   async def list_posts(
       status: str | None = Query(None),
       from_: str | None = Query(None, alias="from"),
       to: str | None = Query(None),
       limit: int = Query(200, ge=1, le=500),
       uid: str = Depends(get_admin_uid),
   ): ...
   ```
   - Filter dict assembled and passed to `posts.list({...}, limit=limit)`.

   ### d. Get / Update / Delete
   - `GET /posts/{id}` → 404 if not found.
   - `PUT /posts/{id}`:
     - Reject if current status `in {"uploading","posted"}` (immutable post-publish).
     - If `schedule_time` provided, coerce.
     - For `status` updates: only `cancelled` allowed (and only from `pending` or `failed`); otherwise 400.
   - `DELETE /posts/{id}`:
     - Get current.
     - If `buffer_post_id` AND status in `{queued, uploading}`: try `BufferClient().delete_post(buffer_post_id)`; on `BufferError` log and continue.
     - `posts.delete(id)` ; return 204.

   ### e. Channels
   - `GET /channels` → `repo.ChannelsRepo().list()`.
   - `POST /channels/sync`:
     - Synchronous (Buffer round-trip is fast; user expects fresh list).
     - `client = BufferClient()` ; `service.sync_channels(client)` ; return list.
     - On `BufferAuthError` → 502 "Buffer auth failed — check BUFFER_API_KEY".

   ### f. Stats
   - `GET /stats` → `AutoSocialStats`. Implementation:
     - Single-pass over `auto_social_posts` collection (limit 1000) — counts by status + count `posted_at >= now-7d`.
     - For larger volumes, future optimization: maintain a counters doc updated on transitions. Not needed v1.

3. **Wire router in `main.py`**:
   - Add import line near other route imports.
   - Update `_ALLOWED_PREFIXES = ("/api/v1/vertex-config", "/api/v1/auto-social", "/health")`.
   - Add `app.include_router(auto_social_router, prefix="/api/v1")` at bottom.

4. **Compile check**:
   - `cd backend && python -c "import main; print(len(main.app.routes))"` — verify no import errors.

5. **Manual smoke test (local)**:
   - Start server `uvicorn main:app --port 8099 --reload`.
   - `curl -X POST http://localhost:8099/api/v1/auto-social/channels/sync` (dev mode = no auth needed).
   - `curl http://localhost:8099/api/v1/auto-social/stats`.
   - Confirm Firestore `auto_social_channels` collection populated.

## Todo List

- [ ] Add `get_admin_uid` to `api/deps.py`
- [ ] Create `api/routes/auto_social.py` with helpers + CRUD + channels + stats
- [ ] Add `_coerce_schedule_time` helper
- [ ] Add 422/400/403/502 error mappings
- [ ] Modify `main.py` import + middleware allow-list + router include
- [ ] Compile check via `python -c "import main"`
- [ ] Local smoke: POST channels/sync + GET stats
- [ ] Verify Firestore writes in `hapura-hq` project console

## Success Criteria

- All 8 endpoints respond locally (200/201/204/4xx as designed).
- Maintenance middleware does NOT block `/api/v1/auto-social/*`.
- Non-admin Firebase users get 403 in production-like mode.
- Dev mode allows unauthenticated access (parity with rest of app).
- Channels sync populates Firestore with TikTok channel `xuantuanh8` (id `69f5bb6f5c4c051afa015f6d`).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Forgetting maintenance allow-list extension → 503 in prod | High | Critical | Phase 08 deploy step explicitly curls the prefix post-deploy |
| `get_admin_uid` raises 503 when env empty → blocks dev | Low | Medium | Skip uid-whitelist in `app_env=development` |
| Concurrent CREATE + DELETE race | Low | Medium | Firestore single-doc ops are atomic; race not catastrophic |
| `_coerce_schedule_time` mis-parses ICT input as UTC | Medium | High | Unit test both formats (ISO with Z, ICT DD/MM/YYYY HH:MM); reject ambiguous |
| Buffer delete returns 404 when post already published | Medium | Low | Treat 404 as success; log warn |

## Security Considerations

- Admin uid whitelist enforced at every non-cron endpoint.
- Cron endpoints reuse existing `SCHEDULER_SECRET` — do NOT add a separate secret (DRY).
- DELETE requires authenticated admin; never allow unauth deletion of Buffer-bound posts.
- Caption stored verbatim; sanitize on render in frontend (React escapes by default).

## Next Steps

- Phase 03: cron endpoints + Cloud Scheduler job creation.
- Phase 04: frontend can start consuming API once 02 deployed to local backend.
- Open question: should `PUT /posts/{id}` re-coerce `schedule_time` if value already `queued` in Buffer? Decision: editing `schedule_time` only allowed when status `pending` (not yet sent to Buffer); reject 409 otherwise. Document in route.
