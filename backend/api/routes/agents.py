from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Header, Request
from firebase_admin import firestore
from api.deps import get_current_user
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/agents", tags=["agents"])

AGENT_IDS = ["health_checker", "strategist", "bug_detective", "revenue_forecaster", "hq_assistant"]

# Extended IDs: all workspace agents that can be triggered
WORKSPACE_AGENT_IDS = [
    "director", "aso_analyst", "content_strategist", "competitor_watcher",
    "feature_prioritizer", "release_planner", "pricing_strategist",
    "conversion_analyst", "review_monitor", "retention_analyst", "support_draft",
    "anomaly_detector", "dashboard_curator", "infra_monitor", "cost_optimizer",
]
ALL_AGENT_IDS = AGENT_IDS + WORKSPACE_AGENT_IDS

AGENT_META = {
    "health_checker": {
        "name": "Health Checker",
        "role": "Daily: Ping tất cả Cloud Run endpoints, báo cáo latency và status",
        "schedule": "Daily 08:00 VN",
        "color": "neon-green",
        "department": "product",
    },
    "strategist": {
        "name": "Strategist",
        "role": "Weekly: Phân tích GP scores, đề xuất focus project tuần tới",
        "schedule": "Monday 09:00 VN",
        "color": "neon-purple",
        "department": "analytics",
    },
    "bug_detective": {
        "name": "Bug Detective",
        "role": "On-demand: Tổng hợp GitHub Issues và PRs quan trọng của 4 projects",
        "schedule": "On demand",
        "color": "neon-amber",
        "department": "product",
    },
    "revenue_forecaster": {
        "name": "Revenue Forecaster",
        "role": "Monthly: Dự báo doanh thu tháng tới theo trend hiện tại",
        "schedule": "1st of month",
        "color": "brand",
        "department": "revenue",
    },
    "hq_assistant": {
        "name": "ARIA",
        "role": "Trợ lý ảo của Victor — nắm rõ 4 dự án, chat qua Telegram 24/7",
        "schedule": "Always on",
        "color": "neon-cyan",
        "department": "executive",
    },
}


def _get_db():
    return firestore.client()


def _run_agent(agent_id: str, triggered_by: str, run_doc_id: str):
    """Background task: actually run the agent and update Firestore."""
    db = _get_db()
    ref = db.collection("command_agent_runs").document(run_doc_id)
    try:
        if agent_id == "health_checker":
            from agents.health_checker import run_health_check
            result = run_health_check(triggered_by=triggered_by)
        elif agent_id == "strategist":
            from agents.strategist import run_strategy_analysis
            result = run_strategy_analysis(triggered_by=triggered_by)
        elif agent_id == "bug_detective":
            from agents.bug_detective import run_bug_detection
            result = run_bug_detection(triggered_by=triggered_by)
        elif agent_id == "revenue_forecaster":
            from agents.revenue_forecaster import run_revenue_forecast
            result = run_revenue_forecast(triggered_by=triggered_by)
        elif agent_id == "hq_assistant":
            result = {"report": "ARIA is always on via Telegram. No scheduled run needed.", "result": "ok"}
        elif agent_id in WORKSPACE_AGENT_IDS:
            from workspace.department_runner import run_agent_by_id
            result = run_agent_by_id(agent_id, triggered_by=triggered_by)
        else:
            result = {"error": "unknown agent"}

        # Update the pre-created run doc with results
        report = result.get("report", result.get("result", str(result)))
        ref.update({
            "status": "done",
            "finished_at": datetime.utcnow().isoformat(),
            "report_markdown": report[:10000],  # Firestore 1MB limit safety
            "summary": report[:300],
        })
    except Exception as e:
        ref.update({
            "status": "error",
            "finished_at": datetime.utcnow().isoformat(),
            "report_markdown": f"## Error\n\n```\n{str(e)}\n```",
            "summary": f"Error: {str(e)[:200]}",
        })


