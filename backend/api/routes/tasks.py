from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore
from api.deps import get_current_user
from models import TaskCreate, TaskStatusUpdate
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_db():
    return firestore.client()


@router.get("", response_model=list[dict])
async def list_tasks(project_id: Optional[str] = None, uid: str = Depends(get_current_user)):
    db = _get_db()
    query = db.collection("command_tasks")
    if project_id:
        query = query.where("project_id", "==", project_id)
    docs = query.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@router.post("", response_model=dict, status_code=201)
async def create_task(body: TaskCreate, uid: str = Depends(get_current_user)):
    db = _get_db()
    now = datetime.utcnow().isoformat()
    data = {
        **body.model_dump(),
        "status": "todo",
        "created_at": now,
        "updated_at": now,
        "created_by": uid,
    }
    ref = db.collection("command_tasks").document()
    ref.set(data)
    return {"id": ref.id, **data}


@router.put("/{task_id}", response_model=dict)
async def update_task(task_id: str, body: dict, uid: str = Depends(get_current_user)):
    db = _get_db()
    ref = db.collection("command_tasks").document(task_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Task not found")
    updates = {k: v for k, v in body.items() if k not in ("id", "created_at", "created_by")}
    updates["updated_at"] = datetime.utcnow().isoformat()
    ref.update(updates)
    return {"id": task_id, **ref.get().to_dict()}


@router.patch("/{task_id}/status", response_model=dict)
async def update_task_status(task_id: str, body: TaskStatusUpdate, uid: str = Depends(get_current_user)):
    if body.status not in ("todo", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")
    db = _get_db()
    ref = db.collection("command_tasks").document(task_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Task not found")
    ref.update({"status": body.status, "updated_at": datetime.utcnow().isoformat()})
    return {"id": task_id, **ref.get().to_dict()}


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, uid: str = Depends(get_current_user)):
    db = _get_db()
    db.collection("command_tasks").document(task_id).delete()
