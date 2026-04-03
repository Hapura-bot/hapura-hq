from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore
from api.deps import get_current_user
from models import ProjectRoom, ProjectRoomUpdate, GPScore
from datetime import datetime, date

router = APIRouter(prefix="/projects", tags=["projects"])

# Default project metadata — seeded on first run
DEFAULT_PROJECTS: list[dict] = [
    {
        "id": "clippack",
        "name": "ClipPack",
        "tagline": "Video packaging cho Shopee/TikTok sellers",
        "platform": "android",
        "status": "dev",
        "tech_stack": ["React Native", "Expo", "FastAPI", "Cloud Run", "Google Drive"],
        "cloud_run_service_id": "clippack-backend",
        "github_repo": "Hapura-bot/clippack",
        "frontend_url": "",
        "color_accent": "#ff8d89",
        "port_backend": None,
        "port_frontend": 8082,
        "phase_current": 2,
        "phase_total": 3,
        "phase_label": "Play Store Launch",
    },
    {
        "id": "trendkr",
        "name": "Trendkr",
        "tagline": "Multi-platform trending video search",
        "platform": "web",
        "status": "deployed",
        "tech_stack": ["React", "FastAPI", "Firebase", "Cloud Run", "TikHub"],
        "cloud_run_service_id": "trendkr-backend",
        "github_repo": "Hapura-bot/trendkr",
        "frontend_url": "https://trendkr.hapura.vn",
        "color_accent": "#06b6d4",
        "port_backend": 8083,
        "port_frontend": 5176,
        "phase_current": 4,
        "phase_total": 4,
        "phase_label": "Monetization",
    },
    {
        "id": "hapu-studio",
        "name": "Hapu Studio",
        "tagline": "AI viral content factory cho TikTok VN",
        "platform": "web",
        "status": "dev",
        "tech_stack": ["React", "FastAPI", "Gemini 2.5", "Creatomate", "Cloud Run"],
        "cloud_run_service_id": "hapu-studio-backend",
        "github_repo": "Hapura-bot/great-studio",
        "frontend_url": "",
        "color_accent": "#aa44ff",
        "port_backend": 8002,
        "port_frontend": 5174,
        "phase_current": 3,
        "phase_total": 4,
        "phase_label": "Deploy + Auth",
    },
    {
        "id": "douyin-vi-dubber",
        "name": "Douyin Vi Dubber",
        "tagline": "Auto-dub Douyin/TikTok videos sang tiếng Việt",
        "platform": "web",
        "status": "deployed",
        "tech_stack": ["React", "FastAPI", "Google STT", "Google TTS", "PraisonAI"],
        "cloud_run_service_id": "douyin-vi-dubber-api",
        "github_repo": "Hapura-bot/douyin-vi-dubber",
        "frontend_url": "https://hapudub.hapura.vn",
        "color_accent": "#ffaa00",
        "port_backend": 8001,
        "port_frontend": 5175,
        "phase_current": 3,
        "phase_total": 4,
        "phase_label": "Growth & Scale",
    },
]


def _get_db():
    return firestore.client()


def _seed_projects_if_empty(db):
    """Seed default projects. Merges updated defaults into existing docs."""
    for p in DEFAULT_PROJECTS:
        ref = db.collection("command_projects").document(p["id"])
        if not ref.get().exists:
            ref.set({**p, "created_at": datetime.utcnow().isoformat()})
        else:
            ref.set(p, merge=True)


