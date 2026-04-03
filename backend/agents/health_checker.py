"""
Health Checker Agent — Daily ping tất cả Cloud Run endpoints.
Reports latency, status, và gửi Telegram alert nếu có service down/slow.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime
from praisonaiagents import Agent, Task, Agents
from praisonaiagents.tools import tool

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "clippack":   "https://clippack-backend-730131473012.asia-southeast1.run.app/health",
    "trendkr":    "https://trendkr-backend-730131473012.asia-southeast1.run.app/health",
    "hapu-studio":      None,  # not deployed yet
    "douyin-vi-dubber": None,  # not deployed yet
}


def _setup_llm():
    import litellm
    from config import get_settings
    s = get_settings()
    if not getattr(litellm, "_hapura_stream_patched", False):
        _orig = litellm.completion
        def _completion_no_stream(*args, **kwargs):
            kwargs["stream"] = False
            return _orig(*args, **kwargs)
        litellm.completion = _completion_no_stream
        litellm._hapura_stream_patched = True
    if s.openai_api_key:
        os.environ["OPENAI_API_KEY"]   = s.openai_api_key
        os.environ["OPENAI_BASE_URL"]  = s.openai_base_url
    return s.model_health_checker


@tool
def ping_endpoint(project_id: str) -> dict:
    """Ping a project's Cloud Run health endpoint. Returns status, latency_ms, and details."""
    import httpx, time
    url = ENDPOINTS.get(project_id)
    if not url:
        return {"project_id": project_id, "status": "not_deployed", "latency_ms": None, "url": None}
    try:
        start = time.time()
        r = httpx.get(url, timeout=8)
        latency = int((time.time() - start) * 1000)
        return {
            "project_id": project_id,
            "status": "healthy" if r.status_code == 200 else "degraded",
            "latency_ms": latency,
            "status_code": r.status_code,
            "url": url,
        }
    except httpx.TimeoutException:
        return {"project_id": project_id, "status": "timeout", "latency_ms": 8000, "url": url}
    except Exception as e:
        return {"project_id": project_id, "status": "offline", "latency_ms": None, "error": str(e), "url": url}


@tool
def save_health_report(findings: str) -> str:
    """Save the health check report to Firestore command_agent_runs collection. Returns run ID."""
    from firebase_admin import firestore
    db = firestore.client()
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": "health_checker",
        "status": "done",
        "triggered_by": "agent",
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "report_markdown": findings,
        "summary": findings[:200],
    })
    return ref.id


@tool
def send_alert(message: str) -> str:
    """Send a Telegram alert for critical issues found during health check."""
    from config import get_settings
    from agents.telegram import send_telegram_sync
    s = get_settings()
    result = send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, message)
    return "sent" if result else "failed"


def run_health_check(triggered_by: str = "schedule") -> dict:
    """Run full health check across all projects. Returns report dict."""
    llm = _setup_llm()

    # Run pings directly (fast, no LLM needed for data collection)
    results = []
    for pid in ENDPOINTS:
        results.append(ping_endpoint(pid))

    # Build markdown report
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"## 🔍 Health Check — {now}\n"]
    issues = []

    for r in results:
        pid = r["project_id"]
        status = r["status"]
        latency = r.get("latency_ms")

        if status == "healthy":
            icon = "✅"
            detail = f"{latency}ms"
        elif status == "not_deployed":
            icon = "⚪"
            detail = "not deployed yet"
        elif status == "timeout":
            icon = "⏱️"
            detail = "TIMEOUT (>8s)"
            issues.append(f"⏱️ *{pid}*: timeout")
        elif status == "offline":
            icon = "🔴"
            detail = f"OFFLINE — {r.get('error', '')}"
            issues.append(f"🔴 *{pid}*: OFFLINE")
        else:
            icon = "🟡"
            detail = f"degraded ({latency}ms)"
            issues.append(f"🟡 *{pid}*: degraded")

        lines.append(f"- {icon} **{pid}**: {detail}")

    if issues:
        lines.append(f"\n### ⚠️ Issues Detected\n" + "\n".join(issues))
    else:
        lines.append("\n### ✅ All systems nominal")

    report = "\n".join(lines)

    # Save to Firestore
    from firebase_admin import firestore
    db = firestore.client()
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": "health_checker",
        "status": "done",
        "triggered_by": triggered_by,
        "started_at": now,
        "finished_at": datetime.utcnow().isoformat(),
        "report_markdown": report,
        "summary": f"{len(results)} services checked, {len(issues)} issues found",
        "metadata": {"results": results},
    })

    # Send Telegram alert if issues found
    if issues:
        from config import get_settings
        from agents.telegram import send_telegram_sync
        s = get_settings()
        alert = f"⚠️ *Hapura HQ — Health Alert*\n\n" + "\n".join(issues) + f"\n\n_Checked at {now}_"
        send_telegram_sync(s.telegram_bot_token, s.telegram_chat_id, alert)

    return {"report": report, "issues": issues, "run_id": ref.id}
