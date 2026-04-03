"""
DepartmentRunner — Orchestrates all agents within a department.
Runs specialists sequentially, then produces a department summary.
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from workspace.registry import DEPARTMENTS, get_agents_in_department
from workspace.base_agent import save_department_report, setup_llm

logger = logging.getLogger(__name__)

# Maps agent_id -> (module_path, function_name)
AGENT_RUNNERS: dict[str, tuple[str, str]] = {
    # Existing agents
    "health_checker":      ("agents.health_checker", "run_health_check"),
    "strategist":          ("agents.strategist", "run_strategy_analysis"),
    "bug_detective":       ("agents.bug_detective", "run_bug_detection"),
    "revenue_forecaster":  ("agents.revenue_forecaster", "run_revenue_forecast"),
    # Growth agents (Phase 2)
    "aso_analyst":         ("workspace.departments.growth", "run_aso_analyst"),
    "content_strategist":  ("workspace.departments.growth", "run_content_strategist"),
    "competitor_watcher":  ("workspace.departments.growth", "run_competitor_watcher"),
    # Product agents (Phase 2+)
    "feature_prioritizer": ("workspace.departments.product", "run_feature_prioritizer"),
    "release_planner":     ("workspace.departments.product", "run_release_planner"),
    # Revenue agents (Phase 2+)
    "pricing_strategist":  ("workspace.departments.revenue", "run_pricing_strategist"),
    "conversion_analyst":  ("workspace.departments.revenue", "run_conversion_analyst"),
    # Support agents (Phase 3)
    "review_monitor":      ("workspace.departments.support", "run_review_monitor"),
    "retention_analyst":   ("workspace.departments.support", "run_retention_analyst"),
    "support_draft":       ("workspace.departments.support", "run_support_draft"),
    # Analytics agents (Phase 3)
    "anomaly_detector":    ("workspace.departments.analytics", "run_anomaly_detector"),
    "dashboard_curator":   ("workspace.departments.analytics", "run_dashboard_curator"),
    # Infra agents (Phase 3)
    "infra_monitor":       ("workspace.departments.infra", "run_infra_monitor"),
    "cost_optimizer":      ("workspace.departments.infra", "run_cost_optimizer"),
    # Executive
    "director":            ("workspace.director", "run_director"),
}


def run_agent_by_id(agent_id: str, triggered_by: str = "department_runner") -> dict:
    """Dynamically import and run any registered agent."""
    if agent_id not in AGENT_RUNNERS:
        return {"error": f"Agent '{agent_id}' not registered in AGENT_RUNNERS"}

    module_path, func_name = AGENT_RUNNERS[agent_id]
    try:
        import importlib
        module = importlib.import_module(module_path)
        runner = getattr(module, func_name)
        return runner(triggered_by=triggered_by)
    except Exception as e:
        logger.error("Failed to run agent %s: %s", agent_id, e, exc_info=True)
        return {"error": str(e), "agent_id": agent_id}


def run_department(department_id: str, triggered_by: str = "manual") -> dict:
    """Run all agents in a department sequentially, then create summary."""
    dept = DEPARTMENTS.get(department_id)
    if not dept:
        return {"error": f"Department '{department_id}' not found"}

    agent_ids = get_agents_in_department(department_id)
    results: list[dict] = []
    run_ids: list[str] = []

    # Run each specialist agent
    for agent_id in agent_ids:
        if agent_id == "director":
            continue  # Director runs separately
        if agent_id == "hq_assistant":
            continue  # ARIA is always-on, not batch
        if agent_id not in AGENT_RUNNERS:
            logger.warning("Agent %s not yet implemented, skipping", agent_id)
            results.append({"agent_id": agent_id, "status": "not_implemented"})
            continue

        logger.info("Running agent %s in department %s", agent_id, department_id)
        result = run_agent_by_id(agent_id, triggered_by=f"dept:{department_id}")
        results.append(result)

    # Generate department summary using LLM
    period = _current_period()
    summary_report = _generate_department_summary(dept, results, period)

    return {
        "department_id": department_id,
        "period": period,
        "agents_run": len(results),
        "summary": summary_report,
        "triggered_by": triggered_by,
    }


def _current_period() -> str:
    """Return current ISO week period, e.g. '2026-W14'."""
    today = date.today()
    return f"{today.year}-W{today.isocalendar()[1]:02d}"


def _generate_department_summary(dept, agent_results: list[dict], period: str) -> str:
    """Create a summary from all agent results and save to Firestore."""
    # Collect reports from Firestore for agents that ran
    from firebase_admin import firestore
    db = firestore.client()

    agent_reports = []
    for result in agent_results:
        agent_id = result.get("agent_id")
        if not agent_id or result.get("status") == "not_implemented":
            continue
        # Get latest report for this agent
        docs = list(
            db.collection("command_agent_runs")
            .where("agent_id", "==", agent_id)
            .order_by("started_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        if docs:
            d = docs[0].to_dict()
            agent_reports.append(f"### {agent_id}\n{d.get('summary', 'No summary')}")

    combined = "\n\n".join(agent_reports) if agent_reports else "No agent reports available."

    # Use LLM to summarize (lightweight call)
    try:
        llm = setup_llm("llm_model")
        from praisonaiagents import Agent, Task, Agents

        summarizer = Agent(
            name=f"{dept.name} Lead",
            role=f"Department Head of {dept.name}",
            goal=f"Tóm tắt tình hình phòng {dept.name_vi} tuần này",
            backstory=f"Bạn là trưởng phòng {dept.name_vi} tại Hapura. Đọc báo cáo từ nhân viên và tóm tắt ngắn gọn.",
            tools=[],
            llm=llm,
        )

        task = Task(
            description=f"""Dựa vào các báo cáo sau từ phòng {dept.name_vi}:\n\n{combined}\n\n
Hãy tóm tắt trong 3-5 bullet points:
1. Tình trạng chung
2. Điểm nổi bật
3. Vấn đề cần chú ý
4. Đề xuất hành động tuần tới""",
            expected_output="Tóm tắt ngắn gọn bằng tiếng Việt, markdown format",
            agent=summarizer,
        )

        pipeline = Agents(agents=[summarizer], tasks=[task])
        summary_result = str(pipeline.start())

        # Save department report
        save_department_report(
            department_id=dept.id,
            period=period,
            report_markdown=summary_result,
            summary=summary_result[:300],
            recommendations=[],
        )

        return summary_result
    except Exception as e:
        logger.error("Failed to generate department summary: %s", e)
        # Fallback: save raw combined report
        save_department_report(
            department_id=dept.id,
            period=period,
            report_markdown=combined,
            summary=f"Auto-summary failed: {str(e)[:100]}",
        )
        return combined