@router.get("", response_model=list[dict])
async def list_projects(uid: str = Depends(get_current_user)):
    db = _get_db()
    _seed_projects_if_empty(db)
    docs = db.collection("command_projects").stream()
    projects = [doc.to_dict() for doc in docs]
    # Sort by canonical order
    order = {p["id"]: i for i, p in enumerate(DEFAULT_PROJECTS)}
    return sorted(projects, key=lambda p: order.get(p.get("id", ""), 99))


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str, uid: str = Depends(get_current_user)):
    db = _get_db()
    doc = db.collection("command_projects").document(project_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")
    return doc.to_dict()


@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    body: ProjectRoomUpdate,
    uid: str = Depends(get_current_user),
):
    db = _get_db()
    ref = db.collection("command_projects").document(project_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Project not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow().isoformat()
    ref.update(updates)
    return ref.get().to_dict()


def _fmt_vnd(n: int) -> str:
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:     return f"{n/1_000_000:.1f}M"
    if n >= 1_000:         return f"{n/1_000:.0f}k"
    return str(n)


def _load_gp_data(db, period: str):
    """Shared helper: load metrics + integration cache, return (all_metrics, int_cache, maxes)."""
    project_ids = [p["id"] for p in DEFAULT_PROJECTS]
    metrics_docs = db.collection("command_metrics").where("period", "==", period).stream()
    all_metrics = {doc.to_dict()["project_id"]: doc.to_dict() for doc in metrics_docs}
    int_cache = {}
    for pid in project_ids:
        doc = db.collection("command_integrations_cache").document(pid).get()
        if doc.exists:
            int_cache[pid] = doc.to_dict()
    all_revenue = [m.get("revenue_vnd", 0) for m in all_metrics.values()]
    all_users   = [m.get("active_users", 0) for m in all_metrics.values()]
    all_commits = [int_cache.get(pid, {}).get("github_commits_7d", 0) for pid in project_ids]
    maxes = {
        "revenue": max(all_revenue) if all_revenue else 1,
        "users":   max(all_users)   if all_users   else 1,
        "commits": max(all_commits) if any(c > 0 for c in all_commits) else 1,
    }
    return project_ids, all_metrics, int_cache, maxes


def _compute_gp_for(pid, all_metrics, int_cache, maxes) -> int:
    m  = all_metrics.get(pid, {})
    ic = int_cache.get(pid, {})
    up = {"healthy": 200, "degraded": 100, "timeout": 50, "offline": 0, "unknown": 150}.get(
        ic.get("cloudrun_status", "unknown"), 150)
    return (int((m.get("revenue_vnd", 0)       / maxes["revenue"]) * 400)
          + int((m.get("active_users", 0)       / maxes["users"])   * 200)
          + int((ic.get("github_commits_7d", 0) / maxes["commits"]) * 200)
          + up)


@router.post("/winner/declare", response_model=dict)
async def declare_winner(uid: str = Depends(get_current_user)):
    """Compute FOCUS project, send Telegram announcement."""
    from config import get_settings
    settings = get_settings()
    db = _get_db()
    period = date.today().strftime("%Y-%m")
    project_ids, all_metrics, int_cache, maxes = _load_gp_data(db, period)

    all_gp = {pid: _compute_gp_for(pid, all_metrics, int_cache, maxes) for pid in project_ids}
    winner_id   = max(all_gp, key=all_gp.get)
    winner_meta = next(p for p in DEFAULT_PROJECTS if p["id"] == winner_id)
    winner_gp   = all_gp[winner_id]
    winner_rev  = all_metrics.get(winner_id, {}).get("revenue_vnd", 0)
    multiplier  = round(1.0 + winner_gp / 500, 2)

    telegram_sent = False
    if settings.telegram_bot_token and settings.telegram_chat_id:
        from agents.telegram import send_telegram_sync
        text = (
            f"🏆 *HAPURA REVENUE WAR — WINNER THÁNG {period}*\n\n"
            f"🥇 *{winner_meta['name']}*\n"
            f"💰 Revenue: {_fmt_vnd(winner_rev)}đ\n"
            f"⚡ GP Score: {winner_gp}/1000\n"
            f"📈 Multiplier: {multiplier}x\n\n"
            f"Sprint tiếp theo sẽ FOCUS vào *{winner_meta['name']}*!"
        )
        telegram_sent = send_telegram_sync(settings.telegram_bot_token, settings.telegram_chat_id, text)

    return {
        "winner_id":    winner_id,
        "winner_name":  winner_meta["name"],
        "gp_total":     winner_gp,
        "period":       period,
        "message":      f"Announced for {period}",
        "telegram_sent": telegram_sent,
    }


@router.get("/{project_id}/gp", response_model=GPScore)
async def get_gp_score(project_id: str, uid: str = Depends(get_current_user)):
    db = _get_db()
    period = date.today().strftime("%Y-%m")
    project_ids, all_metrics, int_cache, maxes = _load_gp_data(db, period)

    my      = all_metrics.get(project_id, {})
    my_int  = int_cache.get(project_id, {})
    my_status = my_int.get("cloudrun_status", "unknown")

    gp_revenue  = int((my.get("revenue_vnd", 0)       / maxes["revenue"]) * 400)
    gp_users    = int((my.get("active_users", 0)       / maxes["users"])   * 200)
    gp_velocity = int((my_int.get("github_commits_7d", 0) / maxes["commits"]) * 200)
    gp_uptime   = {"healthy": 200, "degraded": 100, "timeout": 50, "offline": 0, "unknown": 150}.get(my_status, 150)
    gp_total    = gp_revenue + gp_users + gp_velocity + gp_uptime

    all_gp   = {pid: _compute_gp_for(pid, all_metrics, int_cache, maxes) for pid in project_ids}
    is_focus = project_id == max(all_gp, key=all_gp.get)

    return GPScore(
        project_id=project_id,
        gp_total=gp_total,
        gp_revenue=gp_revenue,
        gp_users=gp_users,
        gp_velocity=gp_velocity,
        gp_uptime=gp_uptime,
        investment_multiplier=round(1.0 + (gp_total / 500), 2),
        is_focus=is_focus,
    )
