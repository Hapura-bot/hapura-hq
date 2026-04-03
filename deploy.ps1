# Deploy Hapura Command Center to Cloud Run + Firebase Hosting
param(
  [string]$ProjectId      = "trendkr-hapura",
  [string]$Region         = "asia-southeast1",
  [string]$BackendService = "hapura-command-backend",
  [switch]$SetupScheduler
)

$ErrorActionPreference = "Stop"
Write-Host "=== Hapura Command Center Deploy ===" -ForegroundColor Cyan

# ── 1. Deploy backend to Cloud Run ────────────────────────────────────────────
Write-Host "`n[1/3] Deploying backend to Cloud Run..." -ForegroundColor Yellow
Push-Location backend
gcloud run deploy $BackendService `
  --source . `
  --region $Region `
  --project $ProjectId `
  --allow-unauthenticated `
  --port 8099 `
  --memory 512Mi `
  --set-env-vars "APP_ENV=production,GCP_PROJECT_ID=$ProjectId,GCP_REGION=$Region"
Pop-Location

$BackendUrl = (gcloud run services describe $BackendService `
  --region $Region --project $ProjectId `
  --format "value(status.url)").Trim()
Write-Host "Backend: $BackendUrl" -ForegroundColor Green

# ── 2. Build frontend with production API URL ──────────────────────────────────
Write-Host "`n[2/3] Building frontend..." -ForegroundColor Yellow
Push-Location frontend
"VITE_API_URL=$BackendUrl/api/v1" | Out-File -FilePath .env.production -Encoding utf8 -NoNewline
npm run build
Pop-Location

# ── 3. Deploy frontend to Firebase Hosting ────────────────────────────────────
Write-Host "`n[3/3] Deploying frontend to Firebase Hosting..." -ForegroundColor Yellow
firebase deploy --only hosting --project $ProjectId

Write-Host "`n=== Deploy complete ===" -ForegroundColor Green
Write-Host "Backend : $BackendUrl" -ForegroundColor Cyan
Write-Host "Frontend: https://$ProjectId.web.app" -ForegroundColor Cyan

# ── 4. Optional: Setup Cloud Scheduler ────────────────────────────────────────
if ($SetupScheduler) {
  $ApiBase = "$BackendUrl/api/v1"
  $Secret  = Read-Host "Enter WEBHOOK_SECRET (from backend .env)"
  Write-Host "`nCreating Cloud Scheduler jobs..." -ForegroundColor Yellow

  # Health checker — daily 08:00 VN = 01:00 UTC
  gcloud scheduler jobs create http hapura-health-checker `
    --location=$Region --project=$ProjectId `
    --schedule="0 1 * * *" `
    --uri="$ApiBase/agents/schedule/health_checker" `
    --message-body="{}" `
    --headers="Content-Type=application/json,X-Scheduler-Secret=$Secret" `
    --http-method=POST

  # Strategist — Monday 09:00 VN = 02:00 UTC
  gcloud scheduler jobs create http hapura-strategist `
    --location=$Region --project=$ProjectId `
    --schedule="0 2 * * 1" `
    --uri="$ApiBase/agents/schedule/strategist" `
    --message-body="{}" `
    --headers="Content-Type=application/json,X-Scheduler-Secret=$Secret" `
    --http-method=POST

  # Revenue forecaster — 1st of month 09:00 VN = 02:00 UTC
  gcloud scheduler jobs create http hapura-revenue-forecaster `
    --location=$Region --project=$ProjectId `
    --schedule="0 2 1 * *" `
    --uri="$ApiBase/agents/schedule/revenue_forecaster" `
    --message-body="{}" `
    --headers="Content-Type=application/json,X-Scheduler-Secret=$Secret" `
    --http-method=POST

  Write-Host "Cloud Scheduler jobs created!" -ForegroundColor Green
} else {
  Write-Host "`nTo setup Cloud Scheduler: ./deploy.ps1 -SetupScheduler" -ForegroundColor DarkGray
}
