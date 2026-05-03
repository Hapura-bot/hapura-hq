# Phase 03 — Cron Endpoints + Cloud Scheduler Wiring

## Context Links

- Existing scheduler endpoint pattern: `C:\Users\Admin\hapura-command\backend\api\routes\scheduler.py`
- Existing Cloud Scheduler upsert script: `C:\Users\Admin\hapura-command\.github\workflows\deploy.yml:133-198`
- Service entry points: `backend/auto_social/service.py::dispatch_pending`, `reconcile_active`
- Existing scheduler secret env: `SCHEDULER_SECRET` in `config.py` and Cloud Run

## Overview

- **Priority:** P1
- **Status:** pending
- **Description:** Add `/cron/dispatch` (5min) and `/cron/reconcile` (10min) endpoints. Add Cloud Scheduler jobs in CI workflow. Make Buffer dispatch + status sync run automatically.

## Key Insights

- **Reuse the scheduler header** `X-Scheduler-Secret` (existing convention; see `routes/scheduler.py::_verify`). Do NOT introduce `X-Hapura-Scheduler-Secret` despite spec — DRY.
- Cloud Scheduler upsert lives in CI: `setup-scheduler` job runs after backend deploy. Append two `upsert_job` lines.
- Dispatch should run as background task to release the Cloud Scheduler HTTP request quickly (3s budget per call). But: the work itself completes inside ~10s for batch=10; can run inline. Decision: **run inline** — simpler, summary returned in response is observable in Cloud Scheduler logs.
- Reconcile is read-mostly and bounded to 50 docs; runs inline as well.
- Both endpoints idempotent — safe to retry.
- `time-zone="Asia/Ho_Chi_Minh"` already used by all existing jobs — keep consistent.

## Requirements

### Functional

- F03-1 `POST /api/v1/auto-social/cron/dispatch` — header `X-Scheduler-Secret`. Body ignored. Returns `DispatchSummary`.
- F03-2 `POST /api/v1/auto-social/cron/reconcile` — header `X-Scheduler-Secret`. Returns `ReconcileSummary`.
- F03-3 Cloud Scheduler job `auto-social-dispatch` runs every 5min.
- F03-4 Cloud Scheduler job `auto-social-reconcile` runs every 10min.

### Non-Functional

