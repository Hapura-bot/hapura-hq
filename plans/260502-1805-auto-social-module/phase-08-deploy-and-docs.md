# Phase 08 — Production Deploy + Telegram Wiring + Docs

## Context Links

- CI workflow: `C:\Users\Admin\hapura-command\.github\workflows\deploy.yml`
- Existing CLAUDE.md: `C:\Users\Admin\hapura-command\CLAUDE.md`
- Existing dev-roadmap (if present): `C:\Users\Admin\hapura-command\docs\development-roadmap.md`
- Old auto-social CLAUDE: `C:\Users\Admin\auto-social\CLAUDE.md`

## Overview

- **Priority:** P1 (closes the feature)
- **Status:** pending
- **Description:** Deploy backend + frontend to production via existing CI. Verify Cloud Scheduler jobs auto-create. Set GitHub secrets. Smoke prod URLs. Update docs and deprecate the old standalone service.

## Key Insights

- CI is push-to-main triggered. Add the BUFFER_API_KEY etc. secrets BEFORE pushing the code that needs them — otherwise deploy works but cron endpoints fail at runtime.
- Maintenance middleware allow-list extension MUST be in this push (covered in phase 02). Verify with curl post-deploy.
- Existing `setup-scheduler` job idempotently re-creates jobs each run — adding 2 lines is sufficient.
- Old `auto-social` standalone service in `C:\Users\Admin\auto-social\` is local-only (not deployed). Deprecation is a doc-update + freeze — no infra to tear down.

## Requirements

### Functional

- F08-1 GitHub repo secrets `BUFFER_API_KEY` and `AUTO_SOCIAL_ADMIN_UIDS` set.
- F08-2 `git push origin main` triggers CI.
- F08-3 Backend deployed to Cloud Run with new env vars.
- F08-4 Frontend deployed to Firebase Hosting; `/auto-social` reachable at `https://hq.hapura.vn/auto-social`.
- F08-5 Cloud Scheduler shows 2 new jobs (`auto-social-dispatch` 5min, `auto-social-reconcile` 10min).
- F08-6 Smoke curl `/api/v1/auto-social/stats` with valid token → 200.
- F08-7 Telegram alert verified (one fake-failed post triggers).
- F08-8 `CLAUDE.md` (hapura-command) updated with auto-social section.
- F08-9 `auto-social/CLAUDE.md` (old service) gets a deprecation banner pointing to hq.hapura.vn module.

### Non-Functional

- Zero-downtime deploy (Cloud Run rolling update).
- Rollback path: previous Cloud Run revision still callable via `gcloud run services update-traffic`.
- Total downtime budget: 0 (existing routes unaffected).

## Architecture

### Deploy Flow

```
git push main
  └─▶ GitHub Actions deploy.yml
        ├── deploy-backend  ──▶ Cloud Run (new env vars baked)
        ├── deploy-frontend ──▶ Firebase Hosting (build with VITE_API_URL)
        └── setup-scheduler ──▶ gcloud scheduler upsert (incl. 2 new jobs)
```

### Secret Distribution

```
GitHub Repo Secrets
├── BUFFER_API_KEY            (NEW) ──▶ Cloud Run env BUFFER_API_KEY
├── AUTO_SOCIAL_ADMIN_UIDS    (NEW) ──▶ Cloud Run env AUTO_SOCIAL_ADMIN_UIDS
├── SCHEDULER_SECRET          (existing, reused)
├── WEBHOOK_SECRET            (existing, reused)
├── TELEGRAM_BOT_TOKEN        (existing, reused)
├── TELEGRAM_CHAT_ID          (existing, reused)
└── FIREBASE_SERVICE_ACCOUNT_HAPURA_HQ (existing)
```

## Related Code Files

### Modify

- `C:\Users\Admin\hapura-command\CLAUDE.md` — append auto-social section (~25 lines).
- `C:\Users\Admin\auto-social\CLAUDE.md` — prepend deprecation banner (~10 lines).
- `C:\Users\Admin\hapura-command\docs\development-roadmap.md` if exists; create if not.
- `C:\Users\Admin\hapura-command\docs\project-changelog.md` if exists; create if not.

### Create

- `C:\Users\Admin\hapura-command\plans\260502-1805-auto-social-module\reports\deploy-2026-MM-DD.md` — generated during execution.

### Delete

- None (old auto-social Python code preserved as reference).

