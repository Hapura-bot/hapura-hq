"""
Bug Detective Agent — On-demand GitHub Issues/PRs summarizer.
Tổng hợp blockers quan trọng nhất từ 4 repos.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime
from praisonaiagents import Agent, Task, Agents
from praisonaiagents.tools import tool

logger = logging.getLogger(__name__)

GITHUB_REPOS = {
    "clippack":         "Hapura-bot/clippack",
    "trendkr":          "Hapura-bot/trendkr",
    "hapu-studio":      "Hapura-bot/great-studio",
    "douyin-vi-dubber": "Hapura-bot/douyin-vi-dubber",
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
    return s.model_bug_detective


@tool
def get_open_issues(project_id: str) -> list:
    """Fetch open GitHub issues for a project. Returns list of issue dicts."""
    import httpx
    from config import get_settings
    s = get_settings()
    repo = GITHUB_REPOS.get(project_id)
    if not repo:
        return []
    headers = {"Accept": "application/vnd.github+json"}
    if s.github_token:
        headers["Authorization"] = f"Bearer {s.github_token}"
    try:
        r = httpx.get(
            f"https://api.github.com/repos/{repo}/issues",
            params={"state": "open", "per_page": 20, "sort": "updated"},
            headers=headers, timeout=8
        )
        if r.status_code == 200:
            return [{"number": i["number"], "title": i["title"],
                     "labels": [l["name"] for l in i.get("labels", [])],
                     "created_at": i["created_at"]} for i in r.json()]
    except Exception as e:
        logger.warning(f"GitHub issues error {project_id}: {e}")
    return []


@tool
def save_bug_report(report: str) -> str:
    """Save bug detective report to Firestore."""
    from firebase_admin import firestore
    db = firestore.client()
    now = datetime.utcnow().isoformat()
    ref = db.collection("command_agent_runs").document()
    ref.set({
        "agent_id": "bug_detective",
        "status": "done",
        "triggered_by": "manual",
        "started_at": now,
        "finished_at": now,
        "report_markdown": report,
        "summary": report[:200],
    })
    return ref.id


def run_bug_detection(triggered_by: str = "manual") -> dict:
    """Fetch issues from all repos and summarize critical blockers."""
    llm = _setup_llm()

    # Collect issues directly
    all_issues = {}
    for pid in GITHUB_REPOS:
        issues = get_open_issues(pid)
        if issues:
            all_issues[pid] = issues

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if not all_issues:
        report = f"## 🕵️ Bug Detective — {now}\n\nKhông tìm thấy issues nào (có thể do GitHub token chưa được cấu hình hoặc repos private)."
        from firebase_admin import firestore
        db = firestore.client()
        ref = db.collection("command_agent_runs").document()
        ref.set({
            "agent_id": "bug_detective",
            "status": "done",
            "triggered_by": triggered_by,
            "started_at": now,
            "finished_at": now,
            "report_markdown": report,
            "summary": "No issues found (check GitHub token)",
        })
        return {"report": report, "run_id": ref.id}

    agent = Agent(
        name="Hapura Bug Detective",
        role="Bug analyst và triage specialist",
        goal="Tìm và tóm tắt các blockers quan trọng nhất cần giải quyết ngay",
        backstory=(
            "Bạn review GitHub issues của Hapura. Ưu tiên: labels 'bug', 'critical', "
            "'blocking'. Bỏ qua feature requests. Trả lời bằng tiếng Việt."
        ),
        tools=[get_open_issues, save_bug_report],
        llm=llm,
    )

    issues_text = "\n".join([
        f"\n### {pid}\n" + "\n".join([f"- #{i['number']}: {i['title']} [{', '.join(i['labels'])}]"
                                       for i in issues])
        for pid, issues in all_issues.items()
    ])

    task = Task(
        description=f"""Issues hiện tại:\n{issues_text}

Hãy:
1. Xác định top 3-5 blockers quan trọng nhất (bug/critical/blocking)
2. Tóm tắt mỗi cái trong 1-2 câu tiếng Việt
3. Đề xuất thứ tự ưu tiên xử lý
4. Lưu report bằng save_bug_report()""",
        expected_output="Report markdown đã được lưu vào Firestore",
        agent=agent,
    )

    pipeline = Agents(agents=[agent], tasks=[task])
    result = pipeline.start()
    return {"result": str(result), "triggered_by": triggered_by}
