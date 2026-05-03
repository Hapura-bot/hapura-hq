"""Auto-social post lifecycle service.

dispatch_pending — picks pending posts due now, calls Buffer, transitions state.
reconcile_active — fetches non-terminal posts with buffer_post_id, syncs status from Buffer.
sync_channels    — pulls Buffer channels, upserts Firestore.
"""

from __future__ import annotations

import logging

from auto_social import alerts
from auto_social.buffer_client import BufferClient, BufferError
from auto_social.models import (
    AutoSocialChannel,
    DispatchSummary,
    PostStatus,
    ReconcileSummary,
)
from auto_social.repo import channels_repo, posts_repo
from auto_social.time_utils import now_utc, parse_iso_utc, to_iso_utc

logger = logging.getLogger(__name__)


_BUFFER_TO_STATUS: dict[str, PostStatus] = {
    "scheduled": "queued",
    "queued": "queued",
    "sending": "uploading",
    "uploading": "uploading",
    "sent": "posted",
    "delivered": "posted",
    "failed": "failed",
    "error": "failed",
    "draft": "cancelled",
}


def _map_buffer_status(s: str) -> PostStatus:
    return _BUFFER_TO_STATUS.get((s or "").lower(), "queued")


def dispatch_pending(batch_limit: int = 10, client: BufferClient | None = None) -> DispatchSummary:
    """Push due pending posts to Buffer. Idempotent via atomic transition."""
    client = client or BufferClient()
    now_iso = to_iso_utc(now_utc())
    posts = posts_repo.list_pending_due(now_iso, limit=batch_limit)

    summary = DispatchSummary(checked=len(posts))
    for post in posts:
        if post.id is None:
            continue
        # Claim the row atomically. If someone else already moved it, skip.
        if not posts_repo.transition(post.id, expected_from="pending", to="uploading"):
            continue

        text_parts = [post.caption or ""]
        if post.hashtags:
            text_parts.append(" ".join(post.hashtags))
        text = "\n\n".join(p for p in text_parts if p)

        try:
            buffer_post = client.create_scheduled_post(
                channel_id=post.channel_id,
                text=text,
                due_at=parse_iso_utc(post.schedule_time),
                video_url=post.video_url,
                thumbnail_url=post.thumbnail_url,
                video_title=(post.caption or "")[:80] or None,
            )
            posts_repo.update(
                post.id,
                {
                    "status": "queued",
                    "buffer_post_id": buffer_post.id,
                    "attempts": post.attempts + 1,
                    "last_error": None,
                },
            )
            summary.dispatched += 1
            logger.info("[dispatch] queued %s buffer=%s", post.id, buffer_post.id)
        except BufferError as e:
            updated = posts_repo.update(
                post.id,
                {
                    "status": "failed",
                    "last_error": str(e)[:500],
                    "attempts": post.attempts + 1,
                },
            )
            summary.failed += 1
            logger.warning("[dispatch] failed %s: %s", post.id, e)
            try:
                alerts.notify_failed(updated)
            except Exception:
                logger.exception("notify_failed crashed for %s", post.id)

    return summary


def reconcile_active(batch_limit: int = 50, client: BufferClient | None = None) -> ReconcileSummary:
    """Mirror Buffer post status to Firestore for all in-flight posts."""
    client = client or BufferClient()
    posts = posts_repo.list_non_terminal_with_buffer_id(limit=batch_limit)

    summary = ReconcileSummary(checked=len(posts))
    for post in posts:
        if post.id is None or not post.buffer_post_id:
            continue
        try:
            buffer_post = client.get_post(post.buffer_post_id)
        except BufferError as e:
            logger.warning("[reconcile] buffer error for %s: %s", post.id, e)
            continue
        if buffer_post is None:
            continue

        new_status = _map_buffer_status(buffer_post.status)
        if new_status == post.status:
            continue

        patch: dict = {"status": new_status}
        if new_status == "posted":
            patch["posted_url"] = buffer_post.external_link
            patch["posted_at"] = to_iso_utc(now_utc())
            summary.posted += 1
        elif new_status == "failed":
            summary.failed += 1
            patch["last_error"] = patch.get("last_error") or "Buffer reported failed"

        updated = posts_repo.update(post.id, patch)
        summary.updated += 1

        if new_status == "posted":
            try:
                alerts.notify_posted(updated)
            except Exception:
                logger.exception("notify_posted crashed for %s", post.id)
        elif new_status == "failed":
            try:
                alerts.notify_failed(updated)
            except Exception:
                logger.exception("notify_failed crashed for %s", post.id)

    return summary


def sync_channels(client: BufferClient | None = None) -> list[AutoSocialChannel]:
    """Pull Buffer channels for the API key's organization and upsert Firestore."""
    client = client or BufferClient()
    account = client.get_account()
    buffer_channels = client.list_channels(account.organization_id)

    out: list[AutoSocialChannel] = []
    for c in buffer_channels:
        ch = AutoSocialChannel(
            id=c.id,
            service=c.service,
            name=c.name,
            service_id=c.service_id,
            timezone=c.timezone,
            is_disconnected=c.is_disconnected,
            external_link=c.external_link,
        )
        channels_repo.upsert(ch)
        out.append(ch)
    return out
