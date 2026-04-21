from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from firebase_admin import firestore
from pydantic import BaseModel
from config import get_settings
from datetime import datetime, date

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── Telegram / ARIA ───────────────────────────────────────────────────────────

async def _handle_aria(text: str, chat_id: str):
    from agents.hq_assistant import run_aria
    from agents.telegram import send_telegram_sync
    s = get_settings()
    try:
        reply = run_aria(text, chat_id)
    except Exception as e:
        reply = f"⚠️ ARIA gặp lỗi: {str(e)[:200]}"
    send_telegram_sync(s.telegram_bot_token, chat_id, reply)


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    """Receive updates from Telegram Bot API webhook."""
    s = get_settings()
    if x_telegram_bot_api_secret_token != s.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    body = await request.json()

    # Extract message
    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}  # Ignore non-message updates

    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))
    is_bot = message.get("from", {}).get("is_bot", False)

    # Only process text messages from Victor (not bots)
    if not text or is_bot or not chat_id:
        return {"ok": True}

    # Security: only Victor's chat
    if chat_id != str(s.telegram_chat_id):
        return {"ok": True}

    background_tasks.add_task(_handle_aria, text, chat_id)
    return {"ok": True}


def _verify_secret(x_hapura_secret: str):
    settings = get_settings()
    if x_hapura_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


# ── Notify (outbound alert) ───────────────────────────────────────────────────

class NotifyPayload(BaseModel):
    message: str
    level: str = "info"  # info | warning | error
    source: str = ""     # e.g. "openclaw-sync", "hapudub", "hapu-studio"

LEVEL_EMOJI = {"info": "ℹ️", "warning": "⚠️", "error": "🚨"}

@router.post("/notify")
async def notify(
    body: NotifyPayload,
    x_hapura_secret: str = Header(...),
):
    """Send an outbound Telegram alert to Victor. Auth: X-Hapura-Secret."""
    _verify_secret(x_hapura_secret)
    s = get_settings()
    emoji = LEVEL_EMOJI.get(body.level, "ℹ️")
    source_tag = f" `[{body.source}]`" if body.source else ""
    text = f"{emoji}{source_tag}\n{body.message}"
    from agents.telegram import send_telegram  # local import avoids circular
    ok = await send_telegram(s.telegram_bot_token, s.telegram_chat_id, text)
    if not ok:
        raise HTTPException(status_code=502, detail="Telegram delivery failed")
    return {"ok": True}


@router.post("/revenue")
async def revenue_webhook(
    request: Request,
    x_hapura_secret: str = Header(...),
):
    """Inbound revenue event from product apps."""
    _verify_secret(x_hapura_secret)
    body = await request.json()
    project_id = body.get("project_id")
    amount_vnd = body.get("amount_vnd", 0)
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")

    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    existing = list(
        db.collection("command_metrics")
        .where("project_id", "==", project_id)
        .where("period", "==", period)
        .limit(1)
        .stream()
    )
    now = datetime.utcnow().isoformat()
    if existing:
        doc = existing[0]
        current = doc.to_dict().get("revenue_vnd", 0)
        doc.reference.update({"revenue_vnd": current + amount_vnd, "recorded_at": now})
    else:
        db.collection("command_metrics").document().set({
            "project_id": project_id,
            "period": period,
            "revenue_vnd": amount_vnd,
            "active_users": 0,
            "new_signups": 0,
            "recorded_at": now,
            "recorded_by": "webhook",
        })
    return {"ok": True, "project_id": project_id, "amount_vnd": amount_vnd}


@router.post("/signup")
async def signup_webhook(
    request: Request,
    x_hapura_secret: str = Header(...),
):
    """Inbound signup event from product apps."""
    _verify_secret(x_hapura_secret)
    body = await request.json()
    project_id = body.get("project_id")
    user_count_delta = body.get("user_count_delta", 1)
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")

    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    existing = list(
        db.collection("command_metrics")
        .where("project_id", "==", project_id)
        .where("period", "==", period)
        .limit(1)
        .stream()
    )
    now = datetime.utcnow().isoformat()
    if existing:
        doc = existing[0]
        current_users = doc.to_dict().get("active_users", 0)
        current_signups = doc.to_dict().get("new_signups", 0)
        doc.reference.update({
            "active_users": current_users + user_count_delta,
            "new_signups": current_signups + user_count_delta,
            "recorded_at": now,
        })
    else:
        db.collection("command_metrics").document().set({
            "project_id": project_id,
            "period": period,
            "revenue_vnd": 0,
            "active_users": user_count_delta,
            "new_signups": user_count_delta,
            "recorded_at": now,
            "recorded_by": "webhook",
        })
    return {"ok": True, "project_id": project_id, "delta": user_count_delta}