- Endpoint timeout 60s (default Cloud Run is 300s, plenty of headroom).
- On Buffer auth failure → return 200 with `errors: ["BUFFER_API_KEY missing"]` and Telegram alert (don't 5xx — Cloud Scheduler retries are not useful for config errors).
- Dispatch summary always returned, even if zero work.

## Architecture

### Sequence Diagrams

**Dispatch (every 5min):**
```
Cloud Scheduler ──HTTP POST + X-Scheduler-Secret──▶ /api/v1/auto-social/cron/dispatch
                                                            │
                                            verify secret ──┤
                                                            │
                                              service.dispatch_pending(batch_limit=10)
                                                            │
                                                  (Firestore + Buffer GraphQL)
                                                            │
                                                ◀── DispatchSummary JSON
```

**Reconcile (every 10min):**
```
Cloud Scheduler ──HTTP POST + X-Scheduler-Secret──▶ /api/v1/auto-social/cron/reconcile
                                                            │
                                            verify secret ──┤
                                                            │
                                              service.reconcile_active(batch_limit=50)
                                                            │
                                                  (Firestore reads + Buffer GraphQL gets)
                                                            │
                                                ◀── ReconcileSummary JSON
```

## Related Code Files

### Modify

- `C:\Users\Admin\hapura-command\backend\api\routes\auto_social.py` — append two `/cron/*` routes (no separate file; same router).
- `C:\Users\Admin\hapura-command\.github\workflows\deploy.yml` — append two `upsert_job` lines + add a marker comment block.

### Create

- None (no new files).

### Delete

- None.

## Implementation Steps

1. **Append cron routes to `auto_social.py`**:

   ```python
   # ── Cron (Cloud Scheduler) ──────────────────────────────────────
   def _verify_scheduler(secret: str | None):
       s = get_settings()
       if secret != s.scheduler_secret:
           raise HTTPException(status_code=401, detail="Invalid scheduler secret")

   @router.post("/cron/dispatch")
   async def cron_dispatch(x_scheduler_secret: str = Header(None)):
       _verify_scheduler(x_scheduler_secret)
       try:
           summary = service.dispatch_pending(batch_limit=10)
           return summary.model_dump()
       except Exception as e:
           # Never 5xx Cloud Scheduler — log + alert + return 200
           import logging
           logging.getLogger(__name__).exception("dispatch failed")
           return {"errors": [str(e)[:300]]}

   @router.post("/cron/reconcile")
   async def cron_reconcile(x_scheduler_secret: str = Header(None)):
       _verify_scheduler(x_scheduler_secret)
       try:
           summary = service.reconcile_active(batch_limit=50)
           return summary.model_dump()
       except Exception as e:
           import logging
           logging.getLogger(__name__).exception("reconcile failed")
           return {"errors": [str(e)[:300]]}
   ```

2. **Append jobs in `.github/workflows/deploy.yml`** within the existing `setup-scheduler` shell block (after the existing `hapura-cost-optimizer` line):

   ```yaml
   # Auto-social
   upsert_job "auto-social-dispatch"   "*/5 * * * *"  "${BACKEND}/api/v1/auto-social/cron/dispatch"
   upsert_job "auto-social-reconcile"  "*/10 * * * *" "${BACKEND}/api/v1/auto-social/cron/reconcile"
   ```

3. **Add Cloud Run env var** `BUFFER_API_KEY` in the `Build env vars file` step:
   - Append `BUFFER_API_KEY: "${BUFFER_API_KEY}"` to the `cat > /tmp/env.yaml` HEREDOC.
   - Append `AUTO_SOCIAL_ADMIN_UIDS: "${AUTO_SOCIAL_ADMIN_UIDS}"`.
   - Append `AUTO_SOCIAL_DEFAULT_CHANNEL_ID: "69f5bb6f5c4c051afa015f6d"`.
   - Append `GCS_ASSETS_BUCKET: "hapura-hq-tiktok-assets"`.
   - Add corresponding secret references in the `env:` block of `Build env vars file` step:
     ```yaml
     BUFFER_API_KEY:           ${{ secrets.BUFFER_API_KEY }}
     AUTO_SOCIAL_ADMIN_UIDS:   ${{ secrets.AUTO_SOCIAL_ADMIN_UIDS }}
     ```
   - GitHub repo secrets to add (manual step, documented phase 08):
     - `BUFFER_API_KEY` — from existing 1-year token
     - `AUTO_SOCIAL_ADMIN_UIDS` — Victor's Firebase uid (single value v1)

4. **Compile-test**:
   - `cd backend && python -c "import main; routes = [r.path for r in main.app.routes]; print([p for p in routes if 'auto-social' in p])"`
   - Expected list includes `/api/v1/auto-social/cron/dispatch` and `/api/v1/auto-social/cron/reconcile`.

5. **Local cron smoke**:
   - `curl -X POST -H "X-Scheduler-Secret: $SCHEDULER_SECRET" http://localhost:8099/api/v1/auto-social/cron/dispatch`
   - With zero pending posts → `{"checked":0,"dispatched":0,"failed":0}`.
   - `curl -X POST -H "X-Scheduler-Secret: $SCHEDULER_SECRET" http://localhost:8099/api/v1/auto-social/cron/reconcile`
   - With zero active → `{"checked":0,"updated":0,"posted":0,"failed":0}`.
   - Verify 401 without header.

6. **Verify Cloud Scheduler creation** (post-deploy, phase 08):
   - `gcloud scheduler jobs list --location=asia-southeast1 --project=hapura-hq | grep auto-social`
   - Expected: 2 jobs.

## Todo List

- [ ] Append `_verify_scheduler` + 2 cron routes to `auto_social.py`
- [ ] Append 2 `upsert_job` lines in `deploy.yml`
- [ ] Add 4 env vars to Cloud Run env build step
- [ ] Add 2 GitHub secrets references (`BUFFER_API_KEY`, `AUTO_SOCIAL_ADMIN_UIDS`)
- [ ] Compile check
- [ ] Local cron smoke (zero work + auth check)
- [ ] Document GitHub secrets to set in phase 08

## Success Criteria

- Cron routes return correct schemas with valid secret.
- 401 returned with bad/missing secret.
- Telemetry: subsequent Cloud Scheduler runs visible in Google Cloud Console logs.
- Buffer call failures logged but never 5xx the cron endpoint.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Buffer 429 rate limit during high-volume reconcile | Low (v1 small batch) | Medium | `BufferRateLimitError` caught per item; errored count returned; next cron cycle retries |
| Cloud Run cold start adds 5s+ to dispatch latency | Medium | Low | 5min cadence absorbs cold-start cost; min-instances stays 0 (cost) |
| Missed dispatch if backend down at the cron tick | Medium | Low | Pending posts remain pending; next tick picks them up |
| Concurrent dispatch + reconcile racing same row (edge case where dispatch puts row in `uploading` but Buffer queue reflects in reconcile before dispatch finishes) | Low | Low | Reconcile only reads `buffer_post_id != null`; uploading rows have it set only after Buffer success → no race |
| Scheduler job not deleted when feature removed | Low | Low | Document deletion command in phase 08 docs |

## Security Considerations

- `SCHEDULER_SECRET` must be set; both endpoints reject without it.
- Endpoints not exposed to anonymous users — header required.
- BufferClient errors are logged with truncated message — never log API key.

## Next Steps

- Phase 04 begins frontend.
- Phase 08 actually creates the Cloud Scheduler jobs (via CI deploy).
- Open question: do we want a `/cron/health` endpoint? Decision: not needed v1 — `/health` already exists and is allow-listed.
