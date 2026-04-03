"""
Revenue & Monetization Department — Pricing Strategist, Conversion Analyst.
Revenue Forecaster is an existing agent adopted into this department.
"""
from __future__ import annotations
import logging
from datetime import datetime, date, timedelta
from praisonaiagents.tools import tool
from workspace.base_agent import run_workspace_agent, save_agent_report, send_department_message

logger = logging.getLogger(__name__)


@tool
def get_all_metrics_history() -> list:
    """Get last 6 months metrics history for all projects."""
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
def get_current_metrics() -> list:
    """Get current month metrics."""
    from firebase_admin import firestore
    db = firestore.client()
    period = date.today().strftime("%Y-%m")
    docs = db.collection("command_metrics").where("period", "==", period).stream()
    return [d.to_dict() for d in docs]


@tool
def get_projects() -> list:
    """Get all project metadata."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_projects").stream()
    return [d.to_dict() for d in docs]


@tool
def save_revenue_report(agent_id: str, report: str, summary: str) -> str:
    """Save a Revenue department agent report."""
    return save_agent_report(
        agent_id=agent_id,
        report=report,
        summary=summary,
        metadata={"department": "revenue"},
        triggered_by="workspace",
    )


@tool
def send_revenue_alert(message: str) -> str:
    """Send revenue alert to Telegram."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    msg = f"💰 *REVENUE INSIGHT*\n\n{message}"
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    return "sent" if result else "failed"


@tool
def send_to_growth_dept(insight: str) -> str:
    """Send pricing/conversion insight to Growth department."""
    return send_department_message(
        from_agent_id="revenue_agent",
        from_department="revenue",
        to_department="growth",
        message_type="recommendation",
        payload={"insight": insight},
        priority="medium",
    )


# ─── Pricing Strategist ────────────────────────────────────────────────────────

def run_pricing_strategist(triggered_by: str = "schedule") -> dict:
    """Analyze competitor pricing and optimize subscription tiers."""
    metrics = get_all_metrics_history()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Pricing Strategy Context — {now}

## Revenue History
{metrics}

## ClipPack Context
- Android app, subscription model (in development)
- Category: Video/Clip editing tools
- Target market: Vietnamese users
- Current phase: Testing subscription features

## Market Context
Vietnam mobile app subscription pricing norms:
- Budget tier: 19,000-29,000đ/tháng
- Standard tier: 49,000-79,000đ/tháng
- Pro tier: 99,000-199,000đ/tháng
- Annual discount: 20-40% vs monthly
"""

    return run_workspace_agent(
        agent_id="pricing_strategist",
        name="Pricing Strategist",
        role="Subscription Monetization & Pricing Expert",
        goal="Tối ưu pricing strategy để maximize revenue cho ClipPack subscription",
        backstory=(
            "Bạn là chuyên gia pricing strategy cho mobile apps Việt Nam. "
            "Bạn hiểu willingness-to-pay của users Việt, competitive landscape, "
            "và psychology of pricing. Mục tiêu: maximize LTV và conversion rate. "
            "Trả lời bằng tiếng Việt với số liệu cụ thể."
        ),
        tools=[
            get_all_metrics_history,
            get_projects,
            save_revenue_report,
            send_revenue_alert,
            send_to_growth_dept,
        ],
        task_description=f"""Dựa vào context:\n{context}

Hãy:
1. Đề xuất cấu trúc pricing tiers cho ClipPack subscription:
   - Free tier (giới hạn tính năng gì?)
   - Basic tier (giá? tính năng gì?)
   - Pro tier (giá? tính năng gì?)
   - Annual plans
2. So sánh với 5 apps tương tự trên Play Store (ước tính)
3. Đề xuất trial strategy: trial length, features during trial
4. Tính estimated revenue scenarios:
   - Conservative: 1% conversion, 100 DAU
   - Moderate: 3% conversion, 500 DAU
   - Optimistic: 5% conversion, 2000 DAU
5. Lưu bằng save_revenue_report("pricing_strategist", report, summary)
6. Gửi key insight qua send_revenue_alert()""",
        expected_output="Pricing tier proposal + revenue scenarios + trial strategy",
        model_key="llm_model",
        triggered_by=triggered_by,
    )


# ─── Conversion Analyst ────────────────────────────────────────────────────────

def run_conversion_analyst(triggered_by: str = "schedule") -> dict:
    """Analyze conversion funnel from install to paid subscription."""
    metrics = get_all_metrics_history()
    projects = get_projects()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Conversion Analysis Context — {now}

## Metrics History
{metrics}

## Projects
{projects}
"""

    return run_workspace_agent(
        agent_id="conversion_analyst",
        name="Conversion Analyst",
        role="Funnel Optimization & Conversion Rate Specialist",
        goal="Phân tích và tối ưu conversion funnel từ install đến paid subscription",
        backstory=(
            "Bạn là Growth Hacker và CRO specialist của Hapura. "
            "Bạn phân tích conversion funnel, A/B testing opportunities, "
            "và paywall optimization. Focus vào ClipPack subscription model. "
            "Trả lời bằng tiếng Việt với actionable recommendations."
        ),
        tools=[
            get_all_metrics_history,
            get_current_metrics,
            get_projects,
            save_revenue_report,
            send_to_growth_dept,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. Estimate current conversion funnel cho ClipPack:
   Install → Activate → Engage (3+ sessions) → Trial → Paid
   Dùng new_signups làm proxy cho installs, active_users cho engaged users
2. Tính estimated conversion rate tại mỗi stage
3. Xác định biggest drop-off point trong funnel
4. Đề xuất 5 CRO (conversion rate optimization) tactics cụ thể:
   - Paywall placement và timing
   - Social proof elements
   - Value proposition messaging
   - Trial incentives
   - Onboarding flow improvements
5. A/B test ideas: 3 experiments để test ngay
6. Lưu bằng save_revenue_report("conversion_analyst", report, summary)""",
        expected_output="Conversion funnel analysis + CRO tactics + A/B test roadmap",
        model_key="llm_model",
        triggered_by=triggered_by,
    )
