"""Firestore repositories for auto-social.

Collections:
  auto_social_posts/{id}
  auto_social_channels/{buffer_channel_id}
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from firebase_admin import firestore
from google.cloud.firestore import Transaction

from auto_social.models import (
    AutoSocialChannel,
    AutoSocialPost,
    AutoSocialPostCreate,
    PostStatus,
)
from auto_social.time_utils import now_utc, to_iso_utc

logger = logging.getLogger(__name__)

POSTS_COLLECTION = "auto_social_posts"
CHANNELS_COLLECTION = "auto_social_channels"

_TERMINAL_STATUSES: tuple[PostStatus, ...] = ("posted", "failed", "cancelled")


def _db():
    return firestore.client()


def _doc_to_post(doc) -> AutoSocialPost | None:
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return AutoSocialPost.model_validate(data)


def _doc_to_channel(doc) -> AutoSocialChannel | None:
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return AutoSocialChannel.model_validate(data)


class PostsRepo:
    def create(self, payload: AutoSocialPostCreate, created_by: str) -> AutoSocialPost:
        doc_id = uuid.uuid4().hex
        now_iso = to_iso_utc(now_utc())
        # Normalize schedule_time to UTC ISO if input has offset
        from auto_social.time_utils import parse_iso_utc

        try:
            sched_utc = to_iso_utc(parse_iso_utc(payload.schedule_time))
        except ValueError as e:
            raise ValueError(f"Invalid schedule_time: {payload.schedule_time}") from e

        record: dict[str, Any] = {
            **payload.model_dump(),
            "schedule_time": sched_utc,
            "status": "pending",
            "buffer_post_id": None,
            "posted_url": None,
            "posted_at": None,
            "attempts": 0,
            "last_error": None,
            "created_by": created_by,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        _db().collection(POSTS_COLLECTION).document(doc_id).set(record)
        record["id"] = doc_id
        return AutoSocialPost.model_validate(record)

    def get(self, post_id: str) -> AutoSocialPost | None:
        doc = _db().collection(POSTS_COLLECTION).document(post_id).get()
        return _doc_to_post(doc)

    def list(
        self,
        *,
        status: str | None = None,
        account: str | None = None,
        schedule_from: str | None = None,
        schedule_to: str | None = None,
        order_by: str = "schedule_time",
        descending: bool = False,
        limit: int = 200,
    ) -> list[AutoSocialPost]:
        q = _db().collection(POSTS_COLLECTION)
        if status:
            q = q.where(filter=firestore.FieldFilter("status", "==", status))
        if account:
            q = q.where(filter=firestore.FieldFilter("account", "==", account))
        if schedule_from:
            q = q.where(filter=firestore.FieldFilter("schedule_time", ">=", schedule_from))
        if schedule_to:
            q = q.where(filter=firestore.FieldFilter("schedule_time", "<=", schedule_to))
        direction = firestore.Query.DESCENDING if descending else firestore.Query.ASCENDING
        q = q.order_by(order_by, direction=direction).limit(limit)
        return [_doc_to_post(d) for d in q.stream() if d.exists]

    def update(self, post_id: str, patch: dict[str, Any]) -> AutoSocialPost:
        patch = {**patch, "updated_at": to_iso_utc(now_utc())}
        ref = _db().collection(POSTS_COLLECTION).document(post_id)
        ref.update(patch)
        return self.get(post_id)  # type: ignore[return-value]

    def delete(self, post_id: str) -> None:
        _db().collection(POSTS_COLLECTION).document(post_id).delete()

    def list_pending_due(self, now_iso_utc: str, limit: int = 10) -> list[AutoSocialPost]:
        q = (
            _db()
            .collection(POSTS_COLLECTION)
            .where(filter=firestore.FieldFilter("status", "==", "pending"))
            .where(filter=firestore.FieldFilter("schedule_time", "<=", now_iso_utc))
            .order_by("schedule_time", direction=firestore.Query.ASCENDING)
            .limit(limit)
        )
        return [_doc_to_post(d) for d in q.stream() if d.exists]

    def list_non_terminal_with_buffer_id(self, limit: int = 50) -> list[AutoSocialPost]:
        # Firestore doesn't support not-in + != null in same query cleanly;
        # query by status not in terminal, then filter buffer_post_id in memory.
        q = (
            _db()
            .collection(POSTS_COLLECTION)
            .where(filter=firestore.FieldFilter("status", "not-in", list(_TERMINAL_STATUSES)))
            .limit(limit * 2)
        )
        out: list[AutoSocialPost] = []
        for d in q.stream():
            if not d.exists:
                continue
            post = _doc_to_post(d)
            if post and post.buffer_post_id:
                out.append(post)
                if len(out) >= limit:
                    break
        return out

    def transition(self, post_id: str, *, expected_from: str, to: str) -> bool:
        """Atomic state transition. Returns True on success, False if status mismatch."""
        ref = _db().collection(POSTS_COLLECTION).document(post_id)

        @firestore.transactional
        def _txn(tx: Transaction) -> bool:
            snap = ref.get(transaction=tx)
            if not snap.exists:
                return False
            current = (snap.to_dict() or {}).get("status")
            if current != expected_from:
                return False
            tx.update(ref, {"status": to, "updated_at": to_iso_utc(now_utc())})
            return True

        return _txn(_db().transaction())


class ChannelsRepo:
    def upsert(self, channel: AutoSocialChannel) -> None:
        ref = _db().collection(CHANNELS_COLLECTION).document(channel.id)
        data = channel.model_dump()
        data["last_synced_at"] = to_iso_utc(now_utc())
        ref.set(data, merge=True)

    def list(self) -> list[AutoSocialChannel]:
        docs = _db().collection(CHANNELS_COLLECTION).stream()
        return [_doc_to_channel(d) for d in docs if d.exists]

    def get(self, channel_id: str) -> AutoSocialChannel | None:
        doc = _db().collection(CHANNELS_COLLECTION).document(channel_id).get()
        return _doc_to_channel(doc)


posts_repo = PostsRepo()
channels_repo = ChannelsRepo()