## Implementation Steps

1. **Add GitHub repo secrets** (manual via repo Settings → Secrets and variables → Actions):
   - `BUFFER_API_KEY` — paste personal key from auto-social `.env`.
   - `AUTO_SOCIAL_ADMIN_UIDS` — Victor's Firebase uid (lookup via Firebase Console → Authentication → Users; copy UID).

2. **Verify CI workflow file accepts new secrets** (already done in phase 03 step 3 — recheck `deploy.yml` line edits).

3. **Pre-flight local checks**:
   - `cd backend && rtk pytest` — ports/units green (any new tests added phase 01–03).
   - `cd frontend && rtk npm run build` — build green.
   - `git diff --stat` → expected: ~10 backend files, ~10 frontend files, 1 workflow change.

4. **Commit + push**:
   - `git add backend/auto_social backend/api backend/main.py backend/config.py backend/.env.example frontend/src .github/workflows/deploy.yml`
   - `git commit -m "feat(auto-social): TikTok scheduler module with Buffer + Cloud Scheduler"` (no AI footer per repo convention)
   - `git push origin main`

5. **Watch CI**:
   - `gh run watch` — wait green.
   - On red: read logs → fix → recommit. Common pitfalls:
     - `BUFFER_API_KEY` secret missing → `Build env vars file` step shows empty → app starts but Buffer calls error 401. Fix: add secret.
     - Missing import in `main.py` → backend deploy fails compile in container. Fix locally + repush.
     - `setup-scheduler` step times out: gcloud auth issue. Re-trigger workflow.

6. **Post-deploy smoke**:
   - Get backend URL: `gcloud run services describe hapura-command-backend --region=asia-southeast1 --project=hapura-hq --format='value(status.url)'`
   - Curl health: `curl <url>/health` → `{"status":"ok",...}`.
   - Curl maintenance allow-list verification: `curl -i <url>/api/v1/auto-social/stats` — expect 401 (auth required), NOT 503 (maintenance). 401 ⇒ middleware allow-list works.
   - With Firebase token via UI: visit `https://hq.hapura.vn/auto-social` → see Stats tab numbers.

7. **Verify Cloud Scheduler**:
   ```bash
   gcloud scheduler jobs list --location=asia-southeast1 --project=hapura-hq | grep auto-social
   ```
   - Expect: `auto-social-dispatch  ENABLED  */5 * * * *` and `auto-social-reconcile  ENABLED  */10 * * * *`.
   - Manually run once: `gcloud scheduler jobs run auto-social-dispatch --location=asia-southeast1 --project=hapura-hq`. Check Cloud Run logs for `[dispatch]` entries.

8. **Telegram alert e2e** (defer to phase 07 step 8g if not yet done): create a deliberately-failing post, wait one cron cycle, verify Telegram message lands.

9. **Update CLAUDE.md** (`C:\Users\Admin\hapura-command\CLAUDE.md`):
   - Append to "Features (all deployed)" section:
     ```
     - **Auto-Social** (`/auto-social`) — schedule TikTok posts via Buffer GraphQL. Cloud Scheduler dispatches every 5min, reconciles every 10min. Admin-only (uid whitelist via `AUTO_SOCIAL_ADMIN_UIDS`).
     ```
   - Append to "Key env vars (Cloud Run)":
     ```
     - `BUFFER_API_KEY` — Buffer Personal API key (1y expiry; renew yearly)
     - `AUTO_SOCIAL_ADMIN_UIDS` — comma-separated Firebase uids allowed to use auto-social
     - `GCS_ASSETS_BUCKET` — `hapura-hq-tiktok-assets`
     ```
   - Append to "Gotchas":
     ```
     - Auto-social: maintenance middleware allow-list MUST include `/api/v1/auto-social` else 503 in prod
     - Buffer free-plan rate limit: 100/15min, 500/24h — reconcile capped at 50 docs/run
     - Buffer URL fetchability: video URL must be public + HEAD-able; bucket `hapura-hq-tiktok-assets` is the supported origin
     - Cloud Scheduler jobs `auto-social-dispatch` (5min) + `auto-social-reconcile` (10min) — list via `gcloud scheduler jobs list`
     ```