@router.get("", response_model=list[dict])
async def list_agents(uid: str = Depends(get_current_user)):
    """List all agents with their latest run info."""
    from workspace.registry import WORKSPACE_AGENT_META
    db = _get_db()
    result = []
    all_meta = {**AGENT_META}
    for aid, wmeta in WORKSPACE_AGENT_META.items():
        if aid not in all_meta:
            all_meta[aid] = wmeta
    for agent_id in ALL_AGENT_IDS:
        meta = all_meta.get(agent_id, {"name": agent_id, "role": "", "schedule": "", "color": "brand"}).copy()
        meta["id"] = agent_id

        # Get latest run
        runs = (
            db.collection("command_agent_runs")
            .where("agent_id", "==", agent_id)
            .order_by("started_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        runs_list = list(runs)
        if runs_list:
            latest = runs_list[0].to_dict()
            meta["last_run_at"] = latest.get("started_at")
            meta["last_run_status"] = latest.get("status")
            meta["last_run_summary"] = latest.get("summary", "")
            meta["last_run_id"] = runs_list[0].id
        else:
            meta["last_run_at"] = None
            meta["last_run_status"] = "never"
            meta["last_run_summary"] = ""
            meta["last_run_id"] = None

        result.append(meta)
    return result


@router.get("/{agent_id}/runs", response_model=list[dict])
async def list_agent_runs(
    agent_id: str,
    uid: str = Depends(get_current_user),
    limit: int = 10,
):
    if agent_id not in ALL_AGENT_IDS:
        raise HTTPException(status_code=404, detail="Agent not found")
    db = _get_db()
    docs = (
        db.collection("command_agent_runs")
        .where("agent_id", "==", agent_id)
        .order_by("started_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.get("/{agent_id}/runs/latest", response_model=dict)
async def get_latest_run(agent_id: str, uid: str = Depends(get_current_user)):
    if agent_id not in ALL_AGENT_IDS:
        raise HTTPException(status_code=404, detail="Agent not found")
    db = _get_db()
    docs = list(
        db.collection("command_agent_runs")
        .where("agent_id", "==", agent_id)
        .order_by("started_at", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    if not docs:
        raise HTTPException(status_code=404, detail="No runs yet")
    return {"id": docs[0].id, **docs[0].to_dict()}


@router.post("/{agent_id}/trigger", response_model=dict, status_code=202)
async def trigger_agent(
    agent_id: str,
    background_tasks: BackgroundTasks,
    uid: str = Depends(get_current_user),
):
    """Trigger an agent run. Returns immediately — run happens in background."""
    if agent_id not in ALL_AGENT_IDS:
        raise HTTPException(status_code=404, detail="Agent not found")

    db = _get_db()
    now = datetime.utcnow().isoformat()

    # Pre-create run doc with "running" status so frontend can poll
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": agent_id,
        "status": "running",
        "triggered_by": f"manual:{uid}",
        "started_at": now,
        "finished_at": None,
        "report_markdown": "",
        "summary": "Running...",
    })

    background_tasks.add_task(_run_agent, agent_id, f"manual:{uid}", ref.id)

    return {
        "run_id": ref.id,
        "agent_id": agent_id,
        "status": "running",
        "started_at": now,
        "message": f"Agent '{agent_id}' triggered. Poll /agents/{agent_id}/runs/latest for results.",
    }


@router.post("/hq_assistant/chat", response_model=dict)
async def aria_chat(
    request: Request,
    uid: str = Depends(get_current_user),
):
    """Send a message to ARIA and get a reply. Used by web UI."""
    body = await request.json()
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    from agents.hq_assistant import run_aria
    reply = run_aria(message, chat_id=f"web:{uid}")
    return {"reply": reply}


@router.get("/hq_assistant/conversations", response_model=list[dict])
async def get_aria_conversations(
    uid: str = Depends(get_current_user),
    limit: int = 30,
):
    """Get ARIA conversation history for display in frontend."""
    from agents.hq_assistant import get_conversation_history
    return get_conversation_history(f"web:{uid}", limit=limit)


@router.post("/schedule/{agent_id}", response_model=dict, status_code=202)
async def schedule_agent(
    agent_id: str,
    background_tasks: BackgroundTasks,
    x_scheduler_secret: str = Header(...),
):
    """Cloud Scheduler endpoint — secret-based auth, no Firebase token required."""
    from config import get_settings
    settings = get_settings()
    if x_scheduler_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if agent_id not in ALL_AGENT_IDS:
        raise HTTPException(status_code=404, detail="Agent not found")

    db = _get_db()
    now = datetime.utcnow().isoformat()
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": agent_id,
        "status": "running",
        "triggered_by": "scheduler",
        "started_at": now,
        "finished_at": None,
        "report_markdown": "",
        "summary": "Running...",
    })
    background_tasks.add_task(_run_agent, agent_id, "scheduler", ref.id)
    return {
        "run_id": ref.id,
        "agent_id": agent_id,
        "status": "running",
        "started_at": now,
    }
