# Phase 07 — GCS Bucket Provisioning + End-to-End Test

## Context Links

- Cloud project: `hapura-hq` (NOT `trendkr-hapura`)
- Region: `asia-southeast1`
- Existing public-bucket reference (similar pattern in other projects): `C:\Users\Admin\douyin-vi-dubber\` (deployed)
- Buffer fetchability requirement: documented in Phase A test (2026-05-02) — Buffer HEADs the URL before accepting

## Overview

- **Priority:** P2 (blocks e2e but doesn't block code merge)
- **Status:** pending
- **Description:** Provision GCS bucket `hapura-hq-tiktok-assets` with public read + 30-day lifecycle. Run end-to-end test of the full schedule → publish → reconcile loop.

## Key Insights

- v1 paste-URL flow doesn't strictly require this bucket (Victor can host elsewhere e.g. `test-videos.co.uk`). But: real workflow needs Hapura-controlled hosting — this bucket is the path.
- Public read = `allUsers:objectViewer`. No object listing. Buckets serve via `https://storage.googleapis.com/hapura-hq-tiktok-assets/{object}` — public URL.
- 30-day TTL via lifecycle rule `Delete` after age 30 — keeps storage cheap.
- Uniform bucket-level access (UBLA) ON — simpler than ACL.
- For v2 upload UI, will need signed-upload-url endpoint. Out of v1 scope — bucket structure ready when needed.
- Must add IAM binding for the Cloud Run service account so backend can later upload (deferred). For v1, bucket is provisioned but unused by code; only Victor manually uploads via `gsutil cp` or Cloud Console.

## Requirements

### Functional

- F07-1 Bucket `hapura-hq-tiktok-assets` exists in `asia-southeast1`, `hapura-hq` project.
- F07-2 UBLA enabled.
- F07-3 IAM: `allUsers` → `roles/storage.objectViewer` (public read).
- F07-4 Lifecycle rule: delete object after 30 days.
- F07-5 CORS configured to allow `https://hq.hapura.vn` GETs (so frontend can fetch metadata if needed).
- F07-6 Smoke: upload a sample 5MB MP4 → publicly accessible via HTTPS URL → Buffer accepts URL in createPost.

### Non-Functional

- Provisioning idempotent (re-running gcloud commands no-ops).
- Storage class STANDARD (region-local, lowest egress).
- Documented in `backend/auto_social/README.md` (small inline doc, ≤30 lines).

## Architecture

### Storage Layout

```
gs://hapura-hq-tiktok-assets/
├── 2026-05/                   # YYYY-MM partitioning
│   ├── post-{id}-video.mp4
│   └── post-{id}-thumb.jpg
└── README.txt                 # internal note: 30-day TTL, public read
```

Naming convention enforced by future backend uploader (phase 09+); v1 manual.

### Public URL Pattern

```
https://storage.googleapis.com/hapura-hq-tiktok-assets/2026-05/post-abc-video.mp4
```

## Related Code Files

### Create

- `C:\Users\Admin\hapura-command\backend\auto_social\README.md` — short note on bucket usage and naming.
- `C:\Users\Admin\hapura-command\backend\auto_social\gcs_lifecycle.json` — lifecycle config snippet for re-run (committed).
- `C:\Users\Admin\hapura-command\backend\auto_social\gcs_cors.json` — CORS config snippet.

### Modify

- None (no code yet; bucket is data layer).

### Delete

- None.

## Implementation Steps

1. **Authenticate gcloud as project owner**:
   - `gcloud auth login`
   - `gcloud config set project hapura-hq`

2. **Create bucket**:
   ```bash
   gcloud storage buckets create gs://hapura-hq-tiktok-assets \
     --project=hapura-hq \
     --location=asia-southeast1 \
     --uniform-bucket-level-access \
     --default-storage-class=STANDARD
   ```

3. **Grant public read**:
   ```bash
   gcloud storage buckets add-iam-policy-binding gs://hapura-hq-tiktok-assets \
     --member=allUsers \
     --role=roles/storage.objectViewer
   ```

4. **Apply lifecycle rule**: write `backend/auto_social/gcs_lifecycle.json`:
   ```json
   {
     "rule": [
       {
         "action": { "type": "Delete" },
         "condition": { "age": 30 }
       }
     ]
   }
   ```
   ```bash
   gcloud storage buckets update gs://hapura-hq-tiktok-assets \
     --lifecycle-file=backend/auto_social/gcs_lifecycle.json
   ```

5. **Apply CORS**: write `backend/auto_social/gcs_cors.json`:
   ```json
   [
     {
       "origin": ["https://hq.hapura.vn", "https://hapura-hq.web.app", "http://localhost:5199"],
       "method": ["GET", "HEAD"],
       "responseHeader": ["Content-Type", "Range"],
       "maxAgeSeconds": 3600
     }
   ]
   ```
   ```bash
   gcloud storage buckets update gs://hapura-hq-tiktok-assets \
     --cors-file=backend/auto_social/gcs_cors.json
   ```

