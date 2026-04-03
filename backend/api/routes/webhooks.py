from fastapi import APIRouter, Request, HTTPException, Header
from firebase_admin import firestore
from config import get_settings
from datetime import datetime, date

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_secret(x_hapura_secret: str):
    settings = get_settings()
    if x_hapura_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


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
