"""
Vertex Config Hub — API routes
Quản lý tập trung endpoint + model config cho tất cả Hapura projects.
"""
import secrets
import time
import httpx
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from firebase_admin import firestore
from pydantic import BaseModel

from api.deps import get_current_user, get_firebase_app
from config import get_settings

router = APIRouter(prefix="/vertex-config", tags=["vertex-config"])

COLLECTION = "vertex_configs"


# ─── Pydantic models ──────────────────────────────────────────────────────────

class EndpointConfig(BaseModel):
    base_url: str
    api_key_ref: str = ""


class ModelEntry(BaseModel):
    value: str
    endpoint: str = "default"


class ReloadWebhook(BaseModel):
    url: str = ""
    # Auth: hub sends client_token as Bearer — same token the SDK uses to poll the hub.
    # No separate secret needed; rotate via /projects/{id}/regenerate-token.


class VertexConfigDoc(BaseModel):
    project_id: str
    display_name: str
    endpoints: dict[str, EndpointConfig] = {}
    models: dict[str, ModelEntry] = {}
    env_map: dict[str, str] = {}
    reload_webhook: ReloadWebhook = ReloadWebhook()
    revision: int = 1
    updated_at: str = ""
    updated_by: str = ""
    last_fetch_at: str = ""   # updated by /client/{id} each time SDK polls
    client_token: str = ""


class VertexConfigCreate(BaseModel):
    project_id: str
    display_name: str
    endpoints: dict[str, EndpointConfig] = {}
    models: dict[str, ModelEntry] = {}
    env_map: dict[str, str] = {}
    reload_webhook: ReloadWebhook = ReloadWebhook()


class VertexConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    endpoints: Optional[dict[str, EndpointConfig]] = None
    models: Optional[dict[str, ModelEntry]] = None
    env_map: Optional[dict[str, str]] = None
    reload_webhook: Optional[ReloadWebhook] = None


class TestConnectionResult(BaseModel):
    ok: bool
    latency_ms: Optional[int] = None
    model: str = ""
    endpoint: str = ""
    sample: str = ""
    error: str = ""


class ReloadResult(BaseModel):
    ok: bool
    status_code: Optional[int] = None
    error: str = ""


# ─── Firestore helpers ────────────────────────────────────────────────────────

def _db():
    get_firebase_app()
    return firestore.client()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _doc_to_model(data: dict) -> VertexConfigDoc:
    """Convert Firestore dict to VertexConfigDoc, normalizing nested dicts."""
    endpoints = {
        k: EndpointConfig(**v) if isinstance(v, dict) else v
        for k, v in data.get("endpoints", {}).items()
    }
    models = {
        k: ModelEntry(**v) if isinstance(v, dict) else v
        for k, v in data.get("models", {}).items()
    }
    rw = data.get("reload_webhook", {})
    return VertexConfigDoc(
        project_id=data["project_id"],
        display_name=data.get("display_name", data["project_id"]),
        endpoints=endpoints,
        models=models,
        env_map=data.get("env_map", {}),
        reload_webhook=ReloadWebhook(**rw) if isinstance(rw, dict) else rw,
        revision=data.get("revision", 1),
        updated_at=data.get("updated_at", ""),
        updated_by=data.get("updated_by", ""),
        last_fetch_at=data.get("last_fetch_at", ""),
        client_token=data.get("client_token", ""),
    )


def _write_history(db, project_id: str, doc: VertexConfigDoc, user_email: str):
    """Append snapshot to history subcollection."""
    history_ref = (
        db.collection(COLLECTION)
        .document(project_id)
        .collection("history")
        .document(str(doc.revision))
    )
    payload = doc.model_dump()
    payload["updated_by"] = user_email
    payload["saved_at"] = _now_iso()
    history_ref.set(payload)


# ─── LIST ─────────────────────────────────────────────────────────────────────

@router.get("/projects")
async def list_configs(uid: str = Depends(get_current_user)):
    db = _db()
    docs = db.collection(COLLECTION).stream()
    result = []
    for d in docs:
        data = d.to_dict()
        if data:
            model = _doc_to_model(data)
            # Hide client_token from list
            out = model.model_dump()
            out["client_token"] = "***" if model.client_token else ""
            result.append(out)
    return result