6. **Grant Cloud Run SA write access** (future use; harmless to set now):
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe hapura-hq --format='value(projectNumber)')
   gcloud storage buckets add-iam-policy-binding gs://hapura-hq-tiktok-assets \
     --member=serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
     --role=roles/storage.objectAdmin
   ```

7. **Manual upload smoke**:
   ```bash
   curl -sLO https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4
   gcloud storage cp Big_Buck_Bunny_360_10s_1MB.mp4 gs://hapura-hq-tiktok-assets/2026-05/test-video.mp4
   curl -I https://storage.googleapis.com/hapura-hq-tiktok-assets/2026-05/test-video.mp4
   # Expect 200 OK, Content-Type: video/mp4
   ```

8. **End-to-End test scenario** (run AFTER phases 01–06 deployed locally + bucket from steps 1–7 ready):

   a. **Sync channels**: in UI click "Sync from Buffer" on Channels tab. Verify `xuantuanh8` row appears.

   b. **Schedule a post**: in UI click `+ Schedule Post`. Fill:
      - Account: xuantuanh8 (TikTok)
      - Video URL: `https://storage.googleapis.com/hapura-hq-tiktok-assets/2026-05/test-video.mp4` (from step 7)
      - Caption: `Hapura auto-social e2e test`
      - Hashtags: `#hapura, #test`
      - Schedule time: now + 8 minutes (ensures dispatch picks up at next 5min tick)
      - Submit.

   c. **Verify Firestore**: in Console → Firestore → `auto_social_posts` collection → new doc with `status: pending`.

   d. **Wait for dispatch tick** (Cloud Scheduler `auto-social-dispatch` every 5min OR manually `curl -X POST -H "X-Scheduler-Secret: $SCHEDULER_SECRET" .../cron/dispatch`):
      - Doc transitions `pending → uploading → queued`
      - `buffer_post_id` populated.

   e. **Wait for reconcile tick** (every 10min OR manual):
      - Buffer `getPost` returns status `sent` once TikTok picks up the post.
      - Doc transitions `queued → posted`.
      - `posted_url` set to `externalLink` (TikTok URL).

   f. **UI assertions**:
      - List tab shows row with green "posted" badge and clickable TikTok URL.
      - Stats card "Posted (7d)" increments to 1.
      - Calendar shows green chip on the scheduled day.

   g. **Telegram alert path test**: schedule a 2nd post with intentionally invalid URL `https://example.com/missing.mp4`:
      - After dispatch tick, status → `failed`.
      - Telegram bot (Victor's chat) receives `🚨 *AUTO-SOCIAL FAIL*…` message.

9. **Document the E2E run** in `plans/260502-1805-auto-social-module/reports/e2e-2026-MM-DD.md` (created during execution, not now). Include screenshots of: stats card, list row, Buffer queue, Firestore doc, TikTok video, Telegram alert.

## Todo List

- [ ] gcloud auth + project set
- [ ] Create bucket `hapura-hq-tiktok-assets`
- [ ] Public read IAM binding
- [ ] Lifecycle rule (commit gcs_lifecycle.json)
- [ ] CORS rule (commit gcs_cors.json)
- [ ] Cloud Run SA storage.objectAdmin
- [ ] Upload smoke (curl 200 OK)
- [ ] E2E happy path: schedule → dispatch → reconcile → posted
- [ ] E2E failure path: invalid URL → failed → Telegram alert
- [ ] Save e2e report in `plans/260502-1805-auto-social-module/reports/`
- [ ] Write `backend/auto_social/README.md`

## Success Criteria

- Bucket reachable at `https://storage.googleapis.com/hapura-hq-tiktok-assets/...` with 30-day TTL.
- E2E happy path completes within 20 minutes of submit.
- Failure path triggers Telegram alert.
- Both paths leave Firestore in correct terminal state.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Public bucket accidentally serves PII | Low | High | Caption/PII never written to bucket; only video+thumbnail. Access logs sampled in Cloud Logging |
| 30-day TTL deletes still-published video → TikTok shows broken thumbnail link | High | Medium | TikTok caches uploaded video natively; `posted_url` is TikTok's, not GCS. GCS only used as upload-source. After post `sent`, bucket asset can expire. |
| Buffer rejects URL despite public read (e.g. due to redirect) | Low | High | URL must be HEAD-able; smoke step 7 verifies. If fails, fallback to test-videos.co.uk for e2e |
| Cloud Run SA missing storage permission breaks future uploader | Low | Low | Step 6 grants now; defensive |
| GCS quota exceeded by accident | Low | Low | Default quotas are generous; lifecycle keeps storage low |

## Security Considerations

- Bucket is public — assume anything uploaded is public-readable. Never store credentials or untrusted user content.
- CORS limited to known origins; prevents browser-side abuse.
- Lifecycle ensures stale assets purged.
- IAM grants reviewed: only `allUsers` reader + Cloud Run SA writer.

## Next Steps

- Phase 08: production deploy + scheduler setup + docs.
- Future v2: signed-upload-url endpoint backend-side, Drag-Drop upload in modal.
- Open question: should we add Cloud Logging alert if bucket egress > 100GB/day? Decision: defer — v1 traffic small.
