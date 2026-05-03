"""auto-social module — TikTok scheduler via Buffer GraphQL.

Internal admin tool for scheduling TikTok posts. Single source of truth: Firestore
(`auto_social_posts`, `auto_social_channels`). Cloud Scheduler triggers cron endpoints
to dispatch pending posts to Buffer and reconcile status back.
"""

from auto_social.buffer_client import (
    BufferAccount,
    BufferAuthError,
    BufferChannel,
    BufferClient,
    BufferError,
    BufferPost,
    BufferRateLimitError,
)
from auto_social.models import (
    AutoSocialChannel,
    AutoSocialPost,
    AutoSocialPostCreate,
    AutoSocialPostUpdate,
    AutoSocialStats,
    DispatchSummary,
    ReconcileSummary,
)

__all__ = [
    "BufferAccount",
    "BufferAuthError",
    "BufferChannel",
    "BufferClient",
    "BufferError",
    "BufferPost",
    "BufferRateLimitError",
    "AutoSocialChannel",
    "AutoSocialPost",
    "AutoSocialPostCreate",
    "AutoSocialPostUpdate",
    "AutoSocialStats",
    "DispatchSummary",
    "ReconcileSummary",
]
