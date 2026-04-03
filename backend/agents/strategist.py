"""
Strategist Agent — Weekly analysis. Reads GP scores + metrics,
recommends which project to focus on next sprint.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, date
from praisonaiagents import Agent, Task, Agents
from praisonaiagents.tools import tool

logger = logging.getLogger(__name__)


def _setup_llm():
    import litellm
    from config import get_settings
    s = get_settings()
    if s.openai_api_key:
        os.environ["OPENAI_API_KEY"]   = s.openai_api_key
        os.environ["OPENAI_BASE_URL"]  = s.openai_base_url
    if not getattr(litellm, "_hapura_stream_patched", False):
        _orig = litellm.completion
        def _completion_no_stream(*args, **kwargs):
            kwargs["stream"] = False
            return _orig(*args, **kwargs)
        litellm.completion = _completion_no_stream
        litellm._hapura_stream_patched = True
    return s.model_strategist


@tool
def get_all_metrics() -> list:
    """Get current month revenue and user metrics for all 4 projects."""
    from firebase_admin import firestore
    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [doc.to_dict() for doc in docs]


@tool
def get_integration_data() -> list:
    """Get latest GitHub commit velocity and health status for all projects."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_integrations_cache").stream()
    return [doc.to_dict() for doc in docs]


@tool
def get_project_list() -> list:
    """Get all project metadata from Firestore."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_projects").stream()
    return [doc.to_dict() for doc in docs]


@tool
def save_strategy_report(report: str, recommended_project: str) -> str:
    """Save strategy report to Firestore and update FOCUS badge on recommended project."""
    from firebase_admin import firestore
    db = firestore.client()
    now = datetime.utcnow().isoformat()

    # Save run
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": "strategist",
        "status": "done",
        "triggered_by": "agent",
        "started_at": now,
        "finished_at": now,
        "report_markdown": report,
        "summary": f"Recommended focus: {recommended_project}",
        "metadata": {"recommended_project": recommended_project},
    })
    return ref.id


@tool
def send_strategy_alert(message: str) -> str:
    """Send weekly strategy recommendation to Telegram."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, message)
    return "sent" if result else "failed"


def run_strategy_analysis(triggered_by: str = "schedule") -> dict:
    """Run weekly strategy analysis with PraisonAI LLM reasoning."""
    llm = _setup_llm()

    # Collect raw data first
    metrics     = get_all_metrics()
    integrations = get_integration_data()
    projects    = get_project_list()

    # Build context string for the agent
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    context = f"""# Hapura Portfolio Data — {now}

## Projects
{projects}

## Revenue & Users (this month)
{metrics}

## GitHub & Health
{integrations}
"""

    agent = Agent(
        name="Hapura Strategist",
        role="Chief Strategy Officer của Hapura portfolio",
        goal="Phân tích toàn bộ metrics và đề xuất project nào nên được focus tuần tới",
        backstory=(
            "Bạn là chiến lược gia của Hapura. Bạn nhìn vào doanh thu, velocity "
            "và health để quyết định phân bổ effort tốt nhất. "
            "Trả lời ngắn gọn, bằng tiếng Việt, actionable."
        ),
        tools=[get_all_metrics, get_integration_data, get_project_list,
               save_strategy_report, send_strategy_alert],
        llm=llm,
    )

    task = Task(
        description=f"""Dựa vào data này:\n{context}

Hãy:
1. Tóm tắt tình trạng mỗi project (1 dòng)
2. Tính GP score tương đối (revenue 40% + users 20% + velocity 20% + uptime 20%)
3. Recommend 1 project để FOCUS tuần tới, giải thích tại sao
4. Đề xuất 2-3 action cụ thể cho project được chọn
5. Lưu report bằng save_strategy_report()
6. Gửi alert Telegram bằng send_strategy_alert() với tóm tắt ngắn""",
        expected_output="Report markdown đầy đủ + đã lưu Firestore + đã gửi Telegram",
        agent=agent,
    )

    pipeline = Agents(agents=[agent], tasks=[task])
    result = pipeline.start()

    return {"result": str(result), "triggered_by": triggered_by}
