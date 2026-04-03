"""
Agent & Department Registry — Single source of truth for all workspace agents.
Existing agents (health_checker, strategist, etc.) are "adopted" into departments.
"""
from __future__ import annotations
from workspace.config_schema import DepartmentMeta


# ─── Department Definitions ──────────────────────────────────────────────────

DEPARTMENTS: dict[str, DepartmentMeta] = {
    "executive": DepartmentMeta(
        id="executive",
        name="Executive Office",
        name_vi="Giám Đốc",
        description="Strategic coordination, cross-department orchestration",
        icon="Crown",
        color="neon-cyan",
        agent_ids=["hq_assistant", "director"],
        lead_agent_id="director",
    ),
    "growth": DepartmentMeta(
        id="growth",
        name="Growth & Marketing",
        name_vi="Tiếp Thị",
        description="User acquisition, ASO, content marketing, competitor analysis",
        icon="TrendingUp",
        color="neon-green",
        agent_ids=["aso_analyst", "content_strategist", "competitor_watcher"],
        lead_agent_id="aso_analyst",
    ),
    "product": DepartmentMeta(
        id="product",
        name="Product & Engineering",
        name_vi="Sản Phẩm",
        description="Bug tracking, feature prioritization, release planning",
        icon="Code2",
        color="neon-purple",
        agent_ids=["bug_detective", "health_checker", "feature_prioritizer", "release_planner"],
        lead_agent_id="bug_detective",
    ),
    "revenue": DepartmentMeta(
        id="revenue",
        name="Revenue & Monetization",
        name_vi="Doanh Thu",
        description="Subscription optimization, pricing, conversion funnels",
        icon="DollarSign",
        color="neon-amber",
        agent_ids=["revenue_forecaster", "pricing_strategist", "conversion_analyst"],
        lead_agent_id="revenue_forecaster",
    ),
    "support": DepartmentMeta(
        id="support",
        name="User Experience & Support",
        name_vi="CSKH",
        description="Review monitoring, retention analysis, support automation",
        icon="HeartHandshake",
        color="neon-red",
        agent_ids=["review_monitor", "retention_analyst", "support_draft"],
        lead_agent_id="review_monitor",
    ),
    "analytics": DepartmentMeta(
        id="analytics",
        name="Analytics & Intelligence",
        name_vi="Phân Tích",
        description="Cross-department metrics, anomaly detection, dashboards",
        icon="BarChart3",
        color="brand",
        agent_ids=["strategist", "anomaly_detector", "dashboard_curator"],
        lead_agent_id="strategist",
    ),
    "infra": DepartmentMeta(
        id="infra",
        name="Infrastructure & DevOps",
        name_vi="Hạ Tầng",
        description="Deployment monitoring, cost optimization, CI/CD health",
        icon="Server",
        color="neon-cyan",
        agent_ids=["infra_monitor", "cost_optimizer"],
        lead_agent_id="infra_monitor",
    ),
}


# ─── Extended Agent Metadata ─────────────────────────────────────────────────
# Merges with existing AGENT_META in agents.py for backward compatibility

