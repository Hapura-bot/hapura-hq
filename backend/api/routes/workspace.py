"""
Workspace API routes — Department management, directives, agent messages.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from firebase_admin import firestore
from api.deps import get_current_user
from datetime import datetime

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _get_db():
    return firestore.client()


# ─── Departments ─────────────────────────────────────────────────────────────

@router.get("/departments", response_model=list[dict])
async def list_departments(uid: str = Depends(get_current_user)):
    """List all 7 departments with agent status summaries."""
    from workspace.registry import DEPARTMENTS, WORKSPACE_AGENT_META, EXISTING_AGENT_DEPARTMENTS

    db = _get_db()
    result = []

    for dept_id, dept in DEPARTMENTS.items():
        dept_data = dept.model_dump()

        # Count implemented agents
        implemented = 0
        total = len(dept.agent_ids)
        agent_statuses = []

        for agent_id in dept.agent_ids:
            # Check latest run status
            runs = list(
                db.collection("command_agent_runs")
                .where("agent_id", "==", agent_id)
                .order_by("started_at", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream()
            )

            is_existing = agent_id in EXISTING_AGENT_DEPARTMENTS
            is_new = agent_id in WORKSPACE_AGENT_META and WORKSPACE_AGENT_META[agent_id].get("is_new", False)

            status = "never"
            last_run_at = None
            if runs:
                run_data = runs[0].to_dict()
                status = run_data.get("status", "never")
                last_run_at = run_data.get("started_at")
                implemented += 1
            elif is_existing:
                implemented += 1

            # Get agent meta
            meta = WORKSPACE_AGENT_META.get(agent_id, {})
            agent_statuses.append({
                "id": agent_id,
                "name": meta.get("name", agent_id),
                "status": status,
                "last_run_at": last_run_at,
                "is_implemented": is_existing or (not is_new),
            })

        # Get latest department report (sort in Python to avoid needing composite index)
        try:
            raw_reports = list(
                db.collection("command_department_reports")
                .where("department_id", "==", dept_id)
                .limit(5)
                .stream()
            )
            raw_reports.sort(key=lambda d: d.to_dict().get("generated_at", ""), reverse=True)
            if raw_reports:
                report = raw_reports[0].to_dict()
                dept_data["last_summary_at"] = report.get("generated_at")
                dept_data["last_summary"] = report.get("summary", "")[:200]
            else:
                dept_data["last_summary_at"] = None
                dept_data["last_summary"] = ""
        except Exception:
            dept_data["last_summary_at"] = None
            dept_data["last_summary"] = ""

        dept_data["agents"] = agent_statuses
        dept_data["agents_implemented"] = implemented
        dept_data["agents_total"] = total
        # Simple health score: percentage of agents that have run successfully
        dept_data["health_score"] = int((implemented / total) * 100) if total > 0 else 0

        result.append(dept_data)

    return result


@router.get("/departments/{dept_id}", response_model=dict)
async def get_department(dept_id: str, uid: str = Depends(get_current_user)):
    """Get detailed department info with all agent reports."""
    from workspace.registry import DEPARTMENTS, WORKSPACE_AGENT_META, EXISTING_AGENT_DEPARTMENTS
    from api.routes.agents import AGENT_META as LEGACY_META

    dept = DEPARTMENTS.get(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    db = _get_db()
    dept_data = dept.model_dump()

    # Get all agents with their latest reports
    agents_detail = []
    for agent_id in dept.agent_ids:
        meta = WORKSPACE_AGENT_META.get(agent_id, LEGACY_META.get(agent_id, {}))

        # Get last 3 runs (sort in Python to avoid composite index requirement)
        raw_runs = list(
            db.collection("command_agent_runs")
            .where("agent_id", "==", agent_id)
            .limit(10)
            .stream()
        )
        raw_runs.sort(key=lambda d: d.to_dict().get("started_at", ""), reverse=True)
        runs = raw_runs[:3]

        agents_detail.append({
            "id": agent_id,
            "name": meta.get("name", agent_id),
            "role": meta.get("role", ""),
            "schedule": meta.get("schedule", ""),
            "color": meta.get("color", "brand"),
            "runs": [{"id": r.id, **r.to_dict()} for r in runs],
        })

    dept_data["agents_detail"] = agents_detail

    # Get department reports (sort in Python to avoid composite index)
    try:
        raw_dept_reports = list(
            db.collection("command_department_reports")
            .where("department_id", "==", dept_id)
            .limit(10)
            .stream()
        )
        raw_dept_reports.sort(key=lambda d: d.to_dict().get("generated_at", ""), reverse=True)
        dept_data["reports"] = [{"id": r.id, **r.to_dict()} for r in raw_dept_reports[:5]]
    except Exception:
        dept_data["reports"] = []

    # Get messages (simple queries — no compound index needed)
    try:
        incoming = list(
            db.collection("command_agent_messages")
            .where("to_department", "==", dept_id)
            .limit(10)
            .stream()
        )
        outgoing = list(
            db.collection("command_agent_messages")
            .where("from_department", "==", dept_id)
            .limit(10)
            .stream()
        )
    except Exception:
        incoming = []
        outgoing = []
    dept_data["messages_incoming"] = [{"id": m.id, **m.to_dict()} for m in incoming]
    dept_data["messages_outgoing"] = [{"id": m.id, **m.to_dict()} for m in outgoing]

    return dept_data


@router.post("/departments/{dept_id}/run", response_model=dict, status_code=202)
async def run_department_agents(
    dept_id: str,
    background_tasks: BackgroundTasks,
    uid: str = Depends(get_current_user),
):
    """Trigger all agents in a department. Returns immediately."""
    from workspace.registry import DEPARTMENTS

    if dept_id not in DEPARTMENTS:
        raise HTTPException(status_code=404, detail="Department not found")

    def _bg_run():
        from workspace.department_runner import run_department
        run_department(dept_id, triggered_by=f"manual:{uid}")

    background_tasks.add_task(_bg_run)

    return {
        "department_id": dept_id,
        "status": "running",
        "message": f"Department '{dept_id}' agents triggered. Check /workspace/departments/{dept_id} for results.",
    }


# ─── Directives ──────────────────────────────────────────────────────────────

@router.get("/directives", response_model=list[dict])
async def list_directives(uid: str = Depends(get_current_user), limit: int = 10):
    """List Weekly Directives."""
    db = _get_db()
    docs = list(db.collection("command_directives").limit(limit * 2).stream())
    docs.sort(key=lambda d: d.to_dict().get("generated_at", ""), reverse=True)
    return [{"id": d.id, **d.to_dict()} for d in docs[:limit]]


@router.post("/directives/{directive_id}/approve", response_model=dict)
async def approve_directive(directive_id: str, uid: str = Depends(get_current_user)):
    """CEO approves a directive, changing status to 'active'."""
    db = _get_db()
    ref = db.collection("command_directives").document(directive_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Directive not found")

    now = datetime.utcnow().isoformat()
    ref.update({
        "status": "active",
        "approved_by": uid,
        "approved_at": now,
    })
    return {"id": directive_id, "status": "active", "approved_by": uid, "approved_at": now}


# ─── Agent Messages ─────────────────────────────────────────────────────────

@router.get("/messages", response_model=list[dict])
async def list_agent_messages(
    uid: str = Depends(get_current_user),
    department: str | None = None,
    limit: int = 20,
):
    """List cross-department agent messages, optionally filtered by department."""
    db = _get_db()
    if department:
        to_msgs = list(
            db.collection("command_agent_messages")
            .where("to_department", "==", department)
            .limit(limit)
            .stream()
        )
        from_msgs = list(
            db.collection("command_agent_messages")
            .where("from_department", "==", department)
            .limit(limit)
            .stream()
        )
        seen: set = set()
        result = []
        for m in to_msgs + from_msgs:
            if m.id not in seen:
                seen.add(m.id)
                result.append({"id": m.id, **m.to_dict()})
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result[:limit]

    docs = list(db.collection("command_agent_messages").limit(limit).stream())
    docs.sort(key=lambda d: d.to_dict().get("created_at", ""), reverse=True)
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/messages/{message_id}/acknowledge", response_model=dict)
async def acknowledge_message(message_id: str, uid: str = Depends(get_current_user)):
    """Mark a cross-department message as acknowledged."""
    db = _get_db()
    ref = db.collection("command_agent_messages").document(message_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Message not found")
    ref.update({"acknowledged": True})
    return {"id": message_id, "acknowledged": True}


# ─── Workspace Config ────────────────────────────────────────────────────────

@router.get("/configs", response_model=list[dict])
async def list_workspace_configs(uid: str = Depends(get_current_user)):
    """List all product workspace configs."""
    db = _get_db()
    docs = list(db.collection("command_workspace_config").stream())
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.get("/config/{product_id}", response_model=dict)
async def get_workspace_config(product_id: str, uid: str = Depends(get_current_user)):
    """Get workspace configuration for a product."""
    db = _get_db()
    doc = db.collection("command_workspace_config").document(product_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Workspace config not found")
    return {"id": doc.id, **doc.to_dict()}


@router.put("/config/{product_id}", response_model=dict)
async def upsert_workspace_config(
    product_id: str,
    config: dict,
    uid: str = Depends(get_current_user),
):
    """Create or update workspace configuration for a product."""
    db = _get_db()
    config["product_id"] = product_id
    config["updated_at"] = datetime.utcnow().isoformat()
    db.collection("command_workspace_config").document(product_id).set(config, merge=True)
    return {"id": product_id, **config}


@router.post("/seed", response_model=dict)
async def seed_workspace(uid: str = Depends(get_current_user)):
    """One-time setup: seed departments + ClipPack/Trendkr workspace configs into Firestore."""
    from workspace.seed import seed_departments, seed_product, CLIPPACK_CONFIG, TRENDKR_CONFIG
    seed_departments()
    seed_product(CLIPPACK_CONFIG)
    seed_product(TRENDKR_CONFIG)
    return {
        "status": "seeded",
        "departments": 7,
        "products": ["clippack", "trendkr"],
        "message": "AI Workplace seeded. Visit /workplace to see departments.",
    }
