"""
Cloud Scheduler endpoints — triggered by Google Cloud Scheduler jobs.
Auth: X-Scheduler-Secret header (set as SCHEDULER_SECRET env var).
Each job POSTs to the relevant endpoint on a cron schedule.
"""
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from config import get_settings

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _verify(secret: str | None):
    s = get_settings()
    if secret != s.scheduler_secret:
        raise HTTPException(status_code=401, detail="Invalid scheduler secret")


# ─── Department runners ──────────────────────────────────────────────────────

@router.post("/departments/{dept_id}/run")
async def schedule_department(
    dept_id: str,
    background_tasks: BackgroundTasks,
    x_scheduler_secret: str = Header(None),
):
    """Cloud Scheduler triggers a full department run."""
    _verify(x_scheduler_secret)
    from workspace.registry import DEPARTMENTS
    if dept_id not in DEPARTMENTS:
        raise HTTPException(status_code=404, detail="Department not found")

    def _run():
        from workspace.department_runner import run_department
        run_department(dept_id, triggered_by="cloud_scheduler")

    background_tasks.add_task(_run)
    return {"department_id": dept_id, "status": "triggered", "triggered_by": "cloud_scheduler"}


# ─── Individual agent runners ────────────────────────────────────────────────

@router.post("/agents/{agent_id}/run")
async def schedule_agent(
    agent_id: str,
    background_tasks: BackgroundTasks,
    x_scheduler_secret: str = Header(None),
):
    """Cloud Scheduler triggers a single agent."""
    _verify(x_scheduler_secret)

    def _run():
        from workspace.department_runner import run_agent_by_id
        run_agent_by_id(agent_id, triggered_by="cloud_scheduler")

    background_tasks.add_task(_run)
    return {"agent_id": agent_id, "status": "triggered", "triggered_by": "cloud_scheduler"}


# ─── Director (weekly directive) ─────────────────────────────────────────────

@router.post("/director/run")
async def schedule_director(
    background_tasks: BackgroundTasks,
    x_scheduler_secret: str = Header(None),
):
    """Cloud Scheduler triggers the Director Agent (Weekly Directive)."""
    _verify(x_scheduler_secret)

    def _run():
        from workspace.director import run_director
        run_director(triggered_by="cloud_scheduler")

    background_tasks.add_task(_run)
    return {"agent_id": "director", "status": "triggered", "triggered_by": "cloud_scheduler"}