WORKSPACE_AGENT_META: dict[str, dict] = {
    # ── Executive ────────────────────────────────────────────
    "director": {
        "name": "Director",
        "role": "Weekly: Đọc tất cả báo cáo phòng ban, tạo Weekly Directive",
        "schedule": "Tuesday 09:00 VN",
        "color": "neon-cyan",
        "department": "executive",
        "is_new": True,
    },
    # ── Growth & Marketing ───────────────────────────────────
    "aso_analyst": {
        "name": "ASO Analyst",
        "role": "Weekly: Phân tích keyword ranking Google Play, đề xuất tối ưu listing",
        "schedule": "Monday 09:00 VN",
        "color": "neon-green",
        "department": "growth",
        "is_new": True,
    },
    "content_strategist": {
        "name": "Content Strategist",
        "role": "Weekly: Tạo content calendar, draft social media posts",
        "schedule": "Wednesday 10:00 VN",
        "color": "neon-green",
        "department": "growth",
        "is_new": True,
    },
    "competitor_watcher": {
        "name": "Competitor Watcher",
        "role": "Weekly: Theo dõi app đối thủ, giá, rating, features mới",
        "schedule": "Wednesday 10:00 VN",
        "color": "neon-green",
        "department": "growth",
        "is_new": True,
    },
    # ── Product & Engineering ────────────────────────────────
    # bug_detective and health_checker already exist in AGENT_META
    "feature_prioritizer": {
        "name": "Feature Prioritizer",
        "role": "Weekly: Đọc user reviews + issues, xếp hạng feature requests",
        "schedule": "Friday 10:00 VN",
        "color": "neon-purple",
        "department": "product",
        "is_new": True,
    },
    "release_planner": {
        "name": "Release Planner",
        "role": "Weekly: Theo dõi commits/PRs, đánh giá release readiness",
        "schedule": "Friday 14:00 VN",
        "color": "neon-purple",
        "department": "product",
        "is_new": True,
    },
    # ── Revenue & Monetization ───────────────────────────────
    # revenue_forecaster already exists
    "pricing_strategist": {
        "name": "Pricing Strategist",
        "role": "Monthly: So sánh giá đối thủ, đề xuất pricing tiers",
        "schedule": "1st of month",
        "color": "neon-amber",
        "department": "revenue",
        "is_new": True,
    },
    "conversion_analyst": {
        "name": "Conversion Analyst",
        "role": "Weekly: Phân tích funnel install → subscribe, đề xuất cải thiện",
        "schedule": "Monday 14:00 VN",
        "color": "neon-amber",
        "department": "revenue",
        "is_new": True,
    },
    # ── Support ──────────────────────────────────────────────
    "review_monitor": {
        "name": "Review Monitor",
        "role": "Daily: Theo dõi Play Store reviews, phân loại sentiment",
        "schedule": "Daily 09:00 VN",
        "color": "neon-red",
        "department": "support",
        "is_new": True,
    },
    "retention_analyst": {
        "name": "Retention Analyst",
        "role": "Weekly: Cohort retention analysis, churn risk alerts",
        "schedule": "Monday 11:00 VN",
        "color": "neon-red",
        "department": "support",
        "is_new": True,
    },
    "support_draft": {
        "name": "Support Draft",
        "role": "On-demand: Draft template responses cho user reviews",
        "schedule": "On demand",
        "color": "neon-red",
        "department": "support",
        "is_new": True,
    },
    # ── Analytics ────────────────────────────────────────────
    # strategist already exists
    "anomaly_detector": {
        "name": "Anomaly Detector",
        "role": "Realtime: Giám sát metrics, cảnh báo bất thường",
        "schedule": "Every 30 min",
        "color": "brand",
        "department": "analytics",
        "is_new": True,
    },
    "dashboard_curator": {
        "name": "Dashboard Curator",
        "role": "4h: Pre-compute metrics và health scores cho frontend",
        "schedule": "Every 4 hours",
        "color": "brand",
        "department": "analytics",
        "is_new": True,
    },
    # ── Infra ────────────────────────────────────────────────
    "infra_monitor": {
        "name": "Infra Monitor",
        "role": "Daily: SSL, DNS, billing, quota + Cloud Run health (evolved Health Checker)",
        "schedule": "Daily 08:00 VN",
        "color": "neon-cyan",
        "department": "infra",
        "is_new": True,
    },
    "cost_optimizer": {
        "name": "Cost Optimizer",
        "role": "Monthly: Theo dõi chi phí GCP, đề xuất tối ưu",
        "schedule": "1st of month",
        "color": "neon-cyan",
        "department": "infra",
        "is_new": True,
    },
}

# Map existing agents to departments (backward compat)
EXISTING_AGENT_DEPARTMENTS: dict[str, str] = {
    "hq_assistant": "executive",
    "health_checker": "product",
    "strategist": "analytics",
    "bug_detective": "product",
    "revenue_forecaster": "revenue",
}


def get_all_agent_ids() -> list[str]:
    """Return all agent IDs (existing + new workspace agents)."""
    existing = ["health_checker", "strategist", "bug_detective", "revenue_forecaster", "hq_assistant"]
    new_ids = [aid for aid in WORKSPACE_AGENT_META if aid not in existing]
    return existing + new_ids


def get_department_for_agent(agent_id: str) -> str | None:
    """Get department ID for any agent."""
    if agent_id in EXISTING_AGENT_DEPARTMENTS:
        return EXISTING_AGENT_DEPARTMENTS[agent_id]
    meta = WORKSPACE_AGENT_META.get(agent_id)
    return meta["department"] if meta else None


def get_agents_in_department(department_id: str) -> list[str]:
    """Get all agent IDs in a department."""
    dept = DEPARTMENTS.get(department_id)
    return dept.agent_ids if dept else []
