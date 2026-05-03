"""Auto-social API routes.

CRUD on `auto_social_posts` + channels sync + stats + Cloud Scheduler cron triggers.

Auth:
- User-facing routes: `Depends(get_current_user)` (Firebase ID token + email allowlist).
- Cron routes: `X-Scheduler-Secret` header (matches `settings.scheduler_secret`).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from api.deps import get_current_user
from auto_social import (
    AutoSocialChannel,
    AutoSocialPost,
    AutoSocialPostCreate,
    AutoSocialPostUpdate,
    AutoSocialStats,
    BufferClient,
    BufferError,
    DispatchSummary,
    ReconcileSummary,
)
from auto_social import service
from auto_social.repo import channels_repo, posts_repo
from auto_social.time_utils import now_utc, to_iso_utc
from config import get_settings

router = APIRouter(prefix="/auto-social", tags=["auto-social"])


# ─── Posts CRUD ─────────────────────────────────────────────────────────────


@router.post("/posts", response_model=AutoSocialPost)
async def create_post(
    payload: AutoSocialPostCreate, uid: str = Depends(get_current_user)
) -> AutoSocialPost:
    try:
        post = posts_repo.create(payload, created_by=uid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return post


@router.get("/posts", response_model=list[AutoSocialPost])
async def list_posts(
    status: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    schedule_from: Optional[str] = Query(None, description="ISO 8601 UTC"),
    schedule_to: Optional[str] = Query(None, description="ISO 8601 UTC"),
    descending: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    uid: str = Depends(get_current_user),
) -> list[AutoSocialPost]:
    return posts_repo.list(
        status=status,
        account=account,
        schedule_from=schedule_from,
        schedule_to=schedule_to,
        descending=descending,
        limit=limit,
    )


@router.get("/posts/{post_id}", response_model=AutoSocialPost)
async def get_post(post_id: str, uid: str = Depends(get_current_user)) -> AutoSocialPost:
    post = posts_repo.get(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.put("/posts/{post_id}", response_model=AutoSocialPost)
async def update_post(
    post_id: str,
    patch: AutoSocialPostUpdate,
    uid: str = Depends(get_current_user),
) -> AutoSocialPost:
    existing = posts_repo.get(post_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if existing.status not in ("pending", "queued"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit a post in status '{existing.status}'",
        )

    update = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
    if "schedule_time" in update:
        try:
            from auto_social.time_utils import parse_iso_utc

            update["schedule_time"] = to_iso_utc(parse_iso_utc(update["schedule_time"]))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    return posts_repo.update(post_id, update)


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, uid: str = Depends(get_current_user)) -> dict:
    """Hard-delete: cancels in Buffer if queued, then removes Firestore doc."""
    existing = posts_repo.get(post_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Post not found")

    buffer_deleted = False
    if existing.buffer_post_id and existing.status not in ("posted", "failed", "cancelled"):
        try:
            BufferClient().delete_post(existing.buffer_post_id)
            buffer_deleted = True
        except BufferError as e:
            # Don't block local delete — just record the issue
            posts_repo.update(post_id, {"last_error": f"buffer delete failed: {str(e)[:200]}"})

    posts_repo.delete(post_id)
    return {"ok": True, "buffer_deleted": buffer_deleted}


# ─── Channels ───────────────────────────────────────────────────────────────


@router.get("/channels", response_model=list[AutoSocialChannel])
async def list_channels(uid: str = Depends(get_current_user)) -> list[AutoSocialChannel]:
    return channels_repo.list()


@router.post("/channels/sync", response_model=list[AutoSocialChannel])
async def sync_channels(uid: str = Depends(get_current_user)) -> list[AutoSocialChannel]:
    try:
        return service.sync_channels()
    except BufferError as e:
        raise HTTPException(status_code=502, detail=f"Buffer: {e}") from e


# ─── Stats ──────────────────────────────────────────────────────────────────


@router.get("/stats", response_model=AutoSocialStats)
async def get_stats(uid: str = Depends(get_current_user)) -> AutoSocialStats:
    posts = posts_repo.list(limit=1000)
    counts: dict[str, int] = {}
    for p in posts:
        counts[p.status] = counts.get(p.status, 0) + 1

    seven_days_ago = to_iso_utc(now_utc() - timedelta(days=7))
    posted_last_7d = sum(
        1 for p in posts if p.status == "posted" and (p.posted_at or "") >= seven_days_ago
    )

    return AutoSocialStats(
        pending=counts.get("pending", 0),
        queued=counts.get("queued", 0),
        uploading=counts.get("uploading", 0),
        posted=counts.get("posted", 0),
        failed=counts.get("failed", 0),
        cancelled=counts.get("cancelled", 0),
        total=len(posts),
        posted_last_7d=posted_last_7d,
    )


# ─── Cloud Scheduler cron triggers ──────────────────────────────────────────


def _verify_scheduler(secret: str | None) -> None:
    s = get_settings()
    if secret != s.scheduler_secret:
        raise HTTPException(status_code=401, detail="Invalid scheduler secret")


@router.post("/cron/dispatch", response_model=DispatchSummary)
async def cron_dispatch(x_scheduler_secret: str | None = Header(None)) -> DispatchSummary:
    """Cloud Scheduler 5-min trigger: push due pending posts to Buffer."""
    _verify_scheduler(x_scheduler_secret)
    return service.dispatch_pending()


@router.post("/cron/reconcile", response_model=ReconcileSummary)
async def cron_reconcile(x_scheduler_secret: str | None = Header(None)) -> ReconcileSummary:
    """Cloud Scheduler 10-min trigger: sync Buffer post status back to Firestore."""
    _verify_scheduler(x_scheduler_secret)
    return service.reconcile_active()
