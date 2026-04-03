from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore
from api.deps import get_current_user
from models import MetricCreate
from datetime import datetime, date

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _get_db():
    return firestore.client()


@router.get("", response_model=list[dict])
async def list_metrics_latest(uid: str = Depends(get_current_user)):
    """Latest metric entry per project for current month."""
    db = _get_db()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [doc.to_dict() for doc in docs]


@router.get("/{project_id}", response_model=list[dict])
async def get_metric_history(project_id: str, uid: str = Depends(get_current_user)):
    """Last 12 months of metrics for one project."""
    db = _get_db()
    docs = (
        db.collection("command_metrics")
        .where("project_id", "==", project_id)
        .order_by("period", direction=firestore.Query.DESCENDING)
        .limit(12)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


@router.post("", response_model=dict, status_code=201)
async def create_metric(body: MetricCreate, uid: str = Depends(get_current_user)):
    """Manual metric entry. Upserts by project_id + period."""
    db = _get_db()
    # Check if entry for this project+period already exists — update it
    existing = (
        db.collection("command_metrics")
        .where("project_id", "==", body.project_id)
        .where("period", "==", body.period)
        .limit(1)
        .stream()
    )
    existing_docs = list(existing)
    now = datetime.utcnow().isoformat()
    data = {
        **body.model_dump(),
        "recorded_at": now,
        "recorded_by": uid,
    }
    if existing_docs:
        ref = existing_docs[0].reference
        ref.update(data)
        return {**data, "id": existing_docs[0].id}
    else:
        ref = db.collection("command_metrics").document()
        ref.set(data)
        return {**data, "id": ref.id}


@router.delete("/{metric_id}", status_code=204)
async def delete_metric(metric_id: str, uid: str = Depends(get_current_user)):
    db = _get_db()
    db.collection("command_metrics").document(metric_id).delete()
