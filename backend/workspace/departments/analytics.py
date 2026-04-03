"""
Analytics & Intelligence Department — Anomaly Detector, Dashboard Curator.
Strategist (existing) is the lead agent of this department.
"""
from __future__ import annotations
import logging
from datetime import datetime, date, timedelta
from praisonaiagents.tools import tool
from workspace.base_agent import run_workspace_agent, save_agent_report, send_department_message

logger = logging.getLogger(__name__)


# ─── Shared Tools ─────────────────────────────────────────────────────────────

@tool
def get_metrics_last_2_months() -> list:
    """Get metrics for last 2 months to detect anomalies."""
    from firebase_admin import firestore
    db = firestore.client()
    today = date.today()
    current = today.strftime("%Y-%m")
    prev_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    docs = (
        db.collection("command_metrics")
        .where("period", "in", [current, prev_month])
        .stream()
    )
    return [d.to_dict() for d in docs]


@tool
def get_integration_data() -> list:
    """Get GitHub commit velocity and Cloud Run health for all projects."""
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
def get_recent_agent_runs(limit: int = 20) -> list:
    """Get the most recent agent runs across all agents."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = (
        db.collection("command_agent_runs")
        .order_by("started_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


@tool
def save_analytics_report(agent_id: str, report: str, summary: str) -> str:
    """Save an Analytics department agent report to Firestore."""
    return save_agent_report(
        agent_id=agent_id,
        report=report,
        summary=summary,
        metadata={"department": "analytics"},
        triggered_by="workspace",
    )


@tool
def send_anomaly_alert(message: str, priority: str) -> str:
    """Send anomaly alert via Telegram. priority: high/medium/low"""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    icon = "🚨" if priority == "high" else "⚠️" if priority == "medium" else "ℹ️"
    msg = f"{icon} *ANOMALY ALERT*\n\n{message}"
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    return "sent" if result else "failed"


@tool
def broadcast_anomaly_to_depts(finding: str, affected_dept: str) -> str:
    """Broadcast anomaly finding to the relevant department."""
    return send_department_message(
        from_agent_id="anomaly_detector",
        from_department="analytics",
        to_department=affected_dept,
        message_type="alert",
        payload={"anomaly": finding},
        priority="high",
    )


# ─── Anomaly Detector ──────────────────────────────────────────────────────────

def run_anomaly_detector(triggered_by: str = "schedule") -> dict:
    """Detect unusual changes in metrics, commits, or health status."""
    metrics = get_metrics_last_2_months()
    integrations = get_integration_data()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    context = f"""# Anomaly Detection Context — {now}

## Metrics (2 months)
{metrics}

## GitHub & Health
{integrations}
"""

    return run_workspace_agent(
        agent_id="anomaly_detector",
        name="Anomaly Detector",
        role="Real-time Metrics Anomaly Detection System",
        goal="Phát hiện bất thường trong metrics, velocity và health status",
        backstory=(
            "Bạn là hệ thống monitoring AI của Hapura. Bạn so sánh metrics "
            "tháng này với tháng trước để phát hiện drops, spikes, và patterns bất thường. "
            "Định nghĩa anomaly: thay đổi >20% so với tháng trước, hoặc health status degraded. "
            "Trả lời bằng tiếng Việt, ngắn gọn."
        ),
        tools=[
            get_metrics_last_2_months,
            get_integration_data,
            save_analytics_report,
            send_anomaly_alert,
            broadcast_anomaly_to_depts,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. So sánh revenue và active_users tháng này vs tháng trước cho từng project
2. Tính % thay đổi, flag bất thường (>20% drop hoặc >50% spike)
3. Kiểm tra commit velocity: project nào ngừng commit? (velocity = 0)
4. Kiểm tra health status: có service nào degraded/offline không?
5. Tạo anomaly report với severity (high/medium/low)
6. Gửi alert cho các anomalies severity high/medium qua send_anomaly_alert()
7. Lưu bằng save_analytics_report("anomaly_detector", report, summary)""",
        expected_output="Anomaly report với severity levels + alerts sent",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Dashboard Curator ─────────────────────────────────────────────────────────

def run_dashboard_curator(triggered_by: str = "schedule") -> dict:
    """Pre-compute and summarize key metrics for the dashboard."""
    projects = get_all_projects()
    metrics = get_metrics_last_2_months()
    integrations = get_integration_data()
    recent_runs = get_recent_agent_runs(10)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    context = f"""# Dashboard Curator Context — {now}

## Projects
{projects}

## Metrics
{metrics}

## Integrations
{integrations}

## Recent Agent Activity
{[{"agent_id": r.get("agent_id"), "status": r.get("status"), "started_at": r.get("started_at")} for r in recent_runs]}
"""

    return run_workspace_agent(
        agent_id="dashboard_curator",
        name="Dashboard Curator",
        role="Portfolio Dashboard Intelligence Compiler",
        goal="Tổng hợp portfolio health overview cho CEO dashboard",
        backstory=(
            "Bạn là hệ thống tổng hợp data cho CEO dashboard. "
            "Bạn tính toán health scores, trend indicators, và executive summary "
            "từ tất cả data sources. Output phải concise và actionable. "
            "Trả lời bằng tiếng Việt."
        ),
        tools=[
            get_all_projects,
            get_metrics_last_2_months,
            get_integration_data,
            get_recent_agent_runs,
            save_analytics_report,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy tạo Portfolio Executive Summary:

1. **Tổng quan portfolio**: Tổng revenue, tổng users, số projects active
2. **Health matrix**: Project | Revenue Trend | User Trend | Dev Velocity | Health
3. **Star of the week**: Project tốt nhất tuần này và lý do
4. **Action required**: 3 vấn đề CEO cần chú ý ngay
5. **AI Agent Activity**: Bao nhiêu agents chạy tuần này, insights quan trọng nhất
6. Lưu bằng save_analytics_report("dashboard_curator", report, summary)""",
        expected_output="Executive portfolio summary với health matrix",
        model_key="llm_model",
        triggered_by=triggered_by,
    )
