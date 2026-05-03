# Hapura Command Center — CLAUDE.md

## Tổng quan
Central management dashboard cho 4 Hapura products. Revenue War Room: gamification doanh thu, AI agents tự động, ARIA chatbot, Telegram alerts.

**GitHub:** `https://github.com/Hapura-bot/hapura-hq`
**Live URL:** https://hq.hapura.vn
**Firebase project:** `hapura-hq` (INDEPENDENT — NOT trendkr-hapura)

## Ports (FIXED)
| Role | Port |
|------|------|
| backend | **8099** |
| frontend | **5199** |

## Chạy development
```bash
# Backend
cd backend && pip install -r requirements.txt
cp .env.example .env   # điền serviceAccountKey.json + OPENAI_API_KEY + TELEGRAM_*
uvicorn main:app --port 8099 --reload

# Frontend
cd frontend && npm install
cp .env.example .env   # điền Firebase config
npm run dev   # → http://localhost:5199
```

## Stack
- Backend: FastAPI + Firebase Admin + Firestore
- Frontend: React 19 + Vite + Tailwind + Framer Motion + TanStack Query
- DB: Firestore (project `hapura-hq`) — collections: `command_projects`, `command_metrics`, `command_tasks`, `command_agent_runs`, `vertex_configs`, `auto_social_posts`, `auto_social_channels`
- AI: PraisonAI agents + OpenAI-compatible via vertex-key.com (all models: `aws/` prefix)
- ARIA: direct OpenAI client (not PraisonAI), model `aws/claude-sonnet-4-6`, real-time chat
- Messaging: OpenClaw trên Huawei server (Tailscale `100.118.69.22`, port 18789)

## Firestore
Firebase project `hapura-hq` — standalone, KHÔNG dùng chung với trendkr hay project nào khác.
`serviceAccountKey.json` riêng — copy từ `hapura-hq` Firebase Console.

## Features (all deployed)
- 4 Project Room cards: health, GP scores, commit spark bars
- Revenue leaderboard với Framer Motion animations
- DECLARE WINNER button → Telegram announcement
- Sprint Board (Kanban drag & drop)
- 4 AI Agents: Health Checker, Strategist, Bug Detective, Revenue Forecaster
- ARIA chat widget (floating bottom-right) — web + Telegram bidirectional
- Cloud Scheduler (daily/weekly/monthly agent runs)
- Webhooks: revenue + signup events từ product apps
- **Vertex Config Hub** (`/vertex-config`) — quản lý tập trung endpoint/model cho tất cả Hapura projects
- **Outbound Telegram alerts** — `POST /api/v1/webhooks/notify` (auth: `X-Hapura-Secret`)
- **Auto-Social** (`/auto-social`) — TikTok scheduler qua Buffer GraphQL API. Calendar/List/Channels/Stats tabs + Schedule modal. Cloud Scheduler dispatch (5min) + reconcile (10min). Video hosting: `gs://hapura-hq-tiktok-assets` (public, 30d lifecycle). Code ở `backend/auto_social/` + `frontend/src/components/auto-social/`. Plan tại `plans/260502-1805-auto-social-module/`.

## CI/CD
GitHub Actions → push to main → deploy-backend (Cloud Run) → deploy-frontend (Firebase Hosting).
`deploy.ps1` chỉ dùng emergency.

## Key env vars (Cloud Run)
- `OPENAI_API_KEY` — Vertex Key API key (vertex-key.com)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (Victor: `896067602`), `TELEGRAM_WEBHOOK_SECRET`
- `WEBHOOK_SECRET` — cho `/webhooks/notify` + Cloud Scheduler
- `GH_API_TOKEN` — GitHub PAT
- `BUFFER_API_KEY` — Buffer GraphQL personal API key (Secret Manager: `buffer-api-key:latest`)
- `BUFFER_GRAPHQL_URL` — `https://api.buffer.com`
- `AUTO_SOCIAL_DEFAULT_CHANNEL_ID` — Buffer channel id của TikTok @xuantuanh8 (`69f5bb6f5c4c051afa015f6d`)
- `AUTO_SOCIAL_ADMIN_UIDS` — comma-separated Firebase uid (optional, route gated bởi ALLOWED_EMAILS)
- `GCS_ASSETS_BUCKET` — `hapura-hq-tiktok-assets`

## Gotchas
- `deps.py`: dùng `Header(None)` (optional) NOT `Header(...)` (required)
- PraisonAI Agent/Agents: không nhận `verbose` hay `self_reflect` params
- CORS_ORIGINS: phải có cả `hapura-hq.web.app` VÀ `hq.hapura.vn`
- Firebase Hosting → Cloud Run rewrite: `firebase-hosting-deploy@hapura-hq.iam.gserviceaccount.com` cần `roles/run.viewer`
- vertex-key.com model prefix: tất cả dùng `aws/` từ 2026-04-21
- `WEBHOOK_SECRET` hiện là `hapura-secret-change-me` (placeholder) — cần rotate thành secret thật
- Vertex Config Hub: Cloud Run consumers (hapudub, hapu-studio) hiện "offline" khi min-scale=0 và không có traffic — expected behavior, không phải lỗi. Online lại khi có request đầu tiên.
- OpenClaw hub sync (Huawei, Task Scheduler): chạy as SYSTEM → `homedir()` = SYSTEM profile path → hardcode `C:\Users\admin\.openclaw\openclaw.json`. Task ExecutionTimeLimit phải set `PT0S` (unlimited), default Windows task bị kill sau 72h.
- Maintenance middleware tại `main.py:42` block mọi route ngoài `_ALLOWED_PREFIXES` — hiện cho phép `/api/v1/vertex-config`, `/api/v1/auto-social`, `/health`. Khi remove maintenance, edit `_ALLOWED_PREFIXES` hoặc xóa middleware.
- Cloud Scheduler `auto-social-dispatch` (mỗi 5 phút) + `auto-social-reconcile` (mỗi 10 phút) trigger `/api/v1/auto-social/cron/*` với `X-Scheduler-Secret`. Firestore composite index `(status, schedule_time)` REQUIRED cho `auto_social_posts`.
- Buffer rate limit: 100 req/15min, 500/24h, 10k/30d (free tier). Reconcile mỗi 10 phút × N posts non-terminal — scale 50+ acc cần tăng interval lên 30 phút.

## Skill Auto-Trigger Rules
- scaffold-fastapi-cloudrun: khi deploy backend lên Cloud Run
- setup-github-cicd: khi setup CI/CD
- debug-backend-logs: khi debug FastAPI errors

## RTK — Token-Optimized Commands
Luôn dùng prefix `rtk` để giảm token 60-90%:

```bash
# Git
rtk git status / rtk git diff / rtk git log / rtk git add . / rtk git commit / rtk git push

# File exploration
rtk ls / rtk grep <pattern> <path>

# Backend (FastAPI/Python)
rtk pytest / rtk ruff check backend/ / rtk pip install -r requirements.txt

# Frontend (React/Vite)
rtk npm run build / rtk npm run lint / rtk vitest

# Logs & debug
rtk log <file> / rtk err <cmd>
```
