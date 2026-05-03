---
title: "Auto-Social Module — TikTok Scheduler via Buffer GraphQL"
description: "Internal admin module inside hq.hapura.vn for scheduling TikTok posts via Buffer. Replaces standalone auto-social Python service."
status: pending
priority: P2
effort: 22h
branch: main
tags: [hapura-command, auto-social, buffer, tiktok, firestore, cloud-scheduler]
created: 2026-05-02
---

## Goal

Internal-only `/auto-social` module inside hapura-command (hq.hapura.vn). Admin schedules TikTok posts → Buffer GraphQL API → posts publish → status syncs back. Single source of truth: Firestore on `hapura-hq` project. No Sheets, no SQLite, no separate FastAPI service.

## Phase Table

| # | File | Status | Effort | Owner |
|---|------|--------|--------|-------|
| 01 | [phase-01-backend-module-skeleton.md](./phase-01-backend-module-skeleton.md) | pending | 3h | backend |
| 02 | [phase-02-backend-routes.md](./phase-02-backend-routes.md) | pending | 3h | backend |
| 03 | [phase-03-cron-and-scheduler.md](./phase-03-cron-and-scheduler.md) | pending | 3h | backend |
| 04 | [phase-04-frontend-page-skeleton.md](./phase-04-frontend-page-skeleton.md) | pending | 2h | frontend |
| 05 | [phase-05-frontend-list-and-create.md](./phase-05-frontend-list-and-create.md) | pending | 3h | frontend |
| 06 | [phase-06-frontend-calendar.md](./phase-06-frontend-calendar.md) | pending | 2h | frontend |
| 07 | [phase-07-gcs-bucket-and-e2e.md](./phase-07-gcs-bucket-and-e2e.md) | pending | 2h | infra |
| 08 | [phase-08-deploy-and-docs.md](./phase-08-deploy-and-docs.md) | pending | 4h | devops |

Sum: 22h.

## Dependency Graph

```
01 → 02 → 03 → 07 → 08
       ↘
        04 → 05 → 06 → 08
```

- 01 unblocks 02 (models needed before routes)
- 02 unblocks 03 (CRUD must exist before cron writes)
- 02 unblocks 04 (frontend needs API stable)
- 05 needs 04; 06 needs 05 (Calendar reuses post fetcher)
- 07 (bucket) parallel with 03–06; required by 08 e2e
- 08 closes everything: deploy + scheduler job creation + docs

## Key Dependencies (External)

- **Buffer Personal API key** — already provisioned. Stored as Cloud Run secret `BUFFER_API_KEY` (new).
- **GCS bucket** `hapura-hq-tiktok-assets` — created in phase 07; public read; lifecycle 30d.
- **Cloud Scheduler** — uses existing `SCHEDULER_SECRET` mechanism (auto-social cron jobs added to `.github/workflows/deploy.yml`).
- **Firebase Auth** — same `get_current_user` dep. Whitelist Victor uid via new env `AUTO_SOCIAL_ADMIN_UIDS` (comma-separated).
- **Maintenance middleware** at `backend/main.py:42-52` currently returns 503 for everything outside `/api/v1/vertex-config` + `/health`. **Phase 02 MUST add `/api/v1/auto-social` to `_ALLOWED_PREFIXES`** OR remove the middleware. Decision: extend the allow-list (least disruptive).

## Risk Register (top items)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Maintenance middleware still active in production | High | Critical | Phase 02 adds `/api/v1/auto-social` to allow-list; phase 08 verifies via curl smoke test post-deploy |
| Buffer rate limit (100/15m, 500/24h) hit by reconcile | Medium | Medium | Reconcile only fetches non-terminal posts; cap query to 50 docs/run; backoff on 429 |
| GCS public bucket leaks PII | Low | High | Bucket holds video assets only, no caption/PII; lifecycle 30d auto-cleanup |
| Firebase admin uid drift breaks auth | Low | Medium | Whitelist via env var, not code constant; document re-issue procedure in phase 08 |
| Cloud Scheduler dispatch overlaps reconcile and double-acts a row | Medium | Medium | Status transition gated by atomic Firestore `update` with `WHERE status == 'pending'` filter; idempotent state machine |
| Buffer schema changes (e.g. `externalLink` field rename) | Low | High | BufferClient ported wholesale from verified working code; reconcile is read-only & error-tolerant; failures logged not crashed |

## Backwards Compatibility / Migration

- No migration: clean greenfield. Old `auto-social` Python service runs in parallel until cutover. After phase 07 e2e green: **Victor manually decommissions** `C:\Users\Admin\auto-social\` (out of scope of this plan).
- No Firestore schema rewrites in existing collections — new collections `auto_social_posts`, `auto_social_channels` only.
- No frontend route conflicts — `/auto-social` is new.

## Success Criteria (DoD)

- [ ] Live scheduled post visible at hq.hapura.vn/auto-social
- [ ] Post → Buffer → TikTok lifecycle completes (manual e2e via test channel)
- [ ] Reconcile updates Firestore within 10min of TikTok publish
- [ ] Telegram alerts fire on `failed` status
- [ ] CLAUDE.md + dev-roadmap updated
- [ ] All deprecation notes added to old `auto-social/CLAUDE.md`

## Files Created (top level)

- `backend/auto_social/` — new package (client, repo, models, service)
- `backend/api/routes/auto_social.py` — new router
- `frontend/src/api/autoSocial.ts` + `frontend/src/hooks/useAutoSocial.ts`
- `frontend/src/pages/AutoSocialPage.tsx`
- `frontend/src/components/auto-social/` — components folder

## Out of Scope (v1)

- Multi-platform (IG, FB, Threads) — Buffer supports but not required
- Direct video upload UI (paste URL only in v1)
- AI caption generation — manual entry only
- Bulk/CSV import
- Per-post scheduling rules (day-of-week templates)
