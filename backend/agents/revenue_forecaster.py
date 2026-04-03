"""
Revenue Forecaster Agent — Monthly trend analysis và dự báo.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, date
from praisonaiagents import Agent, Task, Agents
from praisonaiagents.tools import tool

logger = logging.getLogger(__name__)


def _setup_llm():
    from config import get_settings
    s = get_settings()
    if s.openai_api_key:
        os.environ["OPENAI_API_KEY"]   = s.openai_api_key
        os.environ["OPENAI_BASE_URL"]  = s.openai_base_url
    return s.model_revenue_forecaster


@tool
def get_metric_history(project_id: str) -> list:
    """Get last 6 months of revenue/user metrics for a project."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = (
        db.collection("command_metrics")
        .where("project_id", "==", project_id)
        .order_by("period", direction=firestore.Query.DESCENDING)
        .limit(6)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


@tool
def save_forecast_report(report: str, forecasts: str) -> str:
    """Save revenue forecast report to Firestore."""
    from firebase_admin import firestore
    db = firestore.client()
    now = datetime.utcnow().isoformat()
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": "revenue_forecaster",
        "status": "done",
        "triggered_by": "agent",
        "started_at": now,
        "finished_at": now,
        "report_markdown": report,
        "summary": forecasts[:200],
        "metadata": {"forecasts_text": forecasts},
    })
    return ref.id


@tool
def send_forecast_alert(message: str) -> str:
    """Send monthly forecast to Telegram."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, message)
    return "sent" if result else "failed"


def run_revenue_forecast(triggered_by: str = "schedule") -> dict:
    """Run revenue forecast analysis for all projects."""
    llm = _setup_llm()

    project_ids = ["clippack", "trendkr", "hapu-studio", "douyin-vi-dubber"]
    all_history = {pid: get_metric_history(pid) for pid in project_ids}
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    next_month = date.today().strftime("%Y-%m")  # approximate

    history_text = "\n".join([
        f"\n### {pid}\n" + (
            "\n".join([f"- {m.get('period')}: {m.get('revenue_vnd', 0):,}đ, {m.get('active_users', 0)} users"
                       for m in history])
            if history else "- No data yet"
        )
        for pid, history in all_history.items()
    ])

    agent = Agent(
        name="Hapura Revenue Forecaster",
        role="Financial analyst và revenue strategist",
        goal="Dự báo doanh thu tháng tới cho từng project dựa trên trend",
        backstory=(
            "Bạn là analyst tài chính của Hapura. Nhìn vào lịch sử doanh thu "
            "và tính toán growth rate, dự báo tháng tới. Thực tế và concise. "
            "Trả lời bằng tiếng Việt."
        ),
        tools=[get_metric_history, save_forecast_report, send_forecast_alert],
        llm=llm,
        verbose=False,
        self_reflect=False,
    )

    task = Task(
        description=f"""Lịch sử revenue:\n{history_text}

Hãy:
1. Tính MoM growth rate cho mỗi project có data
2. Dự báo revenue tháng {next_month} cho từng project
3. Xác định project có growth rate cao nhất → "Rising Star"
4. Tạo bảng tóm tắt: Project | Tháng hiện tại | Dự báo tháng tới | Growth %
5. Lưu report bằng save_forecast_report()
6. Gửi Telegram alert bằng send_forecast_alert() với tóm tắt""",
        expected_output="Report markdown với bảng dự báo đã lưu Firestore",
        agent=agent,
    )

    pipeline = Agents(agents=[agent], tasks=[task], verbose=False)
    result = pipeline.start()
    return {"result": str(result), "triggered_by": triggered_by}
