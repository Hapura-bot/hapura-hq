from fastapi import APIRouter, Depends, BackgroundTasks
from firebase_admin import firestore
from api.deps import get_current_user
from config import get_settings
from datetime import datetime, timedelta
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])

# Project → GitHub repo mapping
GITHUB_REPOS = {
    "clippack":         "Hapura-bot/clippack",
    "trendkr":          "Hapura-bot/trendkr",
    "hapu-studio":      "Hapura-bot/great-studio",
    "douyin-vi-dubber": "Hapura-bot/douyin-vi-dubber",
}

# Project → Cloud Run service name mapping
CLOUDRUN_SERVICES = {
    "clippack":         "clippack-backend",
    "trendkr":          "trendkr-backend",
    "hapu-studio":      "hapu-studio-backend",
    "douyin-vi-dubber": "douyin-vi-dubber-api",
}

# Known health endpoints for direct ping
HEALTH_ENDPOINTS = {
    "clippack":         "https://clippack-backend-730131473012.asia-southeast1.run.app/health",
    "trendkr":          "https://trendkr-backend-730131473012.asia-southeast1.run.app/health",
    "douyin-vi-dubber": "https://hapudub.hapura.vn/api/health",
}


def _get_db():
    return firestore.client()


def _is_cache_fresh(cached: dict, ttl_minutes: int) -> bool:
    fetched_at = cached.get("fetched_at")
    if not fetched_at:
        return False
    try:
        t = datetime.fromisoformat(fetched_at)
        return datetime.utcnow() - t < timedelta(minutes=ttl_minutes)
    except Exception:
        return False


async def _fetch_github_stats(repo: str, token: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=10) as client:
        # Commit activity (last 52 weeks, take last 4 weeks)
        commits_7d = 0
        commits_4w = []
        try:
            r = await client.get(
                f"https://api.github.com/repos/{repo}/stats/commit_activity",
                headers=headers,
            )
            if r.status_code == 200:
                weeks = r.json()
                commits_4w = [w["total"] for w in weeks[-4:]]
                commits_7d = weeks[-1]["total"] if weeks else 0
        except Exception as e:
            logger.warning(f"GitHub commits error for {repo}: {e}")

        # Open issues count
        open_issues = 0
        open_prs = 0
        last_commit_at = None
        try:
            r = await client.get(
                f"https://api.github.com/repos/{repo}",
                headers=headers,
            )
            if r.status_code == 200:
                data = r.json()
                open_issues = data.get("open_issues_count", 0)
                last_pushed = data.get("pushed_at")
                if last_pushed:
                    last_commit_at = last_pushed
        except Exception as e:
            logger.warning(f"GitHub repo info error for {repo}: {e}")

    return {
        "commits_7d": commits_7d,
        "commits_4w": commits_4w,
        "open_issues": open_issues,
        "open_prs": open_prs,
        "last_commit_at": last_commit_at,
    }


async def _ping_health(project_id: str) -> dict:
    url = HEALTH_ENDPOINTS.get(project_id)
    if not url:
        return {"status": "unknown", "latency_ms": None}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            start = datetime.utcnow()
            r = await client.get(url)
            latency = int((datetime.utcnow() - start).total_seconds() * 1000)
            return {
                "status": "healthy" if r.status_code == 200 else "degraded",
                "latency_ms": latency,
                "status_code": r.status_code,
            }
    except httpx.TimeoutException:
        return {"status": "timeout", "latency_ms": 8000}
    except Exception as e:
        return {"status": "offline", "latency_ms": None, "error": str(e)}


async def _refresh_project_cache(project_id: str):
    settings = get_settings()
    db = _get_db()
    now = datetime.utcnow().isoformat()

    github_data = {}
    repo = GITHUB_REPOS.get(project_id)
    if repo and settings.github_token:
        github_data = await _fetch_github_stats(repo, settings.github_token)
    elif repo:
        # No token — try unauthenticated (60 req/hr limit)
        github_data = await _fetch_github_stats(repo, "")

    health_data = await _ping_health(project_id)

    cache = {
        "project_id": project_id,
        "github_repo": repo or "",
        "github_commits_7d": github_data.get("commits_7d", 0),
        "github_commits_4w": github_data.get("commits_4w", []),
        "github_open_issues": github_data.get("open_issues", 0),
        "github_open_prs": github_data.get("open_prs", 0),
        "github_last_commit_at": github_data.get("last_commit_at"),
        "cloudrun_status": health_data.get("status", "unknown"),
        "cloudrun_latency_ms": health_data.get("latency_ms"),
        "fetched_at": now,
    }

    db.collection("command_integrations_cache").document(project_id).set(cache)
    return cache


@router.get("/{project_id}", response_model=dict)
async def get_project_integrations(
    project_id: str,
    background_tasks: BackgroundTasks,
    uid: str = Depends(get_current_user),
):
    settings = get_settings()
    db = _get_db()
    ref = db.collection("command_integrations_cache").document(project_id)
    doc = ref.get()

    if doc.exists:
        cached = doc.to_dict()
        if _is_cache_fresh(cached, settings.integrations_cache_ttl_minutes):
            return cached
        # Stale — return cached data and refresh in background
        background_tasks.add_task(_refresh_project_cache, project_id)
        return cached

    # No cache — fetch synchronously first time
    return await _refresh_project_cache(project_id)


@router.post("/{project_id}/refresh", response_model=dict)
async def force_refresh(project_id: str, uid: str = Depends(get_current_user)):
    """Force-refresh integration cache for a project."""
    return await _refresh_project_cache(project_id)


@router.get("", response_model=list[dict])
async def get_all_integrations(
    background_tasks: BackgroundTasks,
    uid: str = Depends(get_current_user),
):
    """Return cached integration data for all 4 projects."""
    settings = get_settings()
    db = _get_db()
    project_ids = list(GITHUB_REPOS.keys())
    result = []

    for pid in project_ids:
        ref = db.collection("command_integrations_cache").document(pid)
        doc = ref.get()
        if doc.exists:
            cached = doc.to_dict()
            if not _is_cache_fresh(cached, settings.integrations_cache_ttl_minutes):
                background_tasks.add_task(_refresh_project_cache, pid)
            result.append(cached)
        else:
            # Fetch synchronously if no cache at all
            data = await _refresh_project_cache(pid)
            result.append(data)

    return result
