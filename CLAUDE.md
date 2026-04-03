# Hapura Command Center — CLAUDE.md

## Tổng quan
Central management dashboard cho 4 Hapura products. Revenue War Room: mỗi project là 1 phòng cạnh tranh doanh thu. AI agents (Phase 3) tự động giám sát và đề xuất chiến lược.

## Ports (FIXED)
| Role | Port |
|------|------|
| backend | **8099** |
| frontend | **5199** |
| openclaw | **18789** (GCE VM, Phase 3) |

## Chạy development
```bash
# Backend
cd backend && pip install -r requirements.txt
cp .env.example .env   # điền serviceAccountKey.json
uvicorn main:app --port 8099 --reload

# Frontend
cd frontend && npm install
cp .env.example .env   # điền Firebase config
npm run dev   # → http://localhost:5199
```

## Stack
- Backend: FastAPI + Firebase Admin + Firestore
- Frontend: React 19 + Vite + Tailwind + Framer Motion + TanStack Query
- DB: Firestore (collections: command_projects, command_metrics, command_tasks, command_agent_runs)
- AI: PraisonAI agents (Phase 3)
- Messaging: OpenClaw on GCE e2-micro (Phase 3)

## Firestore reuse
Dùng cùng Firebase project với Trendkr (`trendkr-hapura`), namespace `command_*`.
Copy serviceAccountKey.json từ trendkr/backend.

## Project phases
- Phase 1 (done): Core dashboard, manual metrics, kanban
- Phase 2: GitHub API + Cloud Run health integration
- Phase 3: PraisonAI agents + OpenClaw GCE + Telegram alerts
- Phase 4: Revenue war gamification, deploy Firebase Hosting

## Skill Auto-Trigger Rules
- scaffold-fastapi-cloudrun: khi deploy backend lên Cloud Run
- setup-github-cicd: khi setup CI/CD
- debug-backend-logs: khi debug FastAPI errors
