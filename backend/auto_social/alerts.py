"""Telegram alerts for auto-social events. Non-fatal on failure."""

from __future__ import annotations

import logging

from auto_social.models import AutoSocialPost
from config import get_settings

logger = logging.getLogger(__name__)


def notify_failed(post: AutoSocialPost) -> None:
    """Push a Telegram alert when a post enters `failed` state."""
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        logger.warning("Telegram not configured — skipping notify_failed for %s", post.id)
        return
    caption_preview = (post.caption or "")[:80].replace("\n", " ")
    msg = (
        "🚨 *AUTO-SOCIAL FAIL*\n"
        f"*{post.account}* | sched `{post.schedule_time}`\n"
        f"Caption: {caption_preview}\n"
        f"Error: `{(post.last_error or '')[:200]}`"
    )
    try:
        from agents.telegram import send_telegram_sync

        send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    except Exception as e:
        logger.error("notify_failed Telegram send failed: %s", e)


def notify_posted(post: AutoSocialPost) -> None:
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        return
    caption_preview = (post.caption or "")[:80].replace("\n", " ")
    msg = (
        "✅ *AUTO-SOCIAL POSTED*\n"
        f"*{post.account}* | {post.posted_url or '(no link)'}\n"
        f"Caption: {caption_preview}"
    )
    try:
        from agents.telegram import send_telegram_sync

        send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    except Exception as e:
        logger.error("notify_posted Telegram send failed: %s", e)
