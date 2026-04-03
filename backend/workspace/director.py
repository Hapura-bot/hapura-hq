"""
DirectorOrchestrator — Reads all department reports, produces Weekly Directive.
Runs on Tuesday 09:00 VN (after all departments have reported on Monday).
"""
from __future__ import annotations
import logging
from datetime import datetime, date, timedelta
from workspace.base_agent import setup_llm, run_workspace_agent
from praisonaiagents.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_all_department_reports() -> list:
    """Get latest department reports from all departments (last 7 days)."""
    from firebase_admin import firestore
    db = firestore.client()
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    # Get all recent docs and filter/sort in Python to avoid composite index
    docs = list(db.collection("command_department_reports").limit(50).stream())
    recent = [d for d in docs if d.to_dict().get("generated_at", "") >= cutoff]
    recent.sort(key=lambda d: d.to_dict().get("generated_at", ""), reverse=True)
    return [{"id": d.id, **d.to_dict()} for d in recent]


@tool
def get_cross_department_messages() -> list:
    """Get unacknowledged cross-department messages."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = list(
        db.collection("command_agent_messages")
        .where("acknowledged", "==", False)
        .limit(20)
        .stream()
    )
    docs.sort(key=lambda d: d.to_dict().get("created_at", ""), reverse=True)
    return [{"id": d.id, **d.to_dict()} for d in docs]


@tool
def get_current_metrics() -> list:
    """Get current month metrics for all projects."""
    from firebase_admin import firestore
    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [d.to_dict() for d in docs]


@tool
def save_directive(
    directive_markdown: str,
    priorities: str,
    department_actions: str,
) -> str:
    """Save the Weekly Directive to Firestore for CEO approval.
    priorities: comma-separated list of priorities.
    department_actions: JSON-like string mapping department to actions.
    """
    from firebase_admin import firestore
    import json
    db = firestore.client()
    today = date.today()
    period = f"{today.year}-W{today.isocalendar()[1]:02d}"

    try:
        actions_dict = json.loads(department_actions)
    except (json.JSONDecodeError, TypeError):
        actions_dict = {"raw": department_actions}

    ref = db.collection("command_directives").document()
    ref.set({
        "period": period,
        "directive_type": "weekly",
        "directive_markdown": directive_markdown[:10000],
        "priorities": [p.strip() for p in priorities.split(",")],
        "department_actions": actions_dict,
        "generated_at": datetime.utcnow().isoformat(),
        "approved_by": None,
        "approved_at": None,
        "status": "draft",
    })
    return ref.id


@tool
def send_directive_to_telegram(summary: str) -> str:
    """Send directive summary to CEO via Telegram for approval."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    message = f"📋 *WEEKLY DIRECTIVE*\n\n{summary}\n\n_Reply 'approve' to activate._"
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, message)
    return "sent" if result else "failed"


def run_director(triggered_by: str = "schedule") -> dict:
    """Run the Director Agent — cross-department weekly directive."""
    # Collect context
    dept_reports = get_all_department_reports()
    messages = get_cross_department_messages()
    metrics = get_current_metrics()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    context = f"""# Hapura Weekly Intelligence Brief — {now}

## Department Reports (last 7 days)
{_format_reports(dept_reports)}

## Cross-Department Messages (unacknowledged)
{_format_messages(messages)}

## Current Month Metrics
{metrics}
"""

    result = run_workspace_agent(
        agent_id="director",
        name="Hapura Director",
        role="Chief Operating Officer của Hapura portfolio",
        goal="Đọc tất cả báo cáo phòng ban, tạo Weekly Directive với priorities rõ ràng",
        backstory=(
            "Bạn là Giám đốc Điều hành AI của Hapura. Bạn đọc báo cáo từ 7 phòng ban, "
            "phát hiện conflicts/gaps, và tạo directive tuần cho CEO duyệt. "
            "Trả lời bằng tiếng Việt, ngắn gọn, actionable."
        ),
        tools=[
            get_all_department_reports,
            get_cross_department_messages,
            get_current_metrics,
            save_directive,
            send_directive_to_telegram,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. Tóm tắt tình hình mỗi phòng ban (1 dòng)
2. Xác định TOP 3 ưu tiên tuần này
3. Phân bổ hành động cho mỗi phòng ban
4. Highlight conflicts hoặc gaps giữa các phòng ban
5. Lưu directive bằng save_directive()
6. Gửi tóm tắt qua Telegram bằng send_directive_to_telegram()""",
        expected_output="Weekly Directive markdown + đã lưu Firestore + đã gửi Telegram",
        model_key="model_revenue_forecaster",  # Use Opus for Director
        triggered_by=triggered_by,
    )

    return result


def _format_reports(reports: list) -> str:
    if not reports:
        return "Chưa có báo cáo nào."
    lines = []
    for r in reports[:10]:
        dept = r.get("department_id", "?")
        summary = r.get("summary", "N/A")[:200]
        lines.append(f"### {dept}\n{summary}")
    return "\n\n".join(lines)


def _format_messages(messages: list) -> str:
    if not messages:
        return "Không có messages chưa xử lý."
    lines = []
    for m in messages[:10]:
        lines.append(f"- [{m.get('priority', 'medium')}] {m.get('from_department')} → {m.get('to_department')}: {m.get('message_type')}")
    return "\n".join(lines)
