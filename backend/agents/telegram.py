"""Telegram notification helper for all agents."""
import httpx
import logging

logger = logging.getLogger(__name__)


async def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    """Send a message to a Telegram chat. Returns True on success."""
    if not bot_token or not chat_id:
        logger.warning("Telegram not configured — skipping notification")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            if r.status_code == 200:
                return True
            logger.error(f"Telegram error: {r.status_code} {r.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_telegram_sync(bot_token: str, chat_id: str, text: str) -> bool:
    """Sync wrapper for use inside PraisonAI @tool functions."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, send_telegram(bot_token, chat_id, text))
                return future.result(timeout=15)
        return loop.run_until_complete(send_telegram(bot_token, chat_id, text))
    except Exception as e:
        logger.error(f"Telegram sync send failed: {e}")
        return False
