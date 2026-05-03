"""Pydantic models for the auto-social module."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

PostStatus = Literal["pending", "uploading", "queued", "posted", "failed", "cancelled"]


class AutoSocialPost(BaseModel):
    id: Optional[str] = None
    account: str
    channel_id: str
    video_url: str
    thumbnail_url: Optional[str] = None
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    schedule_time: str  # ISO 8601 UTC
    status: PostStatus = "pending"
    buffer_post_id: Optional[str] = None
    posted_url: Optional[str] = None
    posted_at: Optional[str] = None
    attempts: int = 0
    last_error: Optional[str] = None
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class AutoSocialPostCreate(BaseModel):
    account: str
    channel_id: str
    video_url: str
    thumbnail_url: Optional[str] = None
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    schedule_time: str  # ISO 8601 (UTC or with offset)


class AutoSocialPostUpdate(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None
    schedule_time: Optional[str] = None
    status: Optional[Literal["cancelled"]] = None


class AutoSocialChannel(BaseModel):
    id: str  # = buffer channel id
    service: str
    name: str
    service_id: str = ""
    timezone: str = ""
    is_disconnected: bool = False
    external_link: Optional[str] = None
    last_synced_at: str = ""


class AutoSocialStats(BaseModel):
    pending: int = 0
    queued: int = 0
    uploading: int = 0
    posted: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0
    posted_last_7d: int = 0


class DispatchSummary(BaseModel):
    checked: int = 0
    dispatched: int = 0
    failed: int = 0


class ReconcileSummary(BaseModel):
    checked: int = 0
    updated: int = 0
    posted: int = 0
    failed: int = 0