10. **Update old `auto-social/CLAUDE.md`** — prepend banner:
    ```markdown
    > **DEPRECATED (2026-05-02):** This standalone service is replaced by the **Auto-Social module** inside `hapura-command` at https://hq.hapura.vn/auto-social. The Python code under `src/auto_social/` is preserved as reference for the BufferClient port — do not run this service in parallel with the live module. Future Buffer integration changes go in `C:\Users\Admin\hapura-command\backend\auto_social\`.
    ```

11. **Touch dev-roadmap + changelog** (create if missing):
    - `docs/development-roadmap.md` — add row "Auto-Social module — Status: Deployed — 2026-05-XX".
    - `docs/project-changelog.md` — add entry under v1.x "feat(auto-social): TikTok scheduler module — Buffer + Cloud Scheduler + Firestore".

12. **Save deploy report** in `plans/260502-1805-auto-social-module/reports/deploy-2026-MM-DD.md` with timestamps, smoke results, scheduler job list, e2e screenshot links.

## Todo List

- [ ] Add `BUFFER_API_KEY` GitHub secret
- [ ] Add `AUTO_SOCIAL_ADMIN_UIDS` GitHub secret (Victor's uid)
- [ ] Local pre-flight: pytest + npm build green
- [ ] Commit + push to main
- [ ] Watch CI green
- [ ] Curl `/health` and `/api/v1/auto-social/stats` (401 expected)
- [ ] Visit https://hq.hapura.vn/auto-social, verify all 4 tabs
- [ ] Verify 2 Cloud Scheduler jobs exist + manually run dispatch
- [ ] Telegram alert e2e fired (1 failed post)
- [ ] Update `hapura-command/CLAUDE.md`
- [ ] Update `auto-social/CLAUDE.md` with deprecation banner
- [ ] Update/create dev-roadmap + changelog
- [ ] Save deploy report

## Success Criteria

- Production URL `/auto-social` works end-to-end with Victor's Firebase login.
- 2 Cloud Scheduler jobs visible + green.
- Stats tab shows live counts from Firestore.
- Telegram alert proven via fake-fail post.
- Old auto-social/CLAUDE.md banner prevents accidental parallel runs.
- New auto-social section in hapura-command CLAUDE.md visible.
- No 503 from `/api/v1/auto-social/*` endpoints.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Push to main breaks existing routes | Low | High | Maintenance middleware extension only adds; doesn't remove. Other route imports unchanged. CI build catches type errors. |
| Cloud Scheduler permission missing for setup-scheduler step | Low | Medium | Existing CI proves permission works for other jobs |
| Forgot to set BUFFER_API_KEY secret → cron endpoints log warns silently | Medium | Medium | Step 1 explicit; smoke step 8 catches |
| GitHub secret typo in env build step var name | Low | Medium | Visual diff in PR; lint via re-running deploy-backend |
| Maintenance middleware NOT extended → 503 in prod | Low (covered in phase 02) | Critical | Smoke step 6 explicitly tests this |
| Old auto-social Python service still running on Victor's PC | Medium | Medium | Deprecation banner; if dual-running, both write to different stores (Sheet vs Firestore), no DB conflict |

### Rollback Plan

- Backend: `gcloud run services update-traffic hapura-command-backend --to-revisions=PREV_REVISION=100 --region=asia-southeast1 --project=hapura-hq` (1-line revert)
- Frontend: previous build cached at Firebase Hosting; `firebase hosting:rollback`
- Cloud Scheduler jobs: `gcloud scheduler jobs delete auto-social-dispatch auto-social-reconcile --location=asia-southeast1 --project=hapura-hq` (idempotent)
- Firestore data: not deleted on rollback; safe to keep
- Maintenance middleware allow-list reversion is a code edit + redeploy (1 commit)

## Security Considerations

- Verify after deploy that no API keys appear in browser network tab (ID token only).
- Confirm `/api/v1/auto-social/cron/*` rejects without secret header (curl test).
- Bucket public read confirmed; manual content reviewed.
- Telegram alert text doesn't include API keys or Firebase tokens.
- Document yearly rotation of `BUFFER_API_KEY`.

## Next Steps

- Future: integrate signed-upload-url + drag-drop UI (phase 09+).
- Future: multi-channel support (IG, FB) — Buffer client ready, just UI work.
- Future: scheduled-content templates and recurring posts.
- Open question: should we add an audit log of every CRUD action in a separate Firestore subcollection? Decision: defer — `created_by` + `updated_at` enough for v1; revisit if compliance asked.
