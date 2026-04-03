"""
Infrastructure & DevOps Department — Infra Monitor, Cost Optimizer.
"""
from __future__ import annotations
import logging
from datetime import datetime
from praisonaiagents.tools import tool
from workspace.base_agent import run_workspace_agent, save_agent_report

logger = logging.getLogger(__name__)

# Cloud Run service endpoints (same as health_checker)
CLOUD_RUN_SERVICES = {
    "clippack":         "https://clippack-backend-730131473012.asia-southeast1.run.app/health",
    "trendkr":          "https://trendkr-backend-730131473012.asia-southeast1.run.app/health",
    "hapura-command":   "https://hapura-command-backend-730131473012.asia-southeast1.run.app/health",
    "hapu-studio":      None,
    "douyin-vi-dubber": None,
}


@tool
def ping_all_services() -> list:
    """Ping all Cloud Run services and check SSL/response headers."""
    import httpx
    import time
    results = []
    for service_id, url in CLOUD_RUN_SERVICES.items():
        if not url:
            results.append({"service": service_id, "status": "not_deployed"})
            continue
        try:
            start = time.time()
            r = httpx.get(url, timeout=10, follow_redirects=True)
            latency = int((time.time() - start) * 1000)
            # Check SSL (HTTPS = SSL ok)
            ssl_ok = url.startswith("https://")
            results.append({
                "service": service_id,
                "status": "healthy" if r.status_code == 200 else "degraded",
                "latency_ms": latency,
                "status_code": r.status_code,
                "ssl": ssl_ok,
                "url": url,
            })
        except httpx.TimeoutException:
            results.append({"service": service_id, "status": "timeout", "latency_ms": 10000, "url": url})
        except Exception as e:
            results.append({"service": service_id, "status": "offline", "error": str(e), "url": url})
    return results


@tool
def get_integration_cache() -> list:
    """Get cached integration data (GitHub + health) for all projects."""
    from firebase_admin import firestore
    db = firestore.client()
    docs = db.collection("command_integrations_cache").stream()
    return [d.to_dict() for d in docs]


@tool
def get_agent_run_stats() -> dict:
    """Get agent run statistics (total, errors, last 24h)."""
    from firebase_admin import firestore
    from datetime import timedelta
    db = firestore.client()
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    recent = list(
        db.collection("command_agent_runs")
        .where("started_at", ">=", cutoff)
        .stream()
    )
    total = len(recent)
    errors = sum(1 for r in recent if r.to_dict().get("status") == "error")
    return {"last_24h_runs": total, "errors": errors, "success_rate": f"{((total - errors) / total * 100):.0f}%" if total > 0 else "N/A"}


@tool
def save_infra_report(agent_id: str, report: str, summary: str) -> str:
    """Save Infra department report to Firestore."""
    return save_agent_report(
        agent_id=agent_id,
        report=report,
        summary=summary,
        metadata={"department": "infra"},
        triggered_by="workspace",
    )


@tool
def send_infra_alert(message: str) -> str:
    """Send infrastructure alert via Telegram."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    msg = f"🖥️ *INFRA ALERT*\n\n{message}"
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, msg)
    return "sent" if result else "failed"


# ─── Infra Monitor ─────────────────────────────────────────────────────────────

def run_infra_monitor(triggered_by: str = "schedule") -> dict:
    """Run comprehensive infrastructure health check."""
    services = ping_all_services()
    cache = get_integration_cache()
    agent_stats = get_agent_run_stats()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    context = f"""# Infrastructure Monitor Context — {now}

## Service Health
{services}

## Integration Cache
{cache}

## AI Agent Stats (last 24h)
{agent_stats}
"""

    return run_workspace_agent(
        agent_id="infra_monitor",
        name="Infra Monitor",
        role="Infrastructure & DevOps Health Monitor",
        goal="Giám sát toàn bộ infrastructure, phát hiện và báo cáo vấn đề kỹ thuật",
        backstory=(
            "Bạn là DevOps engineer AI của Hapura. Bạn giám sát Cloud Run services, "
            "SSL certificates, API response times và AI agent system health. "
            "Bạn phân tích patterns và đề xuất improvements. "
            "Trả lời bằng tiếng Việt, kỹ thuật và chính xác."
        ),
        tools=[
            ping_all_services,
            get_integration_cache,
            get_agent_run_stats,
            save_infra_report,
            send_infra_alert,
        ],
        task_description=f"""Dựa vào dữ liệu:\n{context}

Hãy:
1. Tổng hợp health status của tất cả Cloud Run services
2. Phân tích latency trends (>500ms = warning, >1000ms = critical)
3. Kiểm tra SSL status cho tất cả endpoints
4. Đánh giá AI Agent system health (run success rate, errors)
5. Tạo Infrastructure Health Report với Overall Score (0-100)
6. Gửi alert nếu có issues critical/warning qua send_infra_alert()
7. Lưu bằng save_infra_report("infra_monitor", report, summary)""",
        expected_output="Infrastructure health report với scoring + alerts",
        model_key="model_health_checker",
        triggered_by=triggered_by,
    )


# ─── Cost Optimizer ────────────────────────────────────────────────────────────

def run_cost_optimizer(triggered_by: str = "schedule") -> dict:
    """Analyze infrastructure costs and suggest optimizations."""
    services = ping_all_services()
    now = datetime.utcnow().strftime("%Y-%m-%d")

    context = f"""# Cost Optimization Context — {now}

## Active Services
{services}

## GCP Stack
- Cloud Run: hapura-command-backend, clippack-backend, trendkr-backend
- Firebase: trendkr-hapura project (Firestore, Hosting, Auth)
- Region: asia-southeast1
- Tier: Free/Starter plans
"""

    return run_workspace_agent(
        agent_id="cost_optimizer",
        name="Cost Optimizer",
        role="Cloud Infrastructure Cost Analyst",
        goal="Phân tích chi phí GCP và đề xuất tối ưu để giảm spend",
        backstory=(
            "Bạn là FinOps specialist cho Hapura. Bạn hiểu GCP pricing, "
            "Cloud Run billing (per-request + CPU/memory), Firebase quota. "
            "Mục tiêu: minimize cost trong khi maintain performance. "
            "Trả lời bằng tiếng Việt với estimates cụ thể."
        ),
        tools=[
            ping_all_services,
            save_infra_report,
        ],
        task_description=f"""Dựa vào context:\n{context}

Hãy:
1. Estimate chi phí hàng tháng cho stack hiện tại (Cloud Run + Firebase)
2. Xác định 3-5 cơ hội tiết kiệm chi phí
3. Đề xuất Cloud Run settings tối ưu (min-instances, memory, CPU)
4. Đánh giá Firebase usage vs quota limits
5. Tổng hợp Cost Report với potential savings
6. Lưu bằng save_infra_report("cost_optimizer", report, summary)""",
        expected_output="Cost analysis report với specific optimization recommendations",
        model_key="llm_model",
        triggered_by=triggered_by,
    )
