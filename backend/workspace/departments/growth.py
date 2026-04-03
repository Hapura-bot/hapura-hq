"""
Growth & Marketing Department — ASO, Content, Competitor agents.
Phase 2 priority: directly impacts ClipPack downloads and sales.
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from praisonaiagents.tools import tool
from workspace.base_agent import (
    run_workspace_agent,
    save_agent_report,
    send_department_message,
)

logger = logging.getLogger(__name__)


# ─── Shared Tools ────────────────────────────────────────────────────────────

@tool
def get_project_play_store_info() -> dict:
    """Get Play Store metadata for ClipPack (and other Android products)."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_projects").where("platform", "==", "android").stream()
    projects = [d.to_dict() for d in docs]
    return {
        "projects": projects,
        "note": "Use Google Play Developer API or SerpAPI for live keyword data. "
                "For now, analyze based on known metadata.",
    }


@tool
def get_current_metrics_summary() -> list:
    """Get current month metrics for context."""
    from firebase_admin import firestore
    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [d.to_dict() for d in docs]


@tool
def save_growth_report(agent_id: str, report: str, summary: str) -> str:
    """Save a Growth department agent report to Firestore."""
    doc_id = save_agent_report(
        agent_id=agent_id,
        report=report,
        summary=summary,
        metadata={"department": "growth"},
        triggered_by="workspace",
    )
    return doc_id


@tool
def send_finding_to_department(to_department: str, finding: str, priority: str) -> str:
    """Send a finding to another department (e.g., product, revenue).
    priority: 'high', 'medium', 'low'
    """
    doc_id = send_department_message(
        from_agent_id="growth_agent",
        from_department="growth",
        to_department=to_department,
        message_type="finding",
        payload={"finding": finding},
        priority=priority,
    )
    return f"Message sent: {doc_id}"


@tool
def send_growth_telegram_alert(message: str) -> str:
    """Send a Growth alert to Telegram."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    msg = f"📈 *GROWTH ALERT*\n\n{message}"
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    return "sent" if result else "failed"


# ─── ASO Analyst ─────────────────────────────────────────────────────────────

def run_aso_analyst(triggered_by: str = "schedule") -> dict:
    """Analyze App Store Optimization for ClipPack."""
    play_info = get_project_play_store_info()
    metrics = get_current_metrics_summary()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# ASO Analysis Context — {now}

## Play Store Projects
{play_info}

## Current Metrics
{metrics}
"""

    return run_workspace_agent(
        agent_id="aso_analyst",
        name="ASO Analyst",
        role="App Store Optimization Specialist cho Hapura mobile apps",
        goal="Phân tích và đề xuất cải thiện Play Store listing để tăng organic downloads",
        backstory=(
            "Bạn là chuyên gia ASO với 5 năm kinh nghiệm tối ưu app trên Google Play. "
            "Bạn hiểu keyword ranking, A/B testing title/description, "
            "và các yếu tố ảnh hưởng tới conversion rate trên Play Store. "
            "Trả lời bằng tiếng Việt, ngắn gọn, actionable."
        ),
        tools=[
            get_project_play_store_info,
            get_current_metrics_summary,
            save_growth_report,
            send_finding_to_department,
            send_growth_telegram_alert,
        ],
        task_description=f"""Dựa vào data:\n{context}

Hãy phân tích ASO cho ClipPack:
1. Đánh giá title, description, keywords hiện tại (nếu có data)
2. Đề xuất 10 keywords tiềm năng cho category của app
3. Gợi ý cải thiện Play Store listing (title, short desc, full desc)
4. So sánh với best practices ASO 2026
5. Lưu report bằng save_growth_report("aso_analyst", report, summary)
6. Nếu có finding quan trọng, gửi cho phòng product hoặc revenue""",
        expected_output="ASO report markdown với keyword suggestions + listing improvements",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Content Strategist ─────────────────────────────────────────────────────

def run_content_strategist(triggered_by: str = "schedule") -> dict:
    """Generate content marketing strategy and calendar."""
    play_info = get_project_play_store_info()
    metrics = get_current_metrics_summary()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Content Strategy Context — {now}

## Products
{play_info}

## Metrics
{metrics}
"""

    return run_workspace_agent(
        agent_id="content_strategist",
        name="Content Strategist",
        role="Content Marketing Manager cho Hapura products",
        goal="Tạo content calendar và draft social media posts để tăng brand awareness",
        backstory=(
            "Bạn là content strategist chuyên về app marketing. "
            "Bạn biết cách tạo viral content trên TikTok, Facebook, Instagram "
            "cho các app mobile. Hiểu audience Việt Nam. "
            "Trả lời bằng tiếng Việt."
        ),
        tools=[
            get_project_play_store_info,
            get_current_metrics_summary,
            save_growth_report,
            send_growth_telegram_alert,
        ],
        task_description=f"""Dựa vào context:\n{context}

Hãy:
1. Đề xuất 5 content ideas cho tuần tới (TikTok, Facebook, Instagram)
2. Draft 2 social media posts mẫu cho ClipPack
3. Gợi ý hashtags trending liên quan
4. Đề xuất content calendar tháng này
5. Lưu bằng save_growth_report("content_strategist", report, summary)""",
        expected_output="Content calendar + draft posts + hashtag suggestions",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Competitor Watcher ──────────────────────────────────────────────────────

def run_competitor_watcher(triggered_by: str = "schedule") -> dict:
    """Monitor competitor apps in the same category."""
    play_info = get_project_play_store_info()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Competitor Analysis Context — {now}

## Our Products
{play_info}
"""

    return run_workspace_agent(
        agent_id="competitor_watcher",
        name="Competitor Watcher",
        role="Competitive Intelligence Analyst cho Hapura",
        goal="Theo dõi đối thủ cạnh tranh và phát hiện cơ hội/mối đe dọa",
        backstory=(
            "Bạn là chuyên gia phân tích cạnh tranh trong ngành mobile app. "
            "Bạn theo dõi competitor apps, pricing strategies, feature releases, "
            "và user reviews của đối thủ. Trả lời bằng tiếng Việt."
        ),
        tools=[
            get_project_play_store_info,
            save_growth_report,
            send_finding_to_department,
            send_growth_telegram_alert,
        ],
        task_description=f"""Dựa vào context:\n{context}

Hãy phân tích competitive landscape cho ClipPack:
1. Liệt kê 5 app đối thủ trực tiếp trong cùng category
2. So sánh features, pricing, ratings
3. Xác định competitive advantages và weaknesses của ClipPack
4. Đề xuất 3 cơ hội differentiation
5. Lưu bằng save_growth_report("competitor_watcher", report, summary)
6. Gửi findings quan trọng cho phòng product và revenue""",
        expected_output="Competitor analysis report + opportunities + threats",
        model_key="llm_model",
        triggered_by=triggered_by,
    )