# ─── GET ──────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}")
async def get_config(project_id: str, uid: str = Depends(get_current_user)):
    db = _db()
    doc = db.collection(COLLECTION).document(project_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    data = doc.to_dict()
    model = _doc_to_model(data)
    out = model.model_dump()
    out["client_token"] = "***" if model.client_token else ""
    return out


# ─── CREATE ───────────────────────────────────────────────────────────────────

@router.post("/projects", status_code=201)
async def create_config(body: VertexConfigCreate, uid: str = Depends(get_current_user)):
    db = _db()
    ref = db.collection(COLLECTION).document(body.project_id)
    if ref.get().exists:
        raise HTTPException(status_code=409, detail=f"Project '{body.project_id}' already exists")

    token = secrets.token_urlsafe(32)
    now = _now_iso()

    doc = VertexConfigDoc(
        project_id=body.project_id,
        display_name=body.display_name,
        endpoints=body.endpoints,
        models=body.models,
        env_map=body.env_map,
        reload_webhook=body.reload_webhook,
        revision=1,
        updated_at=now,
        updated_by=uid,
        client_token=token,
    )

    ref.set(doc.model_dump())
    _write_history(db, body.project_id, doc, uid)

    out = doc.model_dump()
    out["client_token"] = token  # Return plain token once on creation
    return out


# ─── UPDATE ───────────────────────────────────────────────────────────────────

@router.put("/projects/{project_id}")
async def update_config(
    project_id: str,
    body: VertexConfigUpdate,
    uid: str = Depends(get_current_user),
):
    db = _db()
    ref = db.collection(COLLECTION).document(project_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    current = _doc_to_model(snap.to_dict())

    # Apply partial update
    updated = current.model_copy(update={
        k: v for k, v in body.model_dump(exclude_none=True).items()
    })
    updated.revision = current.revision + 1
    updated.updated_at = _now_iso()
    updated.updated_by = uid

    ref.set(updated.model_dump())
    _write_history(db, project_id, updated, uid)

    out = updated.model_dump()
    out["client_token"] = "***" if updated.client_token else ""
    return out


# ─── DELETE ───────────────────────────────────────────────────────────────────

@router.delete("/projects/{project_id}", status_code=204)
async def delete_config(project_id: str, uid: str = Depends(get_current_user)):
    db = _db()
    ref = db.collection(COLLECTION).document(project_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    ref.delete()


# ─── HISTORY ─────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/history")
async def get_history(project_id: str, uid: str = Depends(get_current_user)):
    db = _db()
    docs = (
        db.collection(COLLECTION)
        .document(project_id)
        .collection("history")
        .order_by("revision", direction=firestore.Query.DESCENDING)
        .limit(20)
        .stream()
    )
    result = []
    for d in docs:
        data = d.to_dict()
        if data:
            data.pop("client_token", None)
            result.append(data)
    return result


# ─── ROLLBACK ─────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/rollback/{rev}")
async def rollback_config(
    project_id: str, rev: int, uid: str = Depends(get_current_user)
):
    db = _db()
    hist_ref = (
        db.collection(COLLECTION)
        .document(project_id)
        .collection("history")
        .document(str(rev))
    )
    snap = hist_ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Revision {rev} not found")

    old_data = snap.to_dict()

    # Get current doc to preserve client_token and bump revision
    cur_ref = db.collection(COLLECTION).document(project_id)
    cur_snap = cur_ref.get()
    if not cur_snap.exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    current = _doc_to_model(cur_snap.to_dict())
    restored = _doc_to_model(old_data)

    # Preserve token, bump revision
    restored.client_token = current.client_token
    restored.revision = current.revision + 1
    restored.updated_at = _now_iso()
    restored.updated_by = uid

    cur_ref.set(restored.model_dump())
    _write_history(db, project_id, restored, uid)

    out = restored.model_dump()
    out["client_token"] = "***"
    return out


# ─── REGENERATE TOKEN ─────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/regenerate-token")
async def regenerate_token(project_id: str, uid: str = Depends(get_current_user)):
    db = _db()
    ref = db.collection(COLLECTION).document(project_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    token = secrets.token_urlsafe(32)
    ref.update({"client_token": token, "updated_at": _now_iso(), "updated_by": uid})
    return {"client_token": token, "note": "Update VERTEX_CONFIG_TOKEN in your Cloud Run secrets."}


# ─── TEST CONNECTION ──────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/test", response_model=TestConnectionResult)
async def test_connection(project_id: str, uid: str = Depends(get_current_user)):
    db = _db()
    snap = db.collection(COLLECTION).document(project_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    doc = _doc_to_model(snap.to_dict())

    # Use default endpoint
    endpoint_cfg = doc.endpoints.get("default")
    if not endpoint_cfg:
        return TestConnectionResult(ok=False, error="No 'default' endpoint configured")

    # Pick first model or haiku fallback (aws/ prefix = new vertex-key.com format)
    model_str = "aws/claude-haiku-4-5"
    if doc.models:
        model_str = next(iter(doc.models.values())).value

    # Resolve API key: use hapura-command's own key (same vertex-key account)
    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        return TestConnectionResult(ok=False, error="Hub OPENAI_API_KEY not set in settings")

    base_url = endpoint_cfg.base_url.rstrip("/")
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_str,
                    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                    "max_tokens": 10,
                },
            )
        latency = int((time.monotonic() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            sample = data["choices"][0]["message"]["content"].strip()
            return TestConnectionResult(
                ok=True,
                latency_ms=latency,
                model=model_str,
                endpoint=base_url,
                sample=sample[:80],
            )
        else:
            return TestConnectionResult(
                ok=False,
                latency_ms=latency,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

    except Exception as e:
        return TestConnectionResult(ok=False, error=str(e)[:300])


# ─── TRIGGER RELOAD ───────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/reload", response_model=ReloadResult)
async def trigger_reload(project_id: str, uid: str = Depends(get_current_user)):
    db = _db()
    snap = db.collection(COLLECTION).document(project_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    doc = _doc_to_model(snap.to_dict())
    webhook_url = doc.reload_webhook.url.strip()

    if not webhook_url:
        return ReloadResult(ok=False, error="No reload webhook URL configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                headers={
                    "Authorization": f"Bearer {doc.client_token}",
                    "X-Hapura-Project": project_id,
                },
                json={"action": "reload", "revision": doc.revision},
            )
        return ReloadResult(ok=resp.status_code < 300, status_code=resp.status_code)
    except Exception as e:
        return ReloadResult(ok=False, error=str(e)[:200])


# ─── CLIENT ENDPOINT (for SDK) ────────────────────────────────────────────────

@router.get("/client/{project_id}")
async def client_get_config(
    project_id: str,
    x_hapura_token: str = Header(...),
):
    """
    SDK consumer endpoint — returns flat env dict.
    Auth: X-Hapura-Token header (not Firebase, Bearer token).
    """
    db = _db()
    snap = db.collection(COLLECTION).document(project_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    doc = _doc_to_model(snap.to_dict())

    # Verify token
    if not doc.client_token or not secrets.compare_digest(
        x_hapura_token.encode(), doc.client_token.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Resolve env_map → flat dict
    resolved: dict[str, str] = {}

    def _resolve_path(path: str) -> str:
        """Resolve dotted path like 'endpoints.default.base_url' from doc."""
        parts = path.split(".")
        if parts[0] == "endpoints" and len(parts) == 3:
            ep = doc.endpoints.get(parts[1])
            if ep:
                return getattr(ep, parts[2], "")
        if parts[0] == "models" and len(parts) == 3:
            m = doc.models.get(parts[1])
            if m:
                return getattr(m, parts[2], "")
        return ""

    for env_key, field_path in doc.env_map.items():
        val = _resolve_path(field_path)
        if val:
            resolved[env_key] = val

    # Also include all model values directly by key
    for model_key, model_entry in doc.models.items():
        if model_key not in resolved:
            resolved[model_key] = model_entry.value

    # Include default base_url if not already mapped
    default_ep = doc.endpoints.get("default")
    if default_ep and "OPENAI_BASE_URL" not in resolved:
        resolved.setdefault("VERTEX_BASE_URL", default_ep.base_url)

    # Track last fetch time so the UI can show "online/offline" status
    now = _now_iso()
    db.collection(COLLECTION).document(project_id).update({"last_fetch_at": now})

    return {
        "project_id": project_id,
        "revision": doc.revision,
        "updated_at": doc.updated_at,
        "last_fetch_at": now,
        "config": resolved,
    }
