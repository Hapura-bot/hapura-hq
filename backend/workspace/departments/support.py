"""
User Experience & Support Department — Review Monitor, Retention Analyst, Support Draft.
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from praisonaiagents.tools import tool
from workspace.base_agent import run_workspace_agent, save_agent_report, send_department_message

logger = logging.getLogger(__name__)


# ─── Shared Tools ─────────────────────────────────────────────────────────────

@tool
def get_all_metrics_history() -> list:
    """Get last 6 months metrics for all projects to analyze retention trends."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = (
        db.collection("command_metrics")
        .order_by("period", direction=firestore.Query.DESCENDING)
        .limit(30)
        .stream()
    )
    return [d.to_dict() for d in docs]


@tool
def get_current_month_metrics() -> list:
    """Get current month metrics for all projects."""
    from firebase_admin import firestore
    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [d.to_dict() for d in docs]


@tool
def save_support_report(agent_id: str, report: str, summary: str) -> str:
    """Save a Support department agent report to Firestore."""
    return save_agent_report(
        agent_id=agent_id,
        report=report,
        summary=summary,
        metadata={"department": "support"},
        triggered_by="workspace",
    )


@tool
def send_support_alert(message: str) -> str:
    """Send a Support/UX alert to Telegram."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    msg = f"💬 *SUPPORT ALERT*\n\n{message}"
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    return "sent" if result else "failed"


@tool
def send_finding_to_product(finding: str, priority: str) -> str:
    """Send user feedback finding to Product department."""
    return send_department_message(
        from_agent_id="support_agent",
        from_department="support",
        to_department="product",
        message_type="finding",
        payload={"finding": finding, "source": "user_feedback"},
        priority=priority,
    )


# ─── Review Monitor ────────────────────────────────────────────────────────────

def run_review_monitor(triggered_by: str = "schedule") -> dict:
    """Monitor Play Store reviews and sentiment for all Android products."""
    metrics = get_current_month_metrics()
    history = get_all_metrics_history()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Review Monitor Context — {now}

## Current Metrics
{metrics}

## Historical Metrics
{history[:10]}

## Note
Google Play Reviews API requires service account access.
Analyze based on metrics trends to infer user sentiment.
"""

    return run_workspace_agent(
        agent_id="review_monitor",
        name="Review Monitor",
        role="User Feedback & Sentiment Analyst cho Hapura products",
        goal="Phân tích sentiment người dùng, phát hiện patterns từ metrics",
        backstory=(
            "Bạn là chuyên gia phân tích feedback người dùng. "
            "Dựa vào metrics (active users, new signups, revenue trend) "
            "để suy luận về user sentiment và satisfaction. "
            "Khi Google Play API chưa kết nối, dùng metrics làm proxy. "
            "Trả lời bằng tiếng Việt."
        ),
        tools=[
            get_all_metrics_history,
            get_current_month_metrics,
            save_support_report,
            send_support_alert,
            send_finding_to_product,
        ],
        task_description=f"""Dựa vào context:\n{context}

Hãy:
1. Phân tích trend active_users và new_signups để suy luận retention rate
2. Xác định project nào đang có dấu hiệu user churn (users giảm hoặc flat)
3. Đề xuất 3 cải thiện UX dựa trên patterns quan sát
4. Draft mẫu response cho 3 loại negative review phổ biến trong category app
5. Lưu bằng save_support_report("review_monitor", report, summary)
6. Nếu có vấn đề nghiêm trọng, gửi alert và báo product dept""",
        expected_output="Sentiment analysis + UX improvement suggestions + review response templates",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Retention Analyst ─────────────────────────────────────────────────────────

def run_retention_analyst(triggered_by: str = "schedule") -> dict:
    """Analyze user cohort retention and identify churn risks."""
    history = get_all_metrics_history()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Retention Analysis Context — {now}

## Metrics History (last 30 entries)
{history}
"""

    return run_workspace_agent(
        agent_id="retention_analyst",
        name="Retention Analyst",
        role="Cohort Retention & Churn Risk Specialist",
        goal="Phân tích cohort retention, xác định churn risk và đề xuất re-engagement",
        backstory=(
            "Bạn là data analyst chuyên về user retention cho mobile apps. "
            "Tính toán retention rate từ active_users / new_signups theo tháng. "
            "Xác định dấu hiệu churn sớm và đề xuất re-engagement campaigns. "
            "Trả lời bằng tiếng Việt với số liệu cụ thể."
        ),
        tools=[
            get_all_metrics_history,
            save_support_report,
            send_support_alert,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. Tính estimated retention rate cho mỗi project: active_users / (sum new_signups 3 tháng trước)
2. Tạo cohort analysis table: Project | M1 Retention | M3 Retention | Trend
3. Xác định project có churn risk cao nhất
4. Đề xuất 3-5 re-engagement strategy cụ thể (push notifications, email, in-app)
5. Lưu bằng save_support_report("retention_analyst", report, summary)""",
        expected_output="Cohort retention table + churn risk ranking + re-engagement strategies",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Support Draft ──────────────────────────────────────────────────────────────

def run_support_draft(triggered_by: str = "schedule") -> dict:
    """Generate template support responses for common user issues."""
    metrics = get_current_month_metrics()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Support Draft Context — {now}

## Current Products
ClipPack (Android - subscription model, video/clip related)
Trendkr (Web - trend monitoring)
Hapu Studio (Web - creative tools)
Douyin VI Dubber (Web - video dubbing)

## Current Metrics
{metrics}
"""

    return run_workspace_agent(
        agent_id="support_draft",
        name="Support Draft Agent",
        role="Customer Support Response Specialist",
        goal="Tạo template responses cho các vấn đề phổ biến của users",
        backstory=(
            "Bạn là chuyên gia customer support với kinh nghiệm xử lý "
            "feedback người dùng app Việt Nam. Bạn viết responses thân thiện, "
            "rõ ràng và giúp ích. Luôn hướng dẫn cụ thể bằng tiếng Việt."
        ),
        tools=[
            get_current_month_metrics,
            save_support_report,
        ],
        task_description=f"""Dựa vào context:\n{context}

Tạo template responses (bằng tiếng Việt) cho các tình huống:

**ClipPack:**
1. User báo lỗi subscription không active sau khi thanh toán
2. User muốn refund vì app không hoạt động như kỳ vọng
3. User yêu cầu tính năng mới

**Chung (tất cả apps):**
4. App crash / bug nghiêm trọng
5. User đánh 1 sao vì lý do không liên quan kỹ thuật

Mỗi template: Tiêu đề | Tình huống | Response mẫu (100-150 từ)
Lưu bằng save_support_report("support_draft", report, summary)""",
        expected_output="5 support response templates trong tiếng Việt",
        model_key="llm_model",
        triggered_by=triggered_by,
    )
