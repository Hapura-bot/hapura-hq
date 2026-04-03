"""
Product & Engineering Department — Feature Prioritizer, Release Planner.
Bug Detective and Health Checker are existing agents adopted into this department.
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from praisonaiagents.tools import tool
from workspace.base_agent import run_workspace_agent, save_agent_report, send_department_message

logger = logging.getLogger(__name__)


@tool
def get_github_data() -> list:
    """Get GitHub integration cache for all projects."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_integrations_cache").stream()
    return [d.to_dict() for d in docs]


@tool
def get_all_projects() -> list:
    """Get all project metadata."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_projects").stream()
    return [d.to_dict() for d in docs]


@tool
def get_all_metrics() -> list:
    """Get current month metrics for all projects."""
    from firebase_admin import firestore
    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [d.to_dict() for d in docs]


@tool
def create_kanban_task(project_id: str, title: str, description: str, priority: str) -> str:
    """Create a kanban task from agent recommendations. priority: high/medium/low"""
    from firebase_admin import firestore
    db = firestore.client()
    now = datetime.utcnow().isoformat()
    ref = db.collection("command_tasks").document()
    ref.set({
        "project_id": project_id,
        "title": title,
        "description": description,
        "status": "todo",
        "priority": priority,
        "tags": ["ai-generated"],
        "created_at": now,
        "updated_at": now,
    })
    return ref.id


@tool
def save_product_report(agent_id: str, report: str, summary: str) -> str:
    """Save a Product department agent report to Firestore."""
    return save_agent_report(
        agent_id=agent_id,
        report=report,
        summary=summary,
        metadata={"department": "product"},
        triggered_by="workspace",
    )


@tool
def send_finding_to_growth(finding: str, priority: str) -> str:
    """Send product finding (e.g., competitor feature gap) to Growth department."""
    return send_department_message(
        from_agent_id="product_agent",
        from_department="product",
        to_department="growth",
        message_type="finding",
        payload={"finding": finding},
        priority=priority,
    )


# ─── Feature Prioritizer ──────────────────────────────────────────────────────

def run_feature_prioritizer(triggered_by: str = "schedule") -> dict:
    """Analyze user metrics and issues to prioritize features."""
    projects = get_all_projects()
    github_data = get_github_data()
    metrics = get_all_metrics()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Feature Prioritization Context — {now}

## Projects
{projects}

## GitHub Data (issues, commits)
{github_data}

## Current Metrics (users, revenue)
{metrics}
"""

    return run_workspace_agent(
        agent_id="feature_prioritizer",
        name="Feature Prioritizer",
        role="Product Manager AI — Feature Prioritization Specialist",
        goal="Phân tích data để xác định features nên build tiếp theo",
        backstory=(
            "Bạn là Product Manager AI của Hapura. Bạn đọc GitHub issues, "
            "metrics trends và user patterns để quyết định feature nào có ROI cao nhất. "
            "Framework: Impact (user value) × Confidence × Ease / Effort. "
            "Trả lời bằng tiếng Việt."
        ),
        tools=[
            get_all_projects,
            get_github_data,
            get_all_metrics,
            save_product_report,
            send_finding_to_growth,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. Liệt kê các GitHub issues quan trọng nhất (nếu có data)
2. Xác định feature gaps dựa trên metrics trends
3. Tạo Feature Priority Matrix cho ClipPack:
   - Feature | Impact (1-5) | Effort (1-5) | Priority Score | Rationale
4. TOP 5 features nên implement ngay cho ClipPack subscription model
5. Đề xuất quick wins (dễ làm, impact cao) cho mỗi project
6. Lưu bằng save_product_report("feature_prioritizer", report, summary)""",
        expected_output="Feature priority matrix + TOP 5 features + quick wins",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Release Planner ──────────────────────────────────────────────────────────

def run_release_planner(triggered_by: str = "schedule") -> dict:
    """Assess release readiness based on GitHub activity."""
    projects = get_all_projects()
    github_data = get_github_data()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Release Planning Context — {now}

## Projects
{projects}

## GitHub Activity
{github_data}
"""

    return run_workspace_agent(
        agent_id="release_planner",
        name="Release Planner",
        role="Release Engineering & Sprint Planning Specialist",
        goal="Đánh giá release readiness và lập kế hoạch sprint tiếp theo",
        backstory=(
            "Bạn là Release Manager AI của Hapura. Dựa vào commit velocity, "
            "open issues/PRs để đánh giá khi nào project ready để release. "
            "Bạn cân nhắc risk vs speed và đưa ra go/no-go recommendations. "
            "Trả lời bằng tiếng Việt."
        ),
        tools=[
            get_all_projects,
            get_github_data,
            save_product_report,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. Đánh giá release readiness cho từng project (commits 7d, open issues, health)
2. Release Readiness Score: Project | Commits/week | Open Issues | Health | Score (0-10) | Recommendation
3. Xác định project nào sẵn sàng release ngay, project nào cần thêm work
4. Đề xuất sprint goals cho tuần tới dựa trên velocity
5. Risk assessment: điều gì có thể block release của ClipPack?
6. Lưu bằng save_product_report("release_planner", report, summary)""",
        expected_output="Release readiness matrix + sprint recommendations + risk assessment",
        model_key="llm_model",
        triggered_by=triggered_by,
    )
